import subprocess
import sys
import os
import json
import logging
import shutil
import re
import threading
import time
import requests
import queue

def setup_logging():
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the path to the logs directory
    log_dir = os.path.join(script_dir, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, 'transcoding.log')
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def load_config():
    logger = logging.getLogger()
    logger.info("Loading config")
    
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the path to the config file
    config_path = os.path.join(script_dir, 'config.json')
    
    logger.debug(f"Looking for config file at: {config_path}")
    
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        logger.info(f"Script directory: {script_dir}")
        logger.info("Please ensure config.json is in the same directory as the script.")
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            
        # Validate and process config values
        config['video_codec'] = config.get('video_codec', '').lower()
        config['video_bitrate'] = int(config.get('video_bitrate', 0))
        config['audio_bitrate'] = int(config.get('audio_bitrate', 0))
        config['use_media_detection'] = config.get('use_media_detection', False)
        config['omdb_api_key'] = config.get('omdb_api_key', '')
        config['movie_output_directory'] = config.get('movie_output_directory', config['output_directory'])
        config['tv_output_directory'] = config.get('tv_output_directory', config['output_directory'])
        config['delete_original'] = config.get('delete_original', False)
        config['fallback_encoder'] = config.get('fallback_encoder', '').lower()  # Add this line
        
        logger.info("Config loaded successfully")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading config file: {e}")
        raise

def check_ffmpeg_installed():
    return shutil.which("ffmpeg") is not None

def get_video_info(file_path):
    command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    logger.debug(f"Running ffprobe command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.debug(f"ffprobe stdout: {result.stdout}")
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running ffprobe: {e}")
        logger.error(f"ffprobe stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding ffprobe output: {e}")
        logger.error(f"Raw ffprobe output: {result.stdout}")
        return None

def human_readable_size(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def human_readable_bitrate(bitrate):
    if bitrate is None or bitrate == 'N/A':
        return 'N/A'
    bitrate = float(bitrate)
    for unit in ['bps', 'Kbps', 'Mbps', 'Gbps']:
        if bitrate < 1000.0:
            return f"{bitrate:.2f} {unit}"
        bitrate /= 1000.0
    return f"{bitrate:.2f} Tbps"

def print_video_comparison(input_file, output_file):
    input_info = get_video_info(input_file)
    output_info = get_video_info(output_file)

    if input_info is None or output_info is None:
        logger.error("Unable to print video comparison due to missing video information.")
        return

    input_video_stream = next(s for s in input_info['streams'] if s['codec_type'] == 'video')
    output_video_stream = next(s for s in output_info['streams'] if s['codec_type'] == 'video')

    input_audio_stream = next(s for s in input_info['streams'] if s['codec_type'] == 'audio')
    output_audio_stream = next(s for s in output_info['streams'] if s['codec_type'] == 'audio')

    input_video_bitrate = input_video_stream.get('bit_rate', 'N/A')
    output_video_bitrate = output_video_stream.get('bit_rate', 'N/A')
    input_audio_bitrate = input_audio_stream.get('bit_rate', 'N/A')
    output_audio_bitrate = output_audio_stream.get('bit_rate', 'N/A')

    logger.info("\nVideo Comparison:")
    logger.info(f"{'Property':<20} {'Input':<30} {'Output':<30}")
    logger.info("-" * 80)
    logger.info(f"{'Video Codec':<20} {input_video_stream['codec_name']:<30} {output_video_stream['codec_name']:<30}")
    logger.info(f"{'Audio Codec':<20} {input_audio_stream['codec_name']:<30} {output_audio_stream['codec_name']:<30}")
    input_res = f"{input_video_stream['width']}x{input_video_stream['height']}"
    output_res = f"{output_video_stream['width']}x{output_video_stream['height']}"
    logger.info(f"{'Resolution':<20} {input_res:<30} {output_res:<30}")
    logger.info(f"{'Video Bitrate':<20} {human_readable_bitrate(input_video_bitrate):<30} {human_readable_bitrate(output_video_bitrate):<30}")
    logger.info(f"{'Audio Bitrate':<20} {human_readable_bitrate(input_audio_bitrate):<30} {human_readable_bitrate(output_audio_bitrate):<30}")
    logger.info(f"{'Duration':<20} {input_info['format']['duration']:<30} {output_info['format']['duration']:<30}")
    logger.info(f"{'File Size':<20} {human_readable_size(os.path.getsize(input_file)):<30} {human_readable_size(os.path.getsize(output_file)):<30}")

def verify_transcoding(input_file, output_file, tolerance=1.0):
    logger.info("Verifying transcoding...")
    
    if not os.path.exists(output_file):
        logger.error(f"Error: Output file does not exist: {output_file}")
        return False
    
    if os.path.getsize(output_file) == 0:
        logger.error(f"Error: Output file is empty: {output_file}")
        return False
    
    input_info = get_video_info(input_file)
    output_info = get_video_info(output_file)
    
    if input_info is None or output_info is None:
        logger.error("Unable to verify transcoding due to missing video information.")
        return False
    
    input_duration = float(input_info['format']['duration'])
    output_duration = float(output_info['format']['duration'])
    
    duration_diff = abs(input_duration - output_duration)
    
    if duration_diff > tolerance:
        logger.error(f"Error: Duration mismatch. Input: {input_duration:.2f}s, Output: {output_duration:.2f}s")
        return False
    
    logger.info("Verification passed: Output file exists, is non-empty, and has correct duration.")
    return True

def detect_gpu():
    try:
        if shutil.which("nvidia-smi"):
            nvidia_smi = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if nvidia_smi.returncode == 0:
                return "nvidia"
        
        if shutil.which("vainfo"):
            vainfo = subprocess.run(["vainfo"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if "Intel" in vainfo.stdout:
                return "intel"
        
        if shutil.which("rocm-smi"):
            rocm_smi = subprocess.run(["rocm-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if rocm_smi.returncode == 0:
                return "amd"
    except Exception as e:
        logger.error(f"Error detecting GPU: {e}")
    
    return "cpu"

def check_encoder_support(encoder):
    try:
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=True)
        return encoder in result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting encoder list: {e}")
        return False

def get_encoder(config_encoder, gpu_type, config):
    codec_aliases = {
        "h264": ["x264", "h.264", "avc"],
        "hevc": ["x265", "h265", "h.265"],
        "av1": []
    }

    # Normalize the config_encoder
    for codec, aliases in codec_aliases.items():
        if config_encoder.lower() in [codec] + [alias.lower() for alias in aliases]:
            config_encoder = codec
            break

    gpu_encoders = {
        "nvidia": {
            "h264": "h264_nvenc",
            "hevc": "hevc_nvenc",
            "av1": "av1_nvenc",
        },
        "intel": {
            "h264": "h264_qsv",
            "hevc": "hevc_qsv",
            "av1": "av1_qsv",
        },
        "amd": {
            "h264": "h264_amf",
            "hevc": "hevc_amf",
        }
    }

    if gpu_type in gpu_encoders and config_encoder in gpu_encoders[gpu_type]:
        gpu_encoder = gpu_encoders[gpu_type][config_encoder]
        if check_encoder_support(gpu_encoder):
            return gpu_encoder
        else:
            logger.warning(f"GPU encoder {gpu_encoder} not available. Trying fallback encoder.")
    
    # Try fallback encoder with GPU acceleration
    fallback_encoder = config.get('fallback_encoder')
    if fallback_encoder and gpu_type in gpu_encoders and fallback_encoder in gpu_encoders[gpu_type]:
        fallback_gpu_encoder = gpu_encoders[gpu_type][fallback_encoder]
        if check_encoder_support(fallback_gpu_encoder):
            logger.info(f"Using fallback GPU encoder: {fallback_gpu_encoder}")
            return fallback_gpu_encoder
        else:
            logger.warning(f"Fallback GPU encoder {fallback_gpu_encoder} not available. Falling back to CPU encoding.")
    
    # Fall back to CPU encoding
    if config_encoder == "h264":
        return "libx264"
    elif config_encoder == "hevc":
        return "libx265"
    elif config_encoder == "av1":
        return "libaom-av1"
    else:
        logger.warning(f"Unsupported encoder: {config_encoder}. Falling back to libx264.")
        return "libx264"

def transcode_video(input_file, output_file, config):
    logger.debug(f"Starting transcoding of {input_file}")
    if not os.path.exists(input_file):
        logger.error(f"Input file does not exist: {input_file}")
        return False

    if not check_ffmpeg_installed():
        logger.error("FFmpeg is not installed. Please install it and try again.")
        return False

    input_info = get_video_info(input_file)
    if input_info is None:
        logger.error(f"Unable to get video information for {input_file}. Skipping this file.")
        return False

    gpu_type = detect_gpu()
    encoder = get_encoder(config['video_codec'], gpu_type, config)

    # Determine if we're using GPU or CPU encoding
    cpu_encoders = ["libx264", "libx265", "libaom-av1"]
    if encoder in cpu_encoders:
        acceleration = "CPU"
    else:
        acceleration = f"{gpu_type.upper()} GPU"

    logger.info(f"Transcoding to {encoder} using {acceleration} acceleration")
    logger.debug(f"Detected GPU type: {gpu_type}")
    logger.debug(f"Using encoder: {encoder}")

    command = [
        "ffmpeg",
        "-i", input_file,
        "-map", "0",  # Include all streams from the input
        "-c:v", encoder,
    ]

    if config['video_bitrate'] > 0:
        command.extend(["-b:v", f"{config['video_bitrate']}k"])
        command.extend(["-maxrate", f"{int(config['video_bitrate'] * 1.5)}k"])
        command.extend(["-bufsize", f"{config['video_bitrate'] * 2}k"])
    else:
        # When video_bitrate is 0, use the input bitrate
        input_video_stream = next(s for s in input_info['streams'] if s['codec_type'] == 'video')
        input_bitrate = input_video_stream.get('bit_rate')
        if input_bitrate:
            command.extend(["-b:v", input_bitrate])

    # Audio settings
    command.extend(["-c:a", "copy"])  # Copy audio streams by default
    if config['audio_bitrate'] > 0:
        command.extend(["-c:a:0", "aac", "-b:a:0", f"{config['audio_bitrate']}k"])  # Re-encode only the first audio stream if bitrate is specified

    # Subtitle settings
    command.extend(["-c:s", "copy"])  # Copy subtitle streams

    command.extend([
        "-y",
        output_file
    ])

    try:
        logger.debug(f"Running command: {' '.join(command)}")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        duration = get_video_duration(input_file)
        start_time = time.time()
        last_update_time = start_time
        last_progress = 0
        last_frame = 0
        
        while True:
            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.debug(f"FFmpeg output: {output.strip()}")
                progress = parse_progress(output, duration)
                if progress:
                    current_time = time.time()
                    elapsed_time = current_time - start_time
                    if current_time - last_update_time >= 1:  # Update every second
                        progress_diff = progress['percentage'] - last_progress
                        time_diff = current_time - last_update_time
                        frame_diff = progress['frame'] - last_frame
                        
                        # Calculate speed as percentage per second
                        speed = progress_diff / time_diff if time_diff > 0 else 0
                        
                        # Calculate FPS
                        fps = frame_diff / time_diff if time_diff > 0 else 0
                        
                        # Calculate overall FPS
                        overall_fps = progress['frame'] / elapsed_time if elapsed_time > 0 else 0
                        
                        # Estimate ETA based on remaining percentage and current speed
                        remaining_percentage = 100 - progress['percentage']
                        eta = remaining_percentage / speed if speed > 0 else 0
                        
                        print(f"\rProgress: {progress['percentage']:.2f}% | FPS: {overall_fps:.2f} | "
                              f"Speed: {speed:.2f}%/s | ETA: {eta:.2f}s", end='')
                        sys.stdout.flush()
                        last_update_time = current_time
                        last_progress = progress['percentage']
                        last_frame = progress['frame']

        print()  # New line after progress
        
        if process.returncode != 0:
            logger.error(f"FFmpeg process returned non-zero exit code: {process.returncode}")
            return False

        logger.info(f"Transcoding complete: {os.path.basename(input_file)}")
        
        if verify_transcoding(input_file, output_file):
            print_video_comparison(input_file, output_file)
            return True
        else:
            logger.error("Transcoding verification failed. Please check the output file.")
            return False
    except Exception as e:
        logger.error(f"Error during transcoding: {e}")
        return False

def get_video_duration(file_path):
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return float(result.stdout)

def parse_progress(output, duration):
    time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", output)
    frame_match = re.search(r"frame=\s*(\d+)", output)
    if time_match and frame_match:
        hours, minutes, seconds = map(float, time_match.groups())
        time = hours * 3600 + minutes * 60 + seconds
        frame = int(frame_match.group(1))
        percentage = (time / duration) * 100 if duration > 0 else 0
        return {'time': time, 'frame': frame, 'percentage': percentage}
    return None

def detect_media_type(title, config):
    if not config.get('use_media_detection', False):
        return None

    api_key = config.get('omdb_api_key')
    if not api_key:
        return None

    # Remove year and parentheses from the end of the title
    clean_title = re.sub(r'\s*\(\d{4}\)$', '', title)
    # Remove any remaining parentheses and their contents
    clean_title = re.sub(r'\s*\([^)]*\)', '', clean_title)
    # Remove any non-alphanumeric characters except spaces and hyphens
    clean_title = re.sub(r'[^\w\s-]', '', clean_title).strip()

    url = f"http://www.omdbapi.com/?apikey={api_key}&t={clean_title}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad responses
        data = response.json()

        if data.get('Response') == 'True':
            return 'movie' if data.get('Type') == 'movie' else 'tv' if data.get('Type') == 'series' else None
    except requests.RequestException as e:
        logger.error(f"Error querying OMDb API: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding OMDb API response: {e}")
    
    return None

def process_directory(config):
    input_dir = os.path.expanduser(config['input_directory'])
    output_dir = os.path.expanduser(config['output_directory'])
    movie_dir = os.path.expanduser(config.get('movie_output_directory', output_dir))
    tv_dir = os.path.expanduser(config.get('tv_output_directory', output_dir))
    extensions = config['file_extensions']
    use_media_detection = config.get('use_media_detection', False)
    delete_original = config.get('delete_original', False)

    for dir in [input_dir, output_dir, movie_dir, tv_dir]:
        if not os.path.exists(dir):
            os.makedirs(dir)

    files_to_process = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            logger.debug(f"Checking file: {file}")
            # Skip hidden files and macOS metadata files
            if file.startswith('.') or file.startswith('._'):
                logger.info(f"Skipping hidden or metadata file: {file}")
                continue
            if any(file.lower().endswith(ext.lower()) for ext in extensions):
                input_path = os.path.join(root, file)
                rel_path = os.path.relpath(input_path, input_dir)
                
                if use_media_detection:
                    # Detect media type
                    file_name = os.path.splitext(file)[0]
                    media_type = detect_media_type(file_name, config)
                    
                    if media_type == 'movie':
                        output_path = os.path.join(movie_dir, rel_path)
                        logger.info(f"Detected movie: {file_name}")
                    elif media_type == 'tv':
                        output_path = os.path.join(tv_dir, rel_path)
                        logger.info(f"Detected TV series: {file_name}")
                    else:
                        output_path = os.path.join(output_dir, rel_path)
                        logger.info(f"Unknown media type: {file_name}")
                else:
                    output_path = os.path.join(output_dir, rel_path)
                
                logger.debug(f"Adding file to process: {input_path} -> {output_path}")
                files_to_process.append((input_path, output_path))

    total_files = len(files_to_process)
    logger.info(f"Found {total_files} files to process")

    failed_files = []
    processed_files = []
    total_size_saved = 0

    for index, (input_path, output_path) in enumerate(files_to_process, start=1):
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        file_name = os.path.basename(input_path)
        logger.info(f"Transcoding [{index}/{total_files}]: {file_name}")
        
        success = transcode_video(input_path, output_path, config)
        if success:
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            size_saved = input_size - output_size
            total_size_saved += size_saved
            processed_files.append((input_path, size_saved))
            if delete_original:
                try:
                    os.remove(input_path)
                except OSError as e:
                    logger.error(f"Error deleting original file {input_path}: {e}")
        else:
            failed_files.append(file_name)

    return failed_files, processed_files, total_size_saved

def human_readable_size(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Transcoding script started")

    gpu_type = detect_gpu()
    if gpu_type != "cpu":
        logger.info(f"GPU acceleration ({gpu_type}) will be used when possible")
    else:
        logger.info("No compatible GPU detected, using CPU encoding")

    try:
        config = load_config()
        failed_files, processed_files, total_size_saved = process_directory(config)
    except Exception as e:
        logger.exception("An unexpected error occurred:")
        failed_files, processed_files, total_size_saved = [], [], 0
    finally:
        if processed_files:
            final_message = "Script execution completed successfully."
        elif failed_files:
            final_message = "Script execution completed with some errors."
        else:
            final_message = "Script execution completed. No files were processed."

        if processed_files:
            final_message += "\n\nProcessed files:"
            for input_file, _ in processed_files:
                final_message += f"\n- {os.path.basename(input_file)}"

        if failed_files:
            final_message += "\n\nFailed files:"
            for failed_file in failed_files:
                final_message += f"\n- {failed_file}"

        if config.get('delete_original', False) and processed_files:
            final_message += f"\n\nTotal file reduction: {human_readable_size(total_size_saved)}"

        print(f"\n{final_message}")
        print("\nPress [Enter] to exit...")
        input()