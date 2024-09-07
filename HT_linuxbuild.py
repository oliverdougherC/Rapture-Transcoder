import subprocess
import os
import json
import logging
import re
import sys
import argparse
import hashlib
import time
import smtplib
from email.message import EmailMessage
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event
from functools import partial

# Global pause event
pause_event = Event()

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler('transcoder.log')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()

def load_config(config_path):
    try:
        with open(config_path, 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}.")
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON in config file. Please check the format.")
        raise

def create_directory(directory):
    if not os.path.exists(directory):
        logger.info(f"Creating directory: {directory}")
        os.makedirs(directory)

def get_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as file:
        buf = file.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = file.read(65536)
    return hasher.hexdigest()

def get_file_size(file_path):
    return os.path.getsize(file_path)

def verify_transcoded_file(input_file, output_file):
    def get_video_info(file_path):
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)

    input_info = get_video_info(input_file)
    output_info = get_video_info(output_file)

    # Check if output file exists and has non-zero size
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        return False, "Output file is missing or empty"

    # Compare durations (allowing for small differences due to encoding)
    input_duration = float(input_info['format']['duration'])
    output_duration = float(output_info['format']['duration'])
    if abs(input_duration - output_duration) > 1:  # More than 1 second difference
        return False, f"Duration mismatch: input {input_duration}s, output {output_duration}s"

    # You could add more checks here, such as comparing video/audio stream count, etc.

    return True, "Verification passed"

def transcode_file(input_file, output_file, preset):
    handbrake_commands = [
        "HandBrakeCLI",
        "--preset-import-file", preset,
        "-i", input_file,
        "-o", output_file
    ]
    logger.info(f"Running HandBrake command: {' '.join(handbrake_commands)}")
    
    start_time = time.time()
    process = subprocess.Popen(handbrake_commands, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    for line in process.stdout:
        if pause_event.is_set():
            process.terminate()
            logger.info("Transcoding paused")
            return "paused"

        match = re.search(r'(\d+\.\d+) %', line)
        if match:
            progress = float(match.group(1))
            sys.stdout.write(f"\rProgress: {progress:.2f}%")
            sys.stdout.flush()
    
    process.wait()
    end_time = time.time()
    
    if process.returncode != 0:
        logger.error(f"HandBrake error: Process returned {process.returncode}")
        raise subprocess.CalledProcessError(process.returncode, handbrake_commands)
    
    print()  # Move to the next line after progress is complete

    # After transcoding, verify the file
    verified, message = verify_transcoded_file(input_file, output_file)
    if not verified:
        print(f"Verification failed for {output_file}: {message}")
        return False
    else:
        print(f"Verification passed for {output_file}")
        return True

def process_file(filename, indir, outdir, preset):
    full_path = os.path.join(indir, filename)
    output_path = os.path.join(outdir, filename)
    
    logger.info(f"Processing file: {full_path}")
    try:
        original_size = get_file_size(full_path)
        transcode_time = transcode_file(full_path, output_path, preset)
        
        if transcode_time == "paused":
            return "paused"

        logger.info(f"Successfully transcoded {filename} to {output_path}")
        
        # File integrity check
        original_hash = get_file_hash(full_path)
        transcoded_hash = get_file_hash(output_path)
        
        if original_hash != transcoded_hash:
            logger.info(f"File integrity check passed for {filename}")
            transcoded_size = get_file_size(output_path)
            compression_ratio = (1 - transcoded_size / original_size) * 100
            
            stats = {
                "filename": filename,
                "original_size": original_size,
                "transcoded_size": transcoded_size,
                "compression_ratio": compression_ratio,
                "transcode_time": transcode_time
            }
            
            os.remove(full_path)
            logger.info(f"Deleted original file: {full_path}")
            return stats
        else:
            logger.warning(f"File integrity check failed for {filename}. Original file not deleted.")
            return None
    except subprocess.CalledProcessError:
        logger.error(f"Failed to transcode {filename}")
    except OSError as e:
        logger.error(f"Error processing file {full_path}: {e}")
    return None

def send_email(config, subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = config['email']['sender']
    msg['To'] = config['email']['recipient']

    try:
        with smtplib.SMTP(config['email']['smtp_server'], config['email']['smtp_port']) as server:
            server.starttls()
            server.login(config['email']['username'], config['email']['password'])
            server.send_message(msg)
        logger.info("Email notification sent successfully")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")

def main():
    parser = argparse.ArgumentParser(description="Handbrake Transcoder")
    parser.add_argument("-c", "--config", default="config.json", help="Path to the config file")
    parser.add_argument("-i", "--input", help="Override input directory")
    parser.add_argument("-o", "--output", help="Override output directory")
    parser.add_argument("-t", "--threads", type=int, help="Number of concurrent transcoding threads")
    parser.add_argument("--delete-original", action="store_true", help="Delete original files after successful transcoding and verification")
    args = parser.parse_args()

    logger.info("Script started")
    
    try:
        config = load_config(args.config)
        indir = args.input or config['input_directory']
        outdir = args.output or config['output_directory']
        presets = config['presets']
        file_types = config['file_types']
        max_workers = args.threads or config.get('max_workers', 3)

        logger.info(f"Input directory: {indir}")
        logger.info(f"Output directory: {outdir}")

        create_directory(indir)
        create_directory(outdir)

        file_list = os.listdir(indir)
        logger.info(f"Files in input directory: {file_list}")

        all_stats = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for filename in file_list:
                if any(filename.lower().endswith(ext) for ext in file_types):
                    file_ext = os.path.splitext(filename)[1].lower()
                    preset = presets.get(file_ext, presets['default'])
                    futures.append(executor.submit(process_file, filename, indir, outdir, preset))
                else:
                    logger.info(f"Skipping file {filename} (not a supported format)")
            
            for future in as_completed(futures):
                result = future.result()
                if result and result != "paused":
                    all_stats.append(result)
                elif result == "paused":
                    logger.info("Transcoding process paused. Waiting to resume...")
                    pause_event.clear()  # Reset the pause event
                    # Here you would typically wait for user input to resume
                    # For simplicity, we'll just continue with the next file

        # Calculate and log overall statistics
        total_original_size = sum(stat['original_size'] for stat in all_stats)
        total_transcoded_size = sum(stat['transcoded_size'] for stat in all_stats)
        total_time = sum(stat['transcode_time'] for stat in all_stats)
        overall_compression = (1 - total_transcoded_size / total_original_size) * 100

        stats_message = f"""
        Transcoding completed:
        Total files processed: {len(all_stats)}
        Total original size: {total_original_size / 1024 / 1024:.2f} MB
        Total transcoded size: {total_transcoded_size / 1024 / 1024:.2f} MB
        Overall compression: {overall_compression:.2f}%
        Total processing time: {total_time:.2f} seconds
        """
        logger.info(stats_message)

        # Send email notification
        if config.get('email'):
            send_email(config, "Transcoding Process Completed", stats_message)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if config.get('email'):
            send_email(config, "Transcoding Process Error", f"An error occurred: {str(e)}")

    logger.info("Script finished")

if __name__ == "__main__":
    main()
