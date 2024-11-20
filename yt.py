import stat, errno, fuse, sys, os
import os.path
import requests
from dotenv import load_dotenv

load_dotenv()

from fuse import Fuse

fuse.fuse_python_api = (0, 2)


try:
    os.mkdir(os.getenv("CACHE_FOLDER"))
except:
    print("folder exists")
    # absolutely the wrong way of doing it


class YTFUSE(Fuse):
    YT_API_KEY = os.getenv("YT_API_KEY")
    DATA_STORE = {}
    CHANNEL_LIST = ["@flyingcakes85"]
    CACHE_FOLDER = os.getenv("CACHE_FOLDER")

    def _channel_list(self):
        return self.CHANNEL_LIST

    def _get_videos(self, channelId: str):
        if not channelId in self._channel_list():
            return b""

        if "_channel" + channelId in self.DATA_STORE:
            return self.DATA_STORE["_channel" + channelId]

        uploadsPlaylistId = (
            requests.get(
                f"https://www.googleapis.com/youtube/v3/channels?forHandle={channelId}&key={self.YT_API_KEY}&part=contentDetails"
            )
            .json()
            .get("items")[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        )

        videos = requests.get(
            f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploadsPlaylistId}&maxResults=50&key={self.YT_API_KEY}"
        ).json()["items"]

        for v in videos:
            if not os.path.isfile(
                f"{self.CACHE_FOLDER}/{v["snippet"]["resourceId"]["videoId"]}.jpg"
            ):
                print(v["snippet"]["thumbnails"]["default"])
                thumb = requests.get(v["snippet"]["thumbnails"]["default"]["url"])
                with open(
                    f"{self.CACHE_FOLDER}/{v["snippet"]["resourceId"]["videoId"]}.jpg",
                    "wb",
                ) as f:
                    f.write(thumb.content)
            else:
                print("skip thumbnail dowload")

        self.DATA_STORE["_channel" + channelId] = videos
        return videos

    def readdir(self, path: str, offset: int):
        contents = [".", ".."]
        if path == "/":
            contents.extend(self._channel_list())
            contents.append("files")

        elif path == "/files":
            contents.append("README.md")

        # elif path.startswith("/@"):
        else:
            print("CHANNEL")
            channelName = path.split("/")[1]
            videos = self._get_videos(channelName)
            print("LENGTH OF VIDEOS" + str(len(videos)))
            for v in videos:
                contents.append(
                    v["snippet"]["resourceId"]["videoId"]
                    + "_"
                    + v["snippet"]["title"].replace("/", " ")
                    + ".desktop"
                )

        for r in contents:
            print(r)
            yield fuse.Direntry(r)

    def getattr(self, path: str) -> fuse.Stat:
        st = fuse.Stat()

        dirs = ["/%s" % i for i in self._channel_list()]
        dirs.extend("/")
        if path in dirs or path == "/files":
            st.st_mode = stat.S_IFDIR | 0o555
            st.st_nlink = 2
            return st

        if path == "/files/README.md":
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            st.st_size = 512
            return st

        if path.endswith(".desktop"):
            st.st_mode = (
                stat.S_IFREG
                | stat.S_IRWXU
                | stat.S_IRGRP
                | stat.S_IXGRP
                | stat.S_IROTH
                | stat.S_IXOTH
                | stat.S_IEXEC
                | stat.S_IREAD
            )
            st.st_nlink = 1
            st.st_size = 512
            return st

        try:
            idx = path[1:].index("/")
            channel = path[1 : idx + 1]
            if channel in self._channel_list():
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                st.st_size = 512
                return st
        except ValueError:
            return -errno.ENOENT

        # Path does not match any known file objects
        return -errno.ENOENT

    def read(self, path: str, size: int, offset: int) -> bytes:
        if path == "/files/README.md":
            return b"readme.md file"
        try:
            idx = path[1:].index("/")
            channelId = path[1 : idx + 1]
            videoName = path[idx + 2 :]
            print(channelId)
            videoName = path.split("/")[2]
            videoId = videoName[:11]
            fileContents = f"""[Desktop Entry]

Type=Application

Name={videoName[12:-8]}
Exec=mpv --ytdl-raw-options=paths=/tmp ytdl://{videoId}
Icon=preferences-desktop
Icon={self.CACHE_FOLDER}/{videoId}.jpg

Comment=

Categories=Video;
Keywords=youtube;

RunInTerminal=true
NoDisplay=false
"""
            return bytes(fileContents, "utf-8")
        except ValueError:
            return -errno.ENOENT

    def mkdir(self, path: str, mode: str):
        parentDir, newChannel = os.path.split(path)

        if parentDir != "/":
            return -errno.ENOENT

        if newChannel in self._channel_list():
            return errno.EEXIST

        self.CHANNEL_LIST.append(newChannel)

    def rename(self, pathfrom: str, pathto: str):
        parentDir, oldName = os.path.split(pathfrom)

        if parentDir != "/":
            return -errno.ENOENT

        parentDir, newName = os.path.split(pathto)

        if parentDir != "/":
            return -errno.ENOENT

        for i in range(len(self.CHANNEL_LIST)):
            print(i)
            if self.CHANNEL_LIST[i] == oldName:
                self.CHANNEL_LIST[i] = newName
                break
            i = i + 1


def main():
    if len(sys.argv) == 1:
        sys.argv.append("--help")

    title = "YouTube browser via FUSE"
    description = "A filesystem that browses YouTube channels and plays videos"

    usage = "\n\nBeginning FUSE\n  %s: %s\n\n%s\n\n%s" % (
        sys.argv[0],
        title,
        description,
        fuse.Fuse.fusage,
    )

    server = YTFUSE(
        version="%prog " + fuse.__version__, usage=usage, dash_s_do="setsingle"
    )

    server.parse(errex=1)
    server.main()


if __name__ == "__main__":
    main()
