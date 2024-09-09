Default settings:

* Input = /home/user/media/transcode_input
* Output = /home/user/media/transcode_output
* AV1 10bit nvenc video codec
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

1. Update your packages and libraries
```js
sudo softwareupdate -l
```

2. Install Homebrew
```js
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

3. Install Python
```js
brew install python
```

4. Install ffmpeg
```js
brew install ffmpeg
```


<!-- INSTALLATION -->
## Installation

1. Install the Rapture-Transcoder script in whatever directory you want
```js
git clone https://github.com/oliverdougherC/Rapture-Transcoder
```
2. Navigate to the Rapture-Transcoder directory
```js
cd Rapture-Transcoder
```

<!-- CONFIGURATION -->
## Configuration

1. If desired, change the transcoding settings in the "Streaming.json" and general settings in the "config.json" files
```js
nano Streaming.json
```
```js
nano config.json
```


<!-- USAGE -->
## Usage

1. Run the script in CLI mode or GUI mode
```js
python3 transcode_cli.py
```
```js
python3 transcode_gui.py
```

2. Follow the prompts to select your input and output directories. Alternatively, you can add the -i and -o flags to the launch command to set the input and output directories. You can also add the -t flag to set the number of threads to use.
```js
python3 transcode_cli.py -i /path/to/input -o /path/to/output -t number_of_threads
```

3. Follow the prompts to select your profile.

4. Sit back and relax while the script transcodes your videos.

5. If you run into an error or are curious, take a look at the log file
```js
cat transcoder.log
```


