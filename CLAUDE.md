# PhotoOrganizer — Project Context

## Self-learning rule
After every session where something new is learned — a bug fixed, a decision made, a preference stated, a gotcha discovered — update the relevant memory file in:
`~/.claude/projects/-Users-ravigajul-Downloads-PhotoOrganizer/memory/`

- New tool/API decision → `project_state.md`
- New file path or credential → `infrastructure.md`
- User correction or preference → `feedback.md`
- Keep `MEMORY.md` as a lean index only (no content, just pointers)

## What this project does
Organizes kids videos from Mac Photos export into year folders and uploads them to YouTube automatically.

## Key files
- `organize_videos_for_youtube.py` — main script (organise + upload)
- `client_secrets.json` — Google OAuth credentials (do not commit)
- `.venv/` — Python virtual environment with all dependencies
- `~/Desktop/YouTube_Upload/Videos/upload_progress.json` — tracks which videos have been uploaded (used for resume)

## Source videos
- Location: `~/Desktop/MyKidsMedia`
- Count: 1308 videos, 54.5 GB
- Years: 2024 (190), 2025 (993), 2026 (125)

## YouTube settings (hardcoded)
- Playlist names: `Aarav's Videos 2024`, `Aarav's Videos 2025`, `Aarav's Videos 2026`
- Visibility: Unlisted
- Made for kids: Yes
- Title format: `Jun 1, 2024 - IMG 8344`

## Python environment
Always use the venv Python, NOT system python3:
```
.venv/bin/python3
```

---

## Resume Commands

### Check upload progress
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
python3 -c "
import json, os
f = os.path.expanduser('~/Desktop/YouTube_Upload/Videos/upload_progress.json')
if os.path.exists(f):
    d = json.load(open(f))
    print(f'Uploaded so far: {len(d)} videos')
    years = {}
    for v in d.values():
        years[v[\"year\"]] = years.get(v[\"year\"], 0) + 1
    for y, c in sorted(years.items()):
        print(f'  {y}: {c} videos')
else:
    print('No progress file found — upload has not started yet')
"
```

### Resume an interrupted upload
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload --resume
```

### Resume with nudity pre-screening (recommended)
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload --resume --screen-nudity
```

#### One-time setup for --screen-nudity
1. Enable the Cloud Vision API in your GCP project:
   https://console.cloud.google.com/apis/library/vision.googleapis.com?project=KidsVideosUploader
2. Delete the cached OAuth token so it re-auths with the new scope:
   ```bash
   rm ~/.youtube_upload_token.json
   ```
3. Run once interactively (browser will open for re-auth):
   ```bash
   .venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload --resume --screen-nudity
   ```
4. After that, the launchd schedule runs fully unattended.

### Start a fresh upload (first time)
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload
```

### Preview what will be uploaded (safe, no changes)
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload-dry-run
```

### Organize only (no upload)
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only
```

---

## Google Cloud setup (already done)
- Project: KidsVideosUploader
- API: YouTube Data API v3 enabled
- Credentials: client_secrets.json in project root
- OAuth token cached at: `~/.youtube_upload_token.json`

## Daily upload quota
YouTube API allows ~6 uploads/minute. With 1308 videos, expect 2-3 days total.
If you hit quota, the script saves progress automatically — just re-run with `--resume` the next day.

## Email notifications

After each scheduled run, a status email is sent to the configured Gmail address.

### Credentials file (not committed)
`~/.youtube_upload_email.json`:
```json
{
  "email": "your@gmail.com",
  "app_password": "xxxx xxxx xxxx xxxx"
}
```

### Send a test email
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 - << 'EOF'
from organize_videos_for_youtube import send_status_email
send_status_email("Test", "This is a test notification.")
EOF
```

### Enable in manual runs
Add `--notify-email` to any `--upload` command:
```bash
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload --resume --notify-email
```

---

## Troubleshooting
- **"client_secrets.json not found"** — make sure the file is in `/Users/ravigajul/Downloads/PhotoOrganizer/`
- **"quota exceeded"** — wait 24 hours, then re-run with `--resume`
- **Browser doesn't open** — delete `~/.youtube_upload_token.json` and re-run
- **"File not found, skipping"** — symlinks may be broken; re-run without `--resume` to re-organise first
