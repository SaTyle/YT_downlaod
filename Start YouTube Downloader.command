#!/usr/bin/env bash
# Double-click this file in Finder to launch the YouTube Downloader.
# (macOS runs .command files in Terminal when double-clicked.)

# 1) Go to the project directory first.
cd "/Users/ajeet_shinde/vs_code/YT_downlaod" || {
  echo "Could not find the project folder:"
  echo "  /Users/ajeet_shinde/vs_code/YT_downlaod"
  echo "If you moved it, update the path in this file."
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
}

# 2) Then run the app.
exec ./run.sh
