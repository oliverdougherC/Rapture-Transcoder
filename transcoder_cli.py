import os
import sys
import argparse
import json
import threading
import time

# Add the directory containing HT_linuxbuild.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from HT_linuxbuild import main as transcoder_main_function

# Default values
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_THREADS = 4
TIMEOUT = 20  # Timeout in seconds

def load_config(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

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
    default_input_dir = config.get("default_input_directory", "")
    default_output_dir = config.get("default_output_directory", "")

    # Convert paths to the correct format for the current OS
    default_input_dir = os.path.expanduser(default_input_dir)
    default_output_dir = os.path.expanduser(default_output_dir)

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
