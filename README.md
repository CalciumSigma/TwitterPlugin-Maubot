# TwitterPlugin-Maubot
Responds to Twitter posts with teet username, text, and attached images/videos

## Usage
- Needs cv2 module
- Compile yourself (Will release prepackaged versions when code is in a state I deem reasonable)
- Upload to Maubot manager, and insert Twitter API key in config
## What works
Videos and GIFs, but only sometimes. GIFS don't work on mobile (this has to do with how twitter gifs are saved on twitter's servers), and I need to get a better way to get media URLS once uploaded to the server.
## TODO
- Find a better way to get full url of file after uploading to server
- Massively clean the code
- Fix GIFS for mobile devices (maybe) (perhaps need to convert file before upload)
