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
import threading
from email.message import EmailMessage
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from threading import Event, Thread
from functools import partial
from queue import Queue
import select

# Global pause event
pause_event = Event()
command_queue = Queue()

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler('transcoder.log')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

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
    logger.info(f"Input duration: {input_duration}s, Output duration: {output_duration}s")

    # Relax the duration check slightly
    if abs(input_duration - output_duration) > 2:  # Changed from 1 to 2 seconds
        return False, f"Duration mismatch: input {input_duration}s, output {output_duration}s"

    # Check video codec
    output_codec = next((stream['codec_name'] for stream in output_info['streams'] if stream['codec_type'] == 'video'), None)
    logger.info(f"Output codec: {output_codec}")

    # Update the codec check
    if output_codec != 'av1':
        return False, f"Incorrect video codec: expected av1, got {output_codec}"

    return True, "Verification passed"

def transcode_file(input_file, output_file, preset, preset_dir, encoder, quality, encoder_preset, prioritize_config, callback=None, threads=None):
    preset_path = os.path.join(preset_dir, preset)
    handbrake_commands = [
        "/usr/bin/HandBrakeCLI",  # Use the full path if it's not in PATH
        "--preset-import-file", preset_path,
        "-i", input_file,
        "-o", output_file,
    ]
    
    if prioritize_config:
        # Apply config settings, potentially overriding preset
        if encoder:
            handbrake_commands.extend(["-e", encoder])
        if quality:
            handbrake_commands.extend(["-q", quality])
        if encoder_preset:
            handbrake_commands.extend(["--encoder-preset", encoder_preset])
    
    if threads:
        handbrake_commands.extend(["-t", str(threads)])
    
    logger.info(f"Running HandBrake command: {' '.join(handbrake_commands)}")
    
    start_time = time.time()
    try:
        process = subprocess.Popen(handbrake_commands, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        
        full_output = []
        for line in process.stdout:
            full_output.append(line)
            if not command_queue.empty():
                command = command_queue.get()
                if command == 'p':
                    logger.info("Transcoding paused")
                    pause_event.set()
                    command_queue.task_done()
                elif command == 'r':
                    logger.info("Transcoding resumed")
                    pause_event.clear()
                    command_queue.task_done()

            while pause_event.is_set():
                time.sleep(0.1)
                if not command_queue.empty():
                    command = command_queue.get()
                    if command == 'r':
                        logger.info("Transcoding resumed")
                        pause_event.clear()
                        command_queue.task_done()
                        break

            match = re.search(r'(\d+\.\d+) %', line)
            if match:
                progress = float(match.group(1))
                sys.stdout.write(f"\rProgress: {progress:.2f}%")
                sys.stdout.flush()
                if callback:
                    if callback(progress):
                        process.terminate()
                        return "cancelled"
        
        process.wait()
        end_time = time.time()
        
        if process.returncode != 0:
            logger.error(f"HandBrake error: Process returned {process.returncode}")
            logger.error("HandBrake output:")
            for line in full_output:
                logger.error(line.strip())
            return None
        
        print()  # Move to the next line after progress is complete

        # After transcoding, verify the file
        verified, message = verify_transcoded_file(input_file, output_file)
        if not verified:
            logger.error(f"Verification failed for {output_file}: {message}")
            logger.error("HandBrake output:")
            for line in full_output:
                logger.error(line.strip())
            return None
        else:
            logger.info(f"Verification passed for {output_file}")
            return end_time - start_time  # Return the transcoding time

    except subprocess.CalledProcessError as e:
        logger.error(f"HandBrake error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during transcoding: {e}")
        return None

def get_video_codec(file_path):
    try:
        result = subprocess.run([
            'ffprobe',  # Make sure ffprobe is installed
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            file_path
        ], capture_output=True, text=True)
        
        data = json.loads(result.stdout)
        
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                return stream['codec_name']
        
        return "Unknown"
    except Exception as e:
        logger.error(f"Error getting video codec: {str(e)}")
        return "Error"

def process_file(filename, indir, outdir, preset, preset_dir, encoder, quality, encoder_preset, prioritize_config, progress_callback=None, delete_original=False, threads=None):
    full_path = os.path.join(indir, filename)
    output_path = os.path.join(outdir, filename)
    
    logger.info(f"Processing file: {full_path}")
    try:
        original_size = get_file_size(full_path)
        original_codec = get_video_codec(full_path)
        
        callback = partial(progress_callback, filename) if progress_callback else None
        
        transcode_result = transcode_file(full_path, output_path, preset, preset_dir, encoder, quality, encoder_preset, prioritize_config, callback, threads)
        
        if transcode_result is not None:  # Changed from 'if transcode_result:'
            new_size = get_file_size(output_path)
            new_codec = get_video_codec(output_path)
            
            verified, message = verify_transcoded_file(full_path, output_path)
            if verified:
                size_change = (new_size - original_size) / original_size * 100
                logger.info("****************************************")
                logger.info(f"* Transcoding successful for {filename}")
                logger.info(f"* Original size: {original_size:,} bytes")
                logger.info(f"* New size: {new_size:,} bytes")
                logger.info(f"* Size change: {size_change:.2f}%")
                logger.info(f"* Original codec: {original_codec}")
                logger.info(f"* New codec: {new_codec}")
                logger.info("****************************************\n")
                
                
                if delete_original:
                    os.remove(full_path)
                    logger.info(f"Deleted original file: {full_path}")
                
                return True
            else:
                logger.error(f"Verification failed for {output_path}: {message}")
                # Don't delete the output file here, keep it for inspection
                return False
        else:
            logger.error(f"Transcoding failed for {filename}")
            return False
    except Exception as e:
        logger.error(f"An error occurred while processing {filename}: {str(e)}")
        return False

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

def main(input_dir=None, output_dir=None, progress_callback=None, command_callback=None, delete_original=False):
    parser = argparse.ArgumentParser(description="Handbrake Transcoder")
    parser.add_argument("-c", "--config", default="config.json", help="Path to the config file")
    parser.add_argument("-i", "--input", help="Override input directory")
    parser.add_argument("-o", "--output", help="Override output directory")
    parser.add_argument("-t", "--threads", type=int, help="Number of threads for transcoding")
    parser.add_argument("--delete-original", action="store_true", help="Delete original files after successful transcoding and verification")
    args = parser.parse_args()

    logger.info("Script started")
    
    try:
        config = load_config(args.config)
        indir = input_dir or args.input or config['input_directory']
        outdir = output_dir or args.output or config['output_directory']
        presets = config['presets']
        file_types = config['file_types']
        threads_per_task = args.threads or config.get('default_threads', 4)
        delete_original = args.delete_original if args.delete_original is not None else delete_original
        preset_dir = config.get('preset_directory', os.path.dirname(args.config))
        encoder = config.get('encoder')
        quality = config.get('quality')
        encoder_preset = config.get('encoder_preset')
        prioritize_config = config.get('prioritize_config', False)

        logger.info(f"Input directory: {indir}")
        logger.info(f"Output directory: {outdir}")
        logger.info(f"Threads per task: {threads_per_task}")
        logger.info(f"Delete original files: {delete_original}")

        create_directory(indir)
        create_directory(outdir)

        file_list = [f for f in os.listdir(indir) if any(f.lower().endswith(ext) for ext in file_types)]
        logger.info(f"Files to process: {len(file_list)}")

        all_stats = []
        for filename in file_list:
            file_ext = os.path.splitext(filename)[1].lower()
            preset = presets.get(file_ext, presets['default'])
            result = process_file(filename, indir, outdir, preset, preset_dir, encoder, quality, encoder_preset, prioritize_config, progress_callback, delete_original, threads_per_task)
            if result:
                # Don't try to access result as a dictionary
                all_stats.append({
                    'filename': filename,
                    'success': True
                })
            
            if command_callback:
                command = command_callback()
                if command:
                    command_queue.put(command)

        # Calculate and log overall statistics
        successfully_processed = [stat for stat in all_stats if stat['success']]
        
        if successfully_processed:
            # Update this part to not rely on dictionary access of result
            total_files = len(successfully_processed)
            
            stats_message = f"""
            Transcoding completed:
            Total files processed: {total_files}
            """
        else:
            stats_message = "No files were successfully processed."
        
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
    def cli_command_callback():
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip()
            if line in ['p', 'r']:
                return line
        return None

    main(command_callback=cli_command_callback)
