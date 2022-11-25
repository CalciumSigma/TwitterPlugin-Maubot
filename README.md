# TwitterPlugin-Maubot
Responds to Twitter posts with tweet username, text, and attached images/videos

## Usage
- Needs cv2, imageio, and pillow modules
- Compile yourself, or download Prepackaged version from releases
- Upload to Maubot manager, and insert Twitter API key in config
## Features
- Sending tweets and usernames as text
- Sending pictures from tweets
- Sending videos/GIFS from tweets, with the correct file dimensions
- Config settings for which parts of the tweets will be sent
## TODO
- Improve implementation for sending GIFS
## NOTICE for maubot docker container users
The maubot docker container isn't setup correctly to install the required pip packages. So these will need to be run before installing the necessary pip packages (may not be a complete set of commands)
1. apk add gcc g++ linux-headers python3-dev ninja
1. pip install --upgrade pip setuptools wheel
