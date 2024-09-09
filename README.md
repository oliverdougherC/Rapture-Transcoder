Default settings:

* Input = ${HOME}/Documents/media/transcode_input
* Output = ${HOME}/Documents/media/transcode_output
* Apple Video Toolbox H.265 10-bit codec
* Up to 8K max resolution
* Up to 120fps
* All English & Japanese audio
* All English subtitles
* 320 kbps audio bitrate
* "Quality" video preset

<!-- ABOUT THE SCRIPT -->
## About the Script

Rapture-Transcoder is a simple and effecient way to transcode video files. It uses HandbrakeCLI under the hood to transcode video files. It is designed to be run as a schedualed task or manually. It was initially designed to be a CLI program, but I have since added a GUI to make it more user friendly. I am not a python programmer, so forgive me if this is not up to python standards.


<!-- PREREQUISITES -->
## Prerequisites

1. Update your packages and libraries
```sh
sudo softwareupdate -l
```

2. Install Homebrew
```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

3. Run the commands prompted by Homebrew to add it to your PATH

4. Install Python
```sh
brew install python
```

5. Install ffmpeg
```sh
brew install ffmpeg
```


<!-- INSTALLATION -->
## Installation

1. Install the Rapture-Transcoder script in whatever directory you want
```sh
git clone -b MacOS --single-branch https://github.com/oliverdougherC/Rapture-Transcoder
```
2. Navigate to the Rapture-Transcoder directory
```sh
cd Rapture-Transcoder
```

<!-- CONFIGURATION -->
## Configuration

1. If desired, change the settings in the "config.json"
```sh
nano config.json
```

2. If desired, you can tune the transcode settings further in the preset file. Refer to config.json for which file is selected. Default is "AppleSilicon.json"
```sh
nano Presets/AppleSilicon.json
```




<!-- USAGE -->
## Usage

1. Run the script in CLI mode or GUI mode
```sh
python3 transcode_cli.py
```
```sh
python3 transcode_gui.py
```

2. Follow the prompts to select your input and output directories.

3. Alternatively, you can pass optional flags onto the launch command:

* -i = Input Directory
* -o = Output Directory
* -t = Number of threads per job
* --delete-original = Delete original files after successful transcoding

For example:
```sh
python3 transcode_cli.py -i /path/to/input -o /path/to/output -t number_of_threads --delete-original
```

4. Follow the prompts to select your profile.

5. Wait for the script to transcode your video(s).

6. If you run into an error or are curious, take a look at the log file
```js
cat transcoder.log
```


