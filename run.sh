#!/usr/bin/env bash
#
# One-command launcher for the YouTube Downloader.
# Starts the Streamlit app and opens it in your browser.
#
# Usage:  ./run.sh      (from Terminal)
# or just double-click "Start YouTube Downloader.command"
#
set -e

# Always run from this script's own folder, wherever it's launched from.
cd "$(dirname "$0")"

echo "────────────────────────────────────────────"
echo "  YouTube Downloader"
echo "────────────────────────────────────────────"

# Make sure ffmpeg is present (needed to merge 1080p/720p video + audio).
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "⚠️  ffmpeg not found."
  if command -v brew >/dev/null 2>&1; then
    echo "   Installing it with Homebrew..."
    brew install ffmpeg
  else
    echo "   Please install it:  brew install ffmpeg"
    exit 1
  fi
fi

# Make sure Python deps are installed (quietly skips if already present).
echo "Checking dependencies..."
python3 -m pip install -q -r requirements.txt

echo ""
echo "Starting the app — it will open in your browser."
echo "Keep this window open while you use it. Press Ctrl+C here to stop."
echo ""

# Launch Streamlit. It opens the browser itself by default.
exec python3 -m streamlit run streamlit_app.py
