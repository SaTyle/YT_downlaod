"""
YouTube Downloader - Streamlit app.

A single-file Streamlit UI over yt-dlp + ffmpeg. Paste a YouTube link,
pick a quality (1080p / 720p / ...) or grab audio as MP3, and download
at full speed. ffmpeg is used automatically to merge the separate video
and audio streams that YouTube serves for 1080p and above.

Run:  streamlit run streamlit_app.py
"""

import re
import threading
from pathlib import Path

import streamlit as st

try:
    import yt_dlp
except ImportError:
    st.error("yt-dlp is not installed. Run:  pip3 install -r requirements.txt")
    st.stop()

APP_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = APP_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Accept only real YouTube URLs.
YOUTUBE_RE = re.compile(
    r"^(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|live/|embed/)|youtu\.be/)",
    re.IGNORECASE,
)


def is_youtube_url(url: str) -> bool:
    return bool(url and YOUTUBE_RE.match(url.strip()))


def human_duration(seconds) -> str:
    if not seconds:
        return ""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins}:{secs:02d}"


@st.cache_data(show_spinner=False, ttl=600)
def fetch_info(url: str) -> dict:
    """Return title/thumbnail/duration/available heights. Cached per URL."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    heights = set()
    for fmt in info.get("formats", []):
        if fmt.get("vcodec") and fmt.get("vcodec") != "none":
            h = fmt.get("height")
            if h:
                heights.add(int(h))

    ladder = [2160, 1440, 1080, 720, 480, 360, 240, 144]
    available = [h for h in ladder if h in heights] or sorted(
        heights, reverse=True
    )

    return {
        "title": info.get("title", "video"),
        "thumbnail": info.get("thumbnail", ""),
        "uploader": info.get("uploader", ""),
        "duration": human_duration(info.get("duration")),
        "heights": available,
    }


def quality_label(h: int) -> str:
    if h >= 2160:
        return f"{h}p (4K)"
    if h >= 1440:
        return f"{h}p (2K)"
    return f"{h}p"


# --- Background download, driven into a thread-safe progress dict ---------


def run_download(url, height, audio_only, progress):
    """Runs in a worker thread. Writes live state into `progress` (a dict)."""
    outtmpl = str(DOWNLOAD_DIR / "%(title).200s [%(id)s].%(ext)s")

    def hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            progress["status"] = "downloading"
            progress["percent"] = (downloaded / total) if total else 0.0
            progress["speed"] = (d.get("_speed_str") or "").strip()
            progress["eta"] = (d.get("_eta_str") or "").strip()
        elif status == "finished":
            progress["status"] = "processing"
            progress["percent"] = 0.99

    if audio_only:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [hook],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    else:
        fmt = (
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )
        ydl_opts = {
            "format": fmt,
            "outtmpl": outtmpl,
            "noplaylist": True,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [hook],
            "concurrent_fragment_downloads": 5,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final = Path(ydl.prepare_filename(info))
            if audio_only:
                final = final.with_suffix(".mp3")
            elif final.suffix != ".mp4":
                mp4 = final.with_suffix(".mp4")
                if mp4.exists():
                    final = mp4
        progress["status"] = "done"
        progress["percent"] = 1.0
        progress["filepath"] = str(final)
        progress["title"] = info.get("title", "video")
    except Exception as exc:  # noqa: BLE001
        progress["status"] = "error"
        progress["error"] = str(exc)


# --- UI -------------------------------------------------------------------

st.set_page_config(page_title="YouTube Downloader", page_icon="⬇️", layout="centered")

st.markdown(
    """
    <style>
      .block-container { max-width: 760px; padding-top: 2.2rem; }
      .stProgress > div > div > div > div { background: linear-gradient(90deg,#ff0033,#ff5c7a); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⬇️ YouTube Downloader")
st.caption("Paste a link, pick a quality, download at full speed. Runs locally with yt-dlp + ffmpeg.")

# Session state
ss = st.session_state
ss.setdefault("info", None)
ss.setdefault("info_url", "")
ss.setdefault("progress", None)
ss.setdefault("worker", None)

url = st.text_input(
    "YouTube video URL",
    placeholder="https://www.youtube.com/watch?v=...",
    label_visibility="collapsed",
)

if st.button("Fetch video", type="primary", use_container_width=True):
    if not is_youtube_url(url):
        st.error("Please paste a valid YouTube video URL.")
    else:
        with st.spinner("Fetching video info…"):
            try:
                ss.info = fetch_info(url.strip())
                ss.info_url = url.strip()
                ss.progress = None  # reset any prior download
                ss.worker = None
            except Exception as exc:  # noqa: BLE001
                ss.info = None
                st.error(f"Could not read video: {exc}")

# Video details + controls
if ss.info:
    info = ss.info
    st.divider()
    col_img, col_meta = st.columns([1, 1.4])

    with col_img:
        if info["thumbnail"]:
            st.image(info["thumbnail"], use_container_width=True)
        if info["duration"]:
            st.caption(f"⏱️ Duration: {info['duration']}")

    with col_meta:
        st.subheader(info["title"])
        if info["uploader"]:
            st.caption(f"by {info['uploader']}")

        audio_only = st.checkbox("Audio only (MP3)")

        heights = info["heights"] or [720]
        default_idx = heights.index(1080) if 1080 in heights else 0
        height = st.selectbox(
            "Quality",
            options=heights,
            index=default_idx,
            format_func=quality_label,
            disabled=audio_only,
        )

        start = st.button("⬇️ Download", type="primary", use_container_width=True)

    # Start the background download
    if start and ss.worker is None:
        ss.progress = {"status": "starting", "percent": 0.0}
        worker = threading.Thread(
            target=run_download,
            args=(ss.info_url, int(height), audio_only, ss.progress),
            daemon=True,
        )
        # Streamlit >=1.12 needs the script run context attached for
        # the thread to interact cleanly; progress uses a plain dict so
        # this works regardless.
        worker.start()
        ss.worker = worker

# Progress / result
if ss.progress is not None:
    p = ss.progress
    status = p.get("status")

    if status in ("starting", "downloading", "processing"):
        bar = st.progress(0.0)
        info_line = st.empty()

        pct = p.get("percent", 0.0)
        bar.progress(min(max(pct, 0.0), 1.0))

        if status == "processing":
            info_line.info("Merging video + audio…")
        elif status == "downloading":
            bits = [f"{int(pct * 100)}%"]
            if p.get("speed"):
                bits.append(p["speed"])
            if p.get("eta"):
                bits.append("ETA " + p["eta"])
            info_line.write("  ·  ".join(bits))
        else:
            info_line.write("Starting…")

        # Auto-refresh while a download is in flight.
        try:
            st.autorefresh  # noqa: B018 - availability probe
        except AttributeError:
            pass
        # st_autorefresh via query-less rerun loop:
        import time as _time

        _time.sleep(0.6)
        st.rerun()

    elif status == "done":
        ss.worker = None
        bar = st.progress(1.0)
        st.success("Done! Your file is ready.")
        fpath = Path(p["filepath"])
        if fpath.exists():
            mime = "audio/mpeg" if fpath.suffix == ".mp3" else "video/mp4"
            with open(fpath, "rb") as fh:
                st.download_button(
                    "💾 Save file",
                    data=fh.read(),
                    file_name=fpath.name,
                    mime=mime,
                    type="primary",
                    use_container_width=True,
                )
            st.caption(f"Also saved in: {fpath}")
        else:
            st.error("File was reported done but not found on disk.")

    elif status == "error":
        ss.worker = None
        st.error("Download failed: " + p.get("error", "unknown error"))
        st.caption(
            "If this says you must sign in / confirm you're not a bot, or a "
            "format is unavailable, try updating yt-dlp:  pip3 install -U yt-dlp"
        )

st.divider()
st.caption(
    "Runs locally on your machine with yt-dlp + ffmpeg. "
    "For personal use — respect copyright and YouTube's Terms of Service."
)
