# YouTube Downloader

A local web app to download YouTube videos at 1080p, 720p, and other
qualities — or extract audio as MP3. Paste a link, pick a quality, download
at full speed.

It's a small **Streamlit** app that runs [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
and [`ffmpeg`](https://ffmpeg.org/) under the hood. (A browser alone can't
download YouTube videos — YouTube's streams are encrypted and 1080p needs
video + audio merged with ffmpeg. That's why it runs as a local app.)

## Requirements

- Python 3.9+
- `ffmpeg` (for merging 1080p/720p video + audio and MP3 conversion)

On macOS: `brew install ffmpeg`

## Setup

```bash
cd YT_downlaod
pip3 install -r requirements.txt
```

## Run

**Easiest — double-click** `Start YouTube Downloader.command` in Finder.
It installs anything missing and opens the app in your browser.

**Or from the terminal:**

```bash
./run.sh
```

**Or directly:**

```bash
streamlit run streamlit_app.py
```

It opens in your browser automatically (usually http://localhost:8501).

> **Run it on your own machine.** This works because your home internet
> connection is what YouTube accepts. Hosting it on a cloud server
> (Streamlit Cloud, Heroku, etc.) does **not** work reliably — YouTube
> blocks datacenter IPs with `HTTP 403 Forbidden` / "confirm you're not a
> bot", and public downloaders also violate those hosts' and YouTube's
> terms. Keep it local.

## How to use

1. Paste a YouTube video link and click **Fetch**.
2. Pick a quality (1080p, 720p, etc.) — only the qualities that video
   actually has are shown. Or tick **Audio only (MP3)**.
3. Click **Download**. Watch the progress bar (speed + ETA shown live).
4. When it's done, click **Save file** to save it to your computer.

Downloaded files are also kept in the `downloads/` folder.

## Notes

- This runs only on your own machine (`localhost`) — it's not exposed to the
  internet.
- Keep `yt-dlp` up to date so it keeps working when YouTube changes:
  `pip3 install -U yt-dlp`
- For personal use only. Respect copyright and YouTube's Terms of Service.
  Don't download content you don't have the right to.
