# PhotoOrganizer — Kids Video Organizer & YouTube Uploader

Organizes photos/videos exported from Mac Photos into year-based folders, then automatically uploads them to YouTube with proper metadata (title, unlisted visibility, year playlists). Pre-screens videos for nudity before uploading and auto-reschedules around YouTube's 24-hour quota window.

## Features

- Organizes videos and photos into `YYYY/` subfolders by creation date
- Renames files with a `YYYY-MM-DD_` date prefix for easy sorting
- Uploads videos to YouTube via the YouTube Data API v3:
  - Auto-creates yearly playlists (e.g. "Aarav's Videos 2024")
  - Sets title from filename + date (e.g. "Jun 1, 2024 - IMG 8344")
  - Marks all videos as **Unlisted**
  - Saves upload progress — resume safely after interruptions or quota limits
  - Pre-screens each video with **Google Cloud Vision SafeSearch** — permanently skips nudity-flagged videos before upload
  - Auto-reschedules around YouTube's 24h quota window to avoid wasting a day
- Dry-run mode to preview everything before touching a single file

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/PhotoOrganizer.git
cd PhotoOrganizer
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Google Cloud / YouTube API credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project → enable **YouTube Data API v3** and **Cloud Vision API**
3. Enable billing on the project (required for Vision API — free tier covers ~1000 images/month)
4. Create **OAuth 2.0 credentials** (Desktop app type)
5. Download the JSON file → save as `client_secrets.json` in this folder

> `client_secrets.json` is listed in `.gitignore` and will never be committed.

### 3. Add yourself as a test user (while app is unverified)

- Google Cloud Console → APIs & Services → OAuth consent screen → **Audience** tab
- Add your Google account email under **Test users**

## Usage

### Organize files only (no upload)

```bash
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyMedia --videos-only
```

### Preview what would be uploaded (safe, nothing changes)

```bash
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyMedia --videos-only --upload-dry-run
```

### Upload to YouTube

```bash
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyMedia --videos-only --upload
```

The browser opens once for Google sign-in. The token is cached at `~/.youtube_upload_token.json` — subsequent runs are fully automatic.

### Resume after interruption or quota limit

```bash
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyMedia --videos-only --upload --resume
```

Progress is saved to `upload_progress.json` in the output folder after each video. Already-uploaded videos are automatically skipped.

## CLI Reference

| Flag | Description |
| --- | --- |
| `--videos-only` | Process only video files (skip photos) |
| `--upload` | Upload organized videos to YouTube |
| `--upload-dry-run` | Preview upload plan without uploading |
| `--resume` | Skip already-uploaded videos (uses progress file) |
| `--notify-email` | Send a Gmail status email after upload (reads credentials from `~/.youtube_upload_email.json`) |
| `--screen-nudity` | Pre-screen each video with Google Cloud Vision SafeSearch before uploading — flags and permanently skips videos containing nudity. Requires Cloud Vision API enabled + billing on your GCP project. |
| `--client-secrets PATH` | Path to `client_secrets.json` (default: `./client_secrets.json`) |
| `--output PATH` | Where to write organised files (default: `~/Desktop/YouTube_Upload`) |
| `--export-report` | Save a JSON report of all organised files |

## Daily Scheduled Upload (macOS)

Since uploading 1,000+ videos takes multiple days due to YouTube's API quota, the project includes a launchd setup to automatically resume the upload every day at **10:45 AM**.

### How it works

**`~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist`** — a macOS LaunchAgent that tells the OS to run the upload script daily at **10:45 AM**.

The LaunchAgent is loaded into launchd (macOS's service manager) and persists across reboots. Each day at 10:45 AM, it runs the script with `--resume`, picking up from where the previous day left off using the saved `upload_progress.json`. A Gmail status email is sent after each run via `--notify-email`. Videos are pre-screened for nudity via `--screen-nudity` before uploading.

### Auto-rescheduling within the 24h quota window

YouTube's upload limit is a rolling 24-hour window. If yesterday's run ended at 2 PM and the script fires at 10:45 AM the next day (only ~21h later), it would hit the limit immediately and waste the day.

The script handles this automatically:

1. After every run it stamps the session end time to `upload_meta.json`
2. At startup it checks how much time has elapsed since the last session
3. If less than 24h have passed, it calculates `last_end + 24h 5min` as the retry time
4. If that retry time falls before the next regular 10:45 AM run, it creates a one-shot LaunchAgent (`com.ravigajul.youtube-upload-retry.plist`) that fires at exactly the right time
5. Once the retry fires and completes, the one-shot plist is automatically deleted

A status email is sent whenever a retry is scheduled so you know what's happening.

### One-time setup

```bash
# Load the LaunchAgent (registers it with macOS)
launchctl load ~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist
```

To receive daily email notifications, create `~/.youtube_upload_email.json`:

```json
{
  "email": "your@gmail.com",
  "app_password": "xxxx xxxx xxxx xxxx"
}
```

Generate a Gmail App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Set file permissions so only you can read it: `chmod 600 ~/.youtube_upload_email.json`.

### Manage the schedule

```bash
# Verify it is loaded
launchctl list | grep youtube-upload

# Trigger a manual run immediately (for testing)
launchctl start com.ravigajul.youtube-upload

# Stop and unload the schedule (disables daily runs)
launchctl unload ~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist

# Re-enable it
launchctl load ~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist
```

### Logs

Each run writes to `~/Desktop/YouTube_Upload/launchd.log`:

```bash
tail -f ~/Desktop/YouTube_Upload/launchd.log
```

> **Note:** The Mac must be awake at 10:45 AM for the job to trigger. If it is asleep, macOS will not catch up on missed runs — the next trigger will be the following day at 10:45 AM.

### Change the scheduled time

Edit the plist file at `~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist` and update the `Hour` value (24-hour format), then reload:

```bash
launchctl unload ~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist
launchctl load  ~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist
```

## YouTube Quota

The YouTube Data API has a daily quota (~10,000 units/day, ~6 uploads/day by default). Each upload costs ~1,650 units (`videos.insert` = 1,600 + `playlistItems.insert` = 50).

If you hit the limit, the script saves progress automatically and **auto-reschedules** a one-shot retry for exactly 24 hours after the previous session ended — so you never waste a day waiting for the window to reopen.

To request a higher quota: [console.cloud.google.com → YouTube Data API v3 → Quotas → Request higher quota](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas)

## Notes

- This script **never deletes or moves your original files** — it only reads them
- By default, organised files are **symlinks** (no extra disk space). Use `--copy` to duplicate or `--move` to relocate
- `client_secrets.json` and `upload_progress.json` are gitignored
- Flagged/skipped videos are recorded in `upload_skipped.json` — delete an entry to retry that video
