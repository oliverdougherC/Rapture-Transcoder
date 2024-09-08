import os
import sys
import argparse
import json
import threading
import time
import subprocess

# Add the directory containing HT_linuxbuild.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from HT_linuxbuild import main as transcoder_main_function

# Default values
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_THREADS = 4
TIMEOUT = 20  # Timeout in seconds

def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Expand environment variables in the paths
    for key in ['input_directory', 'output_directory']:
        if key in config:
            config[key] = os.path.expandvars(config[key])
    
    return config

def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def input_with_timeout(prompt, timeout=TIMEOUT):
    print(prompt, end='', flush=True)
    result = [None]
    
    def get_input():
        result[0] = input()
    
    thread = threading.Thread(target=get_input)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        print("\nTimeout reached. Using default value.")
        return None
    return result[0]

def verify_file(input_file, output_file):
    try:
        # Check if ffprobe is available
        subprocess.run(["ffprobe", "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("WARNING: ffprobe not found. Skipping file verification.")
        return True

    try:
        # Get input file duration
        input_duration = float(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", input_file
        ]).decode().strip())

        # Get output file duration
        output_duration = float(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", output_file
        ]).decode().strip())

        # Compare durations (allow for small difference due to encoding)
        duration_difference = abs(input_duration - output_duration)
        if duration_difference > 1:  # More than 1 second difference
            print(f"WARNING: Duration mismatch for {input_file}")
            print(f"Input duration: {input_duration:.2f}s, Output duration: {output_duration:.2f}s")
            return False

        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to verify file {input_file}: {e}")
        return False
    except ValueError as e:
        print(f"ERROR: Failed to parse duration for {input_file}: {e}")
        return False

def process_file(input_file, output_file, handbrake_command):
    try:
        # ... (keep existing code)

        # Verify the transcoded file
        if verify_file(input_file, output_file):
            print(f"Successfully transcoded and verified: {input_file}")
        else:
            print(f"WARNING: Verification failed for {input_file}")

    except Exception as e:
        print(f"ERROR - Error processing file {input_file}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Handbrake Transcoder CLI")
    parser.add_argument("-c", "--config", default=DEFAULT_CONFIG_FILE, help="Path to the config file")
    parser.add_argument("-i", "--input", help="Override input directory")
    parser.add_argument("-o", "--output", help="Override output directory")
    parser.add_argument("-t", "--threads", type=int, help="Number of concurrent transcoding threads")
    parser.add_argument("--delete-original", action="store_true", help="Delete original files after successful transcoding and verification")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Get default directories from config
    default_input_dir = config.get("input_directory", "")
    default_output_dir = config.get("output_directory", "")

    print("Welcome to the Handbrake Transcoder CLI")

    # Use config paths if not provided in command line arguments
    args.input = args.input or input(f"Enter input directory (default: {default_input_dir}): ") or default_input_dir
    args.output = args.output or input(f"Enter output directory (default: {default_output_dir}): ") or default_output_dir
    
    # Ensure user-specified directories exist
    ensure_directory_exists(args.input)
    ensure_directory_exists(args.output)

    if not args.threads:
        threads_input = input_with_timeout(f"Enter number of threads (default is {DEFAULT_THREADS}, {TIMEOUT}s timeout): ")
        args.threads = int(threads_input) if threads_input and threads_input.isdigit() else DEFAULT_THREADS

    delete_original = args.delete_original
    if not delete_original:
        delete_input = input_with_timeout(f"Delete original files after successful transcoding? (y/n, default is y, {TIMEOUT}s timeout): ")
        if delete_input is None:
            delete_original = True  # Default to deleting if no input
        else:
            delete_original = delete_input.lower() != 'n'

    # Update sys.argv to pass these arguments to HT_linuxbuild's main function
    sys.argv = [sys.argv[0]]  # Keep the script name
    sys.argv.extend(["-c", args.config])
    sys.argv.extend(["-i", args.input])
    sys.argv.extend(["-o", args.output])
    sys.argv.extend(["-t", str(args.threads)])
    if delete_original:
        sys.argv.append("--delete-original")

    print("Starting transcoding and verification process...")
    transcoder_main_function()
    print("Transcoding and verification completed!")

if __name__ == "__main__":
    main()
