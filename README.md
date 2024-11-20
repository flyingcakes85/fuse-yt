# fuse-yt

A python script to let browse YouTube channels via your file manager.

## Usage

Copy `.env.example` to `.env` and set the variables:

- Get your YouTube API keys form [Google Cloud Console](https://console.cloud.google.com). Add it to `.env`
- Also set a cache directory for thumbnails to `.env`

Now simply run the script with an argument for folder where to mount the filesystem.

```sh
mkdir YouTube
python yt.py YouTube
```

Inside the folder `yt`, you can create folder and give it a name same as the id of the channel you wish to browse. Once you've done this, inside the folder you'll see the fifty most recent videos from the channel.
