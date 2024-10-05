import subprocess
import sys

def run_command(command):
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{command}': {e}")
        sys.exit(1)

def check_and_install_meson():
    try:
        subprocess.run(["meson", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Meson not found. Installing...")
        run_command("pip install meson")

def check_and_install_ninja():
    try:
        subprocess.run(["ninja", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Ninja not found. Installing...")
        if sys.platform.startswith('linux'):
            run_command("sudo apt-get update && sudo apt-get install -y ninja-build")
        elif sys.platform == 'darwin':
            run_command("brew install ninja")
        else:
            print("Automatic Ninja installation not supported on this platform. Please install manually.")
            sys.exit(1)

def check_and_install_cairo():
    if sys.platform.startswith('linux'):
        run_command("sudo apt-get update && sudo apt-get install -y libcairo2-dev")
    elif sys.platform == 'darwin':
        run_command("brew install cairo")
    else:
        print("Automatic Cairo installation not supported on this platform. Please install manually.")
        sys.exit(1)

def main():
    check_and_install_meson()
    check_and_install_ninja()
    check_and_install_cairo()
    
    print("Installing Python requirements...")
    run_command("pip install -r requirements.txt")

if __name__ == "__main__":
    main()