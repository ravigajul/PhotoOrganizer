# Resume YouTube Upload

Resume an interrupted upload, or kick off a manual run. This handles the full flow: token check, resume with the correct flags, and progress confirmation.

## Step 1 — Check for token issues first

```bash
python3 -c "
import os, json
token = os.path.expanduser('~/.youtube_upload_token.json')
if not os.path.exists(token):
    print('NO TOKEN — browser auth required on first run')
else:
    d = json.load(open(token))
    expiry = d.get('token_expiry') or d.get('expiry') or 'unknown'
    print(f'Token file exists (expiry: {expiry})')
"
```

If the last run failed with `invalid_grant` in the log, delete the stale token first:

```bash
# Only run this if the token is expired/revoked:
rm ~/.youtube_upload_token.json
```

Then run interactively once so the browser opens for re-auth:

```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia \
  --videos-only --upload --resume --screen-nudity --notify-email
```

The browser opens once. After sign-in the token is cached and all future runs are unattended.

## Step 2 — Normal resume (no token issues)

```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia \
  --videos-only --upload --resume --screen-nudity --notify-email
```

This is safe to run any time — already-uploaded videos are skipped automatically.

## Step 3 — Confirm upload is running

While uploading, progress lines appear like:

```
Uploading: Jun 1, 2024 - IMG 8344 ...  ✓ uploaded (video_id: abc123)
```

If you see `quotaExceeded`, YouTube's daily limit (10,000 units ≈ 6 uploads/min cap) has been hit. The script saves progress and exits cleanly — just re-run tomorrow, or let the launchd schedule handle it automatically.

## Step 4 — Verify the launchd schedule is active

```bash
launchctl list com.ravigajul.youtube-upload 2>&1 | grep -E "LastExitStatus|Label"
```

`LastExitStatus = 0` means the last scheduled run was clean. If the status is non-zero, check the log:

```bash
tail -40 ~/Desktop/YouTube_Upload/launchd.log
```
