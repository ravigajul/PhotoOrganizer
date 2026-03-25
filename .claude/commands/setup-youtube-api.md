# Setup YouTube API Credentials

Automate the full Google Cloud setup for YouTube API uploads. Run each step using Bash tools. Skip any step that's already done.

## Step 1 — Install gcloud CLI (if not already installed)

```bash
which gcloud && gcloud version | head -1 || echo "not found"
```

If not found, install via Homebrew:

```bash
brew install --cask google-cloud-sdk
source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
```

## Step 2 — Authenticate with Google

```bash
gcloud auth login --no-launch-browser
```

Follow the printed URL — open it in your browser, sign in, copy the auth code back into the terminal.

## Step 3 — Create a Google Cloud project

```bash
gcloud projects create kids-videos-yt-$(date +%s) --name="KidsVideosUploader" 2>&1
```

Capture the project ID and set it active:

```bash
PROJECT_ID=$(gcloud projects list --filter="name:KidsVideosUploader" --format="value(projectId)" | head -1)
gcloud config set project "$PROJECT_ID"
echo "Project set to: $PROJECT_ID"
```

## Step 4 — Enable billing (required to enable APIs)

```bash
gcloud beta billing accounts list 2>/dev/null | head -5 || echo "no billing accounts found"
```

If a billing account is listed, link it:

```bash
# Replace BILLING_ACCOUNT_ID with the ID from above:
# gcloud beta billing projects link "$PROJECT_ID" --billing-account=BILLING_ACCOUNT_ID
```

> YouTube Data API v3 is free — billing just needs to be enabled on the account, no charges incurred.

## Step 5 — Enable the YouTube Data API v3

```bash
gcloud services enable youtube.googleapis.com --project="$PROJECT_ID"
```

If you also want Cloud Vision (for nudity screening with `--screen-nudity`):

```bash
gcloud services enable vision.googleapis.com --project="$PROJECT_ID"
```

## Step 6 — Configure OAuth consent screen (manual step)

The `gcloud` CLI can't fully automate the consent screen. Do this in the browser:

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Select **External** → fill in App name (e.g. `KidsVideosUploader`) → add your email as test user → Save

## Step 7 — Create OAuth 2.0 credentials (manual step)

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click **+ Create Credentials → OAuth client ID**
3. Application type: **Desktop app**, name it anything
4. Click **Create** → **Download JSON**
5. Save the downloaded file as `client_secrets.json` in the project directory:

```bash
# Move it into place (adjust the download filename as needed):
mv ~/Downloads/client_secret_*.json "$(pwd)/client_secrets.json"
```

## Step 8 — Verify client_secrets.json

```bash
python3 -c "
import json, os
f = 'client_secrets.json'
if not os.path.exists(f):
    print('❌ Not found — check Step 7')
else:
    d = json.load(open(f))
    keys = list(d.keys())
    print(f'✅ Valid — top-level keys: {keys}')
"
```

## Step 9 — Install Python dependencies

```bash
python3 -m venv .venv
.venv/bin/pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

If using `--screen-nudity`, also install the Vision API client:

```bash
.venv/bin/pip install google-cloud-vision
```

## Step 10 — Dry run to verify everything works

```bash
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload-dry-run
```

This lists what would be uploaded without touching YouTube. If it completes without errors, you're ready.

## Step 11 — First upload run (browser opens once for auth)

```bash
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia \
  --videos-only --upload --screen-nudity --notify-email
```

The browser opens once for Google sign-in. The token is cached at `~/.youtube_upload_token.json` — all future runs are fully unattended.

## Step 12 — Set up the daily schedule (launchd)

The project includes a `run_upload.sh` and a launchd plist to run automatically each day. Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist
launchctl list com.ravigajul.youtube-upload
```

Logs go to `~/Desktop/YouTube_Upload/launchd.log`. To check status at any time, use `/check-progress`.

---

## Troubleshooting

| Error | Fix |
| --- | --- |
| `client_secrets.json not found` | File must be in the project root (Step 7–8) |
| `invalid_grant` / token expired | `rm ~/.youtube_upload_token.json` then re-run interactively |
| `quotaExceeded` | Wait 24 hours — the schedule will auto-retry |
| Browser doesn't open | Delete `~/.youtube_upload_token.json` and re-run |
| Vision API 403 | Enable `vision.googleapis.com` in GCP (Step 5) and delete the token to re-auth with new scope |
