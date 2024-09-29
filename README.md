Default settings:

* Input = ${HOME}/Documents/media/trans_in
* Output = ${HOME}/Documents/media/trans_out
* Apple Video Toolbox H.264 codec
* 18 quality preset
* Media detection disabled

<!-- ABOUT THE SCRIPT -->
## About the Script

Rapture-Transcoder for Mac is a simple and effecient way to transcode video files. It uses ffmpeg under the hood to transcode video files. It is designed to be run as a schedualed task or manually.


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

*Note: If you would like to use the media detection feature, you will need to set "use_media_detection" to true. This will use the omdb api to detect the media type and output to the respective movie or tv directory. You will also need to supply your omdb api key. You can get one [here](https://www.omdbapi.com/apikey.aspx)*


<!-- USAGE -->
## Usage

1. Run the script
```sh
python3 run_transcode.py
```

2. Wait for the script to transcode your video(s).

3. If you run into an error or are curious, take a look at the log file
```js
cat logs/transcoding.log
```


