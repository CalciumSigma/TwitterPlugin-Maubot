import re, json, mimetypes
import imageio
from typing import Type
import cv2
from urllib.request import Request, urlopen
from mautrix.types import VideoInfo, ImageInfo, EventType, MessageType
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from maubot.handlers import event


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("Twitter_API_Key")
        helper.copy("Send_videos")
        helper.copy("Send_photos")
        helper.copy("Send_text")

twitter_pattern = re.compile(r"^(?:https?:\/\/)?(?:(?:www|m)\.)?(?:(?:vx|fx)?twitter\.com)(?:\/.*\/status\/)(\d+)(?:\?.*)?$")
image_pattern = re.compile(r"^(?:https?:\/\/)(?:pbs\.)(?:twimg\.com\/)(?:media\/)(.*)$")
video_pattern = re.compile(r"(?:https?:\/\/)(?:video\.)(?:twimg\.com\/)(?:(?:tweet_video\/)|(?:\w+\/\d+\/(?:pu\/)?vid\/\w+\/))([^.?]+\.\w+)(?:\?.*)?")
video_url_pattern = re.compile(r"(https?:\/\/video\.twimg\.com\/\w+\/(?:\d+\/(?:pu\/)?vid\/\w+\/)?[^.?]+.\w+)(?:\?.*)?")
stored_media_pattern = re.compile(r"(?:mxc:\/\/)((.*\/)(?:\w+))")

class TwitterPostPlugin(Plugin):
    async def start(self) -> None:
        self.config.load_and_update()

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    @event.on(EventType.ROOM_MESSAGE)
    async def on_message(self, evt: MessageEvent) -> None:
        if evt.content.msgtype != MessageType.TEXT or evt.content.body.startswith("!"):
            return
        for url_tup in twitter_pattern.findall(evt.content.body):

            # Make Twitter API HTTP string, and check if valid response
            await evt.mark_read()
            tweet_id = ''.join(url_tup)
            query_url = "https://api.twitter.com/2/tweets?ids=" + (tweet_id) + \
                        "&expansions=attachments.media_keys,author_id&media.fields=media_key,type,variants,url&user.fields=profile_image_url"
            headers = {'Authorization': 'Bearer ' + self.config["Twitter_API_Key"]}
            req = Request(query_url, headers=headers)
            response = urlopen(req)

            if response.status != 200:
                self.log.warning(f"Unexpected status fetching Twitter Post {query_url}: {response.status}")
                return None

            # Start reading HTTP response as json to get tweet info
            json_str = json.loads(response.read().decode())

            # Send Tweet Username and text
            if self.config["Send_text"] == True:
                for user_info in json_str['includes']['users']:
                    if user_info['id'] == json_str['data'][0]['author_id']:
                        profile_url = user_info['profile_image_url']
                        display_name = user_info['name']
                        user_name = user_info['username']
                await evt.respond(display_name + " (@" + user_name + ")")

                text = (json_str['data'][0]['text'])
                await evt.respond(text)

            # Send Tweet videos and pictures
            for media_info in json_str['includes']['media']:
                # Check for videos, get link and file extension of highest quality file
                if media_info['type'] == "video" and self.config["Send_videos"] == True:
                    for video_object in media_info['variants'][::-1] :
                        if video_object['content_type'] == 'video/mp4' :
                            self.log.info(f"URL{video_object['url']}")
                            media_url = video_url_pattern.findall(video_object['url'])[0]
                            media_name = video_pattern.findall(video_object['url'])[0]
                            mime_type = mimetypes.guess_type(media_name)[0]
                            break
                # Check for GIFS
                elif media_info['type'] == "animated_gif" and self.config["Send_videos"] == True:
                    for video_object in media_info['variants'][::-1] :
                        if video_object['content_type'] == 'video/mp4' :
                            media_url = video_url_pattern.findall(video_object['url'])[0]
                            media_name = video_pattern.findall(video_object['url'])[0] + ".gif"
                            mime_type = mimetypes.guess_type(media_name)[0]
                            break
                # Check for pictures, get link and file extension
                elif media_info['type'] == "photo" and self.config["Send_photos"]:
                    media_url = (media_info['url'])
                    media_name = image_pattern.search(media_info['url'])[0]
                    mime_type = mimetypes.guess_type(media_url)[0]
                # Unknown file type, return warning
                else :
                    self.log.warning(f"Unexpected media type {media_info['type']}, tweet ID {tweet_id}")
                    return None

                # Get the file
                response = await self.http.get(media_url)
                if response.status != 200:
                    self.log.warning(f"Unexpected status fetching media {media_url}: {response.status}")
                    return None

                file_name = media_name
                self.log.info(f"media name: {media_name} {mime_type}")
                media = await response.read()

                #Initial testing of sending Twitter GIFs..... as a GIF
                if "image/gif" in mime_type:
                    image_lst = []
                    cap = cv2.VideoCapture(media_url)
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    success = True
                    while success:
                        success, image = cap.read()
                        if success:
                            frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                            image_lst.append(frame_rgb)
                    bytes_image = imageio.mimwrite('<bytes>', image_lst, format=".gif", fps=fps)
                    uri = await self.client.upload_media(bytes_image, mime_type=mime_type, filename=file_name)
                    await self.client.send_image(evt.room_id, url = uri, file_name=file_name, info=ImageInfo(mimetype=mime_type))
                # Send message with Image
                elif "image" in mime_type:
                    uri = await self.client.upload_media(media, mime_type=mime_type, filename=file_name)
                    await self.client.send_image(evt.room_id, url=uri, file_name=file_name,
                                                 info=ImageInfo(mimetype=mime_type))
                # Send video, getting height and width of video file
                elif "video" in mime_type:
                    uri = await self.client.upload_media(media, mime_type=mime_type, filename=file_name)
                    uri_parts = stored_media_pattern.findall(uri)
                    url = "https://" + uri_parts[0][1] + "_matrix/media/r0/download/" + uri_parts[0][0]
                    vid = cv2.VideoCapture(url)
                    height = vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    width = vid.get(cv2.CAP_PROP_FRAME_WIDTH)
                    await self.client.send_file( evt.room_id, url=uri,
                                                info=VideoInfo(height=int(height), width=int(width), mimetype=mime_type, size=len(media)),
                                                file_name=file_name, file_type=MessageType.VIDEO )
                # Error for unknown media type
                else:
                    self.log.warning(f"Unknown media type {query_url}: {mime_type}")
                    return None
