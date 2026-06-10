#!/bin/bash
# Daily YouTube upload runner — called by launchd

PROJECT_DIR="$HOME/Downloads/PhotoOrganizer"  # update this path if cloned elsewhere
PYTHON="$PROJECT_DIR/.venv/bin/python3"
SCRIPT="$PROJECT_DIR/organize_videos_for_youtube.py"
SOURCE="$HOME/Desktop/MyKidsMedia"
# Logs must NOT live under ~/Desktop — macOS TCC blocks launchd from opening
# files there, which fails the job spawn with EX_CONFIG (78). Use ~/Library/Logs.
LOG_DIR="$HOME/Library/Logs"

mkdir -p "$LOG_DIR"

echo "=== Upload started: $(date) ===" >> "$LOG_DIR/youtube-upload.log"

"$PYTHON" "$SCRIPT" "$SOURCE" --videos-only --upload --resume \
  >> "$LOG_DIR/youtube-upload.log" 2>&1

echo "=== Upload ended: $(date) ===" >> "$LOG_DIR/youtube-upload.log"
