Default settings:

* Input = /home/user/media/transcode_input
* Output = /home/user/media/transcode_output
* H.264 video codec (Change in config.json. More in "Configuration" section)
* Up to 8K max resolution
* Up to 120fps
* All English & Japanese audio
* All English subtitles
* 320 kbps audio bitrate
* "Slowest" video preset

<!-- ABOUT THE SCRIPT -->
## About the Script

Rapture-Transcoder is a simple and effecient way to transcode video files. It uses HandbrakeCLI under the hood to transcode video files. It is designed to be run as a schedualed task or manually. It was initially designed to be a CLI program, but I have since added a GUI to make it more user friendly. I am not a python programmer, so forgive me if this is not up to python standards.


<!-- PREREQUISITES -->
## Prerequisites

1. Install HandbrakeCLI on your system. You can do this by running
```sh
sudo apt install handbrake-cli
```
2. Install Python on your system. You can this by running 
```sh
sudo apt install python3
```
3. Install ffmpeg
```sh
sudo apt install ffmpeg
```

<!-- INSTALLATION -->
## Installation

1. Update your packages and libraries
```sh
sudo apt update && sudo apt upgrade -y
```

2. Install the Rapture-Transcoder script by running 
```sh
git clone https://github.com/oliverdougherC/Rapture-Transcoder
```
3. Navigate to the Rapture-Transcoder directory
```sh
cd Rapture-Transcoder
```

<!-- CONFIGURATION -->
## Configuration

1. If desired, change the transcoding settings in the *H.264.json* and general settings in the *config.json* files. 
```sh
nano H.264.json
```
```sh
nano config.json
```

2. The default codec is H.264 as to maximize compatibility. Take a look at the presets in the "Presets" folder in order to select which preset is best suited for your needs. You may also change the setting "prioritize_config" to *true* in *config.json* in order to prioritize the config settings over the preset settings. This lets you change the encoder, quality, and encoder preset in config.json. If you would like to fine tune your transcoding settings, I would recommend creating your own preset using the Handbrake GUI and then exporting it as a JSON file and placing it in the "Presets" folder. This will allow you to select your own preset in the config.json file.


<!-- USAGE -->
## Usage

1. Run the script
```sh
python3 run_transcode.py
```
2. Follow the prompts to select your input and output directories. Alternatively, you can add the -i and -o flags to the launch command to set the input and output directories. You can also add the -t flag to set the number of threads to use.
```sh
python3 run_transcode.py -i /path/to/input -o /path/to/output -t number_of_threads
```
3. Follow the prompts to select your profile.
4. Sit back and relax while the script transcodes your videos.
5. If you run into an error or are curious, take a look at the log file
```sh
cat transcoder.log
```


