Default settings:

* Input = /home/user/media/trans_in
* Output = /home/user/media/trans_out
* H.264 video codec (Change in config.json. More in "Configuration" section)

<!-- ABOUT THE SCRIPT -->
## About the Script

Rapture-Transcoder is a simple and effecient way to transcode video files. It uses ffmpeg under the hood to transcode video files. It is designed to be run as a schedualed task or manually. I am not a python programmer, so forgive me if this is not up to python standards.


<!-- PREREQUISITES -->
## Prerequisites

1. Install Python
```sh
sudo apt install python3
```

2. (WINDOWS ONLY) Install and add ffmpeg to your PATH, follow this guide:
```sh
https://phoenixnap.com/kb/ffmpeg-windows
```

<!-- INSTALLATION -->
## Installation

1. Update your packages and libraries
```sh
sudo apt update && sudo apt upgrade -y
```

2. Install the Rapture-Transcoder repository by running 
```sh
git clone https://github.com/oliverdougherC/Rapture-Transcoder
```

3. Navigate to the Rapture-Transcoder directory
```sh
cd Rapture-Transcoder
```

4. Run the setup script
```sh
sudo ./setup
```


<!-- CONFIGURATION -->
## Configuration

1. If desired, change the transcoding settings in the *config.json* file. 
```sh
nano config.json
```


<!-- USAGE -->
## Usage

1. Run the script
```sh
./run
```

2. Select the option you want. 1 for runing the transcode service.

3. Sit back and relax while the script transcodes your videos.

4. If you run into an error or are just curious, take a look at the log file
```sh
cat logs/transcoding.log
```

The first time you run the script, the it will create the default directories specified in the *config.json* file if they do not exist.



