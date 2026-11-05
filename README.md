# YouTube Downloader

A local web app to download YouTube videos at 1080p, 720p, and other
qualities — or extract audio as MP3. Paste a link, pick a quality, download
at full speed.

It's a small **Flask** website that runs [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
and [`ffmpeg`](https://ffmpeg.org/) under the hood. (A browser alone can't
download YouTube videos — YouTube's streams are encrypted and 1080p needs
video + audio merged with ffmpeg. That's why there's a small backend.)

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

There are two versions — use whichever you prefer:

**Streamlit (recommended, single file):**

```bash
streamlit run streamlit_app.py
```

It opens in your browser automatically (usually http://localhost:8501).

**Flask (HTML/CSS/JS version):**

```bash
python3 app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## How to use

1. Paste a YouTube video link and click **Fetch**.
2. Pick a quality (1080p, 720p, etc.) — only the qualities that video
   actually has are shown. Or tick **Audio only (MP3)**.
3. Click **Download**. Watch the progress bar (speed + ETA shown live).
4. When it's done, click **Save file** to save it to your computer.

Downloaded files are also kept in the `downloads/` folder.

## Notes

- This runs only on your own machine (`127.0.0.1`) — it's not exposed to the
  internet.
- Keep `yt-dlp` up to date so it keeps working when YouTube changes:
  `pip3 install -U yt-dlp`
- For personal use only. Respect copyright and YouTube's Terms of Service.
  Don't download content you don't have the right to.
