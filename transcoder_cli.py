import os
import sys
import argparse
import select

# Add the directory containing HT_linuxbuild.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from HT_linuxbuild import main as transcoder_main_function

# Default paths
USER = os.getenv('USER')
DEFAULT_INPUT_DIR = f"/home/{USER}/media/transcode_input"
DEFAULT_OUTPUT_DIR = f"/home/{USER}/media/transcode_output"
DEFAULT_THREADS = 4
TIMEOUT = 20  # Timeout in seconds

def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def input_with_timeout(prompt, timeout=TIMEOUT):
    print(prompt, end='', flush=True)
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        return sys.stdin.readline().strip()
    else:
        print("\nTimeout reached. Using default value.")
        return None

def main():
    # Ensure default directories exist
    ensure_directory_exists(DEFAULT_INPUT_DIR)
    ensure_directory_exists(DEFAULT_OUTPUT_DIR)

    parser = argparse.ArgumentParser(description="Handbrake Transcoder CLI")
    parser.add_argument("-c", "--config", default="config.json", help="Path to the config file")
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT_DIR, help="Override input directory")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_DIR, help="Override output directory")
    parser.add_argument("-t", "--threads", type=int, help="Number of concurrent transcoding threads")
    parser.add_argument("--delete-original", action="store_true", help="Delete original files after successful transcoding and verification")
    args = parser.parse_args()

    print("Welcome to the Handbrake Transcoder CLI")

    # Use default paths if not provided
    args.input = args.input or input(f"Enter input directory (default: {DEFAULT_INPUT_DIR}): ") or DEFAULT_INPUT_DIR
    args.output = args.output or input(f"Enter output directory (default: {DEFAULT_OUTPUT_DIR}): ") or DEFAULT_OUTPUT_DIR
    
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
