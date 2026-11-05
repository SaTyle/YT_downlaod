"""
YouTube Downloader - Flask backend.

Uses yt-dlp to fetch video info and download at a chosen quality.
ffmpeg is used automatically by yt-dlp to merge separate video+audio
streams (needed for 1080p and above).

Run:  python3 app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import re
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

try:
    import yt_dlp
except ImportError:
    raise SystemExit(
        "yt-dlp is not installed. Run:  pip3 install -r requirements.txt"
    )

APP_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = APP_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

# In-memory job registry: job_id -> progress dict.
# For a personal/local tool this is fine; it resets when the server restarts.
JOBS = {}
JOBS_LOCK = threading.Lock()

# Accept only real YouTube URLs. Keeps the tool from being pointed at
# arbitrary hosts.
YOUTUBE_RE = re.compile(
    r"^(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|live/|embed/)|youtu\.be/)",
    re.IGNORECASE,
)


def is_youtube_url(url: str) -> bool:
    return bool(url and YOUTUBE_RE.match(url.strip()))


def _set_job(job_id: str, **fields):
    with JOBS_LOCK:
        job = JOBS.setdefault(job_id, {})
        job.update(fields)


def _get_job(job_id: str):
    with JOBS_LOCK:
        return dict(JOBS.get(job_id, {}))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def api_info():
    """Return title, thumbnail, duration and available video heights."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not is_youtube_url(url):
        return jsonify({"error": "Please paste a valid YouTube video URL."}), 400

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to UI
        return jsonify({"error": f"Could not read video: {exc}"}), 400

    # Collect the distinct video heights actually available for this video.
    heights = set()
    for fmt in info.get("formats", []):
        if fmt.get("vcodec") and fmt.get("vcodec") != "none":
            h = fmt.get("height")
            if h:
                heights.add(int(h))

    # Common, sensible ladder; only offer what the video actually has.
    ladder = [2160, 1440, 1080, 720, 480, 360, 240, 144]
    available = [h for h in ladder if h in heights]
    if not available:
        available = sorted(heights, reverse=True)

    duration = info.get("duration")
    if duration:
        mins, secs = divmod(int(duration), 60)
        hours, mins = divmod(mins, 60)
        duration_str = (
            f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins}:{secs:02d}"
        )
    else:
        duration_str = ""

    return jsonify(
        {
            "title": info.get("title", "video"),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", ""),
            "duration": duration_str,
            "heights": available,
        }
    )


def _progress_hook(job_id):
    def hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total else 0
            _set_job(
                job_id,
                status="downloading",
                percent=round(pct, 1),
                speed=d.get("_speed_str", "").strip(),
                eta=d.get("_eta_str", "").strip(),
            )
        elif status == "finished":
            # Download of one stream done; merge (if any) happens next.
            _set_job(job_id, status="processing", percent=99.0)

    return hook


def _run_download(job_id, url, height, audio_only):
    outtmpl = str(DOWNLOAD_DIR / "%(title).200s [%(id)s].%(ext)s")

    if audio_only:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [_progress_hook(job_id)],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    else:
        # Pick best video at or below the requested height + best audio,
        # fall back gracefully. Merge into mp4 (needs ffmpeg).
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
            "progress_hooks": [_progress_hook(job_id)],
            # Speeds up large downloads by fetching in parallel chunks.
            "concurrent_fragment_downloads": 5,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            final = Path(filename)
            # After postprocessing the extension can change (e.g. .mp3/.mp4).
            if audio_only:
                final = final.with_suffix(".mp3")
            elif final.suffix != ".mp4":
                mp4 = final.with_suffix(".mp4")
                if mp4.exists():
                    final = mp4

        _set_job(
            job_id,
            status="done",
            percent=100.0,
            filename=final.name,
            title=info.get("title", "video"),
        )
    except Exception as exc:  # noqa: BLE001
        _set_job(job_id, status="error", error=str(exc))


@app.route("/api/download", methods=["POST"])
def api_download():
    """Start a download in the background and return a job id."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    height = int(data.get("height") or 720)
    audio_only = bool(data.get("audio_only"))

    if not is_youtube_url(url):
        return jsonify({"error": "Please paste a valid YouTube video URL."}), 400

    job_id = uuid.uuid4().hex
    _set_job(job_id, status="starting", percent=0.0)

    thread = threading.Thread(
        target=_run_download,
        args=(job_id, url, height, audio_only),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
def api_progress(job_id):
    job = _get_job(job_id)
    if not job:
        return jsonify({"error": "Unknown job."}), 404
    return jsonify(job)


@app.route("/downloads/<path:filename>")
def serve_download(filename):
    """Let the browser download the finished file to the user's Downloads."""
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    print("\n  YouTube Downloader running at:  http://127.0.0.1:5000\n")
    # threaded=True so progress polling works while a download runs.
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
