import stat, errno, sys, os
import os.path
from fuse import Fuse
import fuse
import requests
from dotenv import load_dotenv

load_dotenv()


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

    def _get_videos(self, channel_id: str):
        if not channel_id in self._channel_list():
            return b""

        if "_channel" + channel_id in self.DATA_STORE:
            return self.DATA_STORE["_channel" + channel_id]

        uploads_playlist_id = (
            requests.get(
                f"https://www.googleapis.com/youtube/v3/channels?forHandle={channel_id}&key={self.YT_API_KEY}&part=contentDetails",
                timeout=15,
            )
            .json()
            .get("items")[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        )

        videos = requests.get(
            f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=50&key={self.YT_API_KEY}",
            timeout=15,
        ).json()["items"]

        for v in videos:
            if not os.path.isfile(
                f"{self.CACHE_FOLDER}/{v["snippet"]["resourceId"]["videoId"]}.jpg"
            ):
                print(v["snippet"]["thumbnails"]["default"])
                thumb = requests.get(
                    v["snippet"]["thumbnails"]["default"]["url"],
                    timeout=15,
                )
                with open(
                    f"{self.CACHE_FOLDER}/{v["snippet"]["resourceId"]["videoId"]}.jpg",
                    "wb",
                ) as f:
                    f.write(thumb.content)
            else:
                print("skip thumbnail dowload")

        self.DATA_STORE["_channel" + channel_id] = videos
        return videos

    def readdir(self, path: str, _offset: int):
        contents = [".", ".."]
        if path == "/":
            contents.extend(self._channel_list())
            contents.append("files")

        elif path == "/files":
            contents.append("README.md")

        # elif path.startswith("/@"):
        else:
            print("CHANNEL")
            channel_name = path.split("/")[1]
            videos = self._get_videos(channel_name)
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

    def read(self, path: str, _size: int, _offset: int) -> bytes:
        if path == "/files/README.md":
            return b"readme.md file"
        try:
            idx = path[1:].index("/")
            channel_id = path[1 : idx + 1]
            video_name = path[idx + 2 :]
            print(channel_id)
            video_name = path.split("/")[2]
            video_id = video_name[:11]
            file_contents = f"""[Desktop Entry]

Type=Application

Name={video_name[12:-8]}
Exec=mpv --ytdl-raw-options=paths=/tmp ytdl://{video_id}
Icon=preferences-desktop
Icon={self.CACHE_FOLDER}/{video_id}.jpg

Comment=

Categories=Video;
Keywords=youtube;

RunInTerminal=true
NoDisplay=false
"""
            return bytes(file_contents, "utf-8")
        except ValueError:
            return -errno.ENOENT

    def mkdir(self, path: str, mode: str):
        parent_dir, new_channel = os.path.split(path)

        if parent_dir != "/":
            return -errno.ENOENT

        if new_channel in self._channel_list():
            return errno.EEXIST

        self.CHANNEL_LIST.append(new_channel)

    def rename(self, pathfrom: str, pathto: str):
        parent_dir, old_name = os.path.split(pathfrom)

        if parent_dir != "/":
            return -errno.ENOENT

        parent_dir, new_name = os.path.split(pathto)

        if parent_dir != "/":
            return -errno.ENOENT

        for i in range(len(self.CHANNEL_LIST)):
            print(i)
            if self.CHANNEL_LIST[i] == old_name:
                self.CHANNEL_LIST[i] = new_name
                break
            i = i + 1


def main():
    if len(sys.argv) == 1:
        sys.argv.append("--help")

    title = "YouTube browser via FUSE"
    description = "A filesystem that browses YouTube channels and plays videos"

    # usage = "\n\nBeginning FUSE\n  %s: %s\n\n%s\n\n%s" % (
    #     sys.argv[0],
    #     title,
    #     description,
    #     fuse.Fuse.fusage,
    # )

    usage = f"\n\nBeginning FUSE\n  {sys.argv[0]}: {title}\n\n{description}\n\n{fuse.Fuse.fusage}"

    server = YTFUSE(
        version="%prog " + fuse.__version__, usage=usage, dash_s_do="setsingle"
    )

    server.parse(errex=1)
    server.main()


if __name__ == "__main__":
    main()
