# Setup YouTube API Credentials

Automate the full Google Cloud setup for YouTube API uploads. Run each step using Bash tools.

## Step 1 — Install gcloud CLI (if not already installed)

Check if gcloud is installed:
```bash
which gcloud || echo "not found"
```

If not found, install via Homebrew:
```bash
brew install --cask google-cloud-sdk
```

Then initialise the shell:
```bash
source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
```

## Step 2 — Authenticate with Google

```bash
gcloud auth login --no-launch-browser
```

Follow the printed URL in the terminal — open it in your browser, sign in with your Google account, copy the auth code back into the terminal.

## Step 3 — Create a new Google Cloud project

```bash
gcloud projects create kids-videos-yt-$(date +%s) --name="KidsVideosUploader" 2>&1
```

Capture the project ID from the output (e.g. `kids-videos-yt-1234567890`) and set it as active:
```bash
PROJECT_ID=$(gcloud projects list --filter="name:KidsVideosUploader" --format="value(projectId)" | head -1)
gcloud config set project "$PROJECT_ID"
echo "Project set to: $PROJECT_ID"
```

## Step 4 — Enable billing (required for API access)

Check if billing is already available (free-tier accounts may need manual step):
```bash
gcloud beta billing accounts list 2>/dev/null | head -5 || echo "no billing accounts"
```

Link billing account to project (replace BILLING_ACCOUNT_ID with the ID from above):
```bash
# gcloud beta billing projects link "$PROJECT_ID" --billing-account=BILLING_ACCOUNT_ID
```

> Note: YouTube Data API v3 is free (no charges for the quota we use). Billing just needs to be enabled on the account.

## Step 5 — Enable the YouTube Data API v3

```bash
gcloud services enable youtube.googleapis.com --project="$PROJECT_ID"
```

## Step 6 — Configure OAuth consent screen

```bash
gcloud alpha iap oauth-brands create \
  --application_title="KidsVideosUploader" \
  --support_email="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -1)" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Consent screen may need manual setup"
```

If the above fails, the consent screen must be done manually:
- Go to: https://console.cloud.google.com/apis/credentials/consent
- Select **External** → fill in App name → Save

## Step 7 — Create OAuth 2.0 credentials

```bash
gcloud alpha iap oauth-clients create \
  "$(gcloud alpha iap oauth-brands list --project="$PROJECT_ID" --format='value(name)' | head -1)" \
  --display_name="KidsVideosDesktopClient" \
  --project="$PROJECT_ID" 2>/dev/null
```

If the gcloud approach isn't available, instruct the user to:
1. Open: https://console.cloud.google.com/apis/credentials
2. Click **+ Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Click **Create** → **Download JSON**
5. Save as `client_secrets.json` in `/Users/ravigajul/Downloads/PhotoOrganizer/`

## Step 8 — Verify client_secrets.json is in place

```bash
ls -la /Users/ravigajul/Downloads/PhotoOrganizer/client_secrets.json && \
  python3 -c "import json; d=json.load(open('client_secrets.json')); print('✅ Valid:', list(d.keys()))" || \
  echo "❌ File not found or invalid"
```

## Step 9 — Test the full setup with a dry run

```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer && \
  .venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload-dry-run
```

## Step 10 — Run the actual upload

Once the dry run looks correct:
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer && \
  .venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload
```

The browser will open once for Google sign-in. After that, the token is cached and all future uploads are fully automatic.

If the upload is interrupted, resume with:
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer && \
  .venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload --resume
```
