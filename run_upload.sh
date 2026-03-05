#!/bin/bash
# Daily YouTube upload runner — called by launchd

PROJECT_DIR="/Users/ravigajul/Downloads/PhotoOrganizer"
PYTHON="$PROJECT_DIR/.venv/bin/python3"
SCRIPT="$PROJECT_DIR/organize_videos_for_youtube.py"
SOURCE="$HOME/Desktop/MyKidsMedia"
LOG_DIR="$HOME/Desktop/YouTube_Upload"

mkdir -p "$LOG_DIR"

echo "=== Upload started: $(date) ===" >> "$LOG_DIR/upload.log"

"$PYTHON" "$SCRIPT" "$SOURCE" --videos-only --upload --resume \
  >> "$LOG_DIR/upload.log" 2>&1

echo "=== Upload ended: $(date) ===" >> "$LOG_DIR/upload.log"
