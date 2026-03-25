# Diagnose PhotoOrganizer Health

Run a full pre-flight check on every component needed for uploads to work. Check each item in order, report pass/fail, and give the exact fix for anything broken.

## Step 1 — Check required files and directories

```bash
python3 -c "
import os, json

PROJECT = '/Users/ravigajul/Downloads/PhotoOrganizer'
HOME = os.path.expanduser('~')

checks = [
    ('client_secrets.json',       os.path.join(PROJECT, 'client_secrets.json'),                        'Download from GCP Console → APIs & Credentials → OAuth 2.0 → Download JSON → save as client_secrets.json'),
    ('OAuth token',               os.path.join(HOME, '.youtube_upload_token.json'),                    'Run interactively once: .venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload'),
    ('Python venv',               os.path.join(PROJECT, '.venv/bin/python3'),                          'Run: python3 -m venv .venv && .venv/bin/pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib'),
    ('Upload progress file',      os.path.join(HOME, 'Desktop/YouTube_Upload/Videos/upload_progress.json'), 'Not created yet — upload has not started. That is OK if this is a fresh start.'),
    ('Source media folder',       os.path.join(HOME, 'Desktop/MyKidsMedia'),                           'Create or restore ~/Desktop/MyKidsMedia with your source videos'),
    ('launchd plist',             os.path.join(HOME, 'Library/LaunchAgents/com.ravigajul.youtube-upload.plist'), 'Plist not installed — scheduler will not run automatically'),
    ('Email credentials',         os.path.join(HOME, '.youtube_upload_email.json'),                    'Create ~/.youtube_upload_email.json with {\"email\": \"...\", \"app_password\": \"...\"}'),
    ('Log directory',             os.path.join(HOME, 'Desktop/YouTube_Upload'),                        'Will be created on first run — OK if missing'),
]

print('FILE / CREDENTIAL CHECKS')
print('=' * 60)
all_ok = True
for label, path, fix in checks:
    exists = os.path.exists(path)
    status = '✅' if exists else '❌'
    print(f'{status}  {label}')
    if not exists:
        all_ok = False
        print(f'    FIX: {fix}')

print()
if all_ok:
    print('All files present.')
else:
    print('Fix the items marked ❌ before uploading.')
"
```

## Step 2 — Validate client_secrets.json format

```bash
python3 -c "
import json, os, sys
f = '/Users/ravigajul/Downloads/PhotoOrganizer/client_secrets.json'
if not os.path.exists(f):
    print('SKIP — file not found (see Step 1)')
    sys.exit(0)
try:
    d = json.load(open(f))
    top = list(d.keys())
    if 'installed' in d or 'web' in d:
        inner = d.get('installed') or d.get('web')
        client_id = inner.get('client_id', 'missing')
        print(f'✅  Valid OAuth2 format (type: {top[0]})')
        print(f'    client_id: {client_id[:30]}...')
    else:
        print(f'❌  Unexpected format — top-level keys: {top}')
        print('    FIX: Re-download from GCP Console as an OAuth 2.0 Desktop app credential')
except json.JSONDecodeError as e:
    print(f'❌  JSON parse error: {e}')
    print('    FIX: Re-download the file — it may be corrupted')
"
```

## Step 3 — Check OAuth token health

```bash
python3 -c "
import json, os, sys
from datetime import datetime, timezone, timedelta

HOME = os.path.expanduser('~')
token_file = os.path.join(HOME, '.youtube_upload_token.json')
meta_file = os.path.join(HOME, 'Desktop/YouTube_Upload/Videos/upload_meta.json')

# Check if quota window is still closed (script exits before auth in this case)
if not os.path.exists(token_file) and os.path.exists(meta_file):
    try:
        d = json.load(open(meta_file))
        last_end_str = d.get('last_session_ended_at')
        if last_end_str:
            last_end = datetime.fromisoformat(last_end_str)
            elapsed_h = (datetime.now() - last_end).total_seconds() / 3600
            if elapsed_h < 23.5:
                retry_time = last_end + timedelta(hours=24, minutes=5)
                print(f'ℹ️   Token not present — quota window not open yet (last session: {elapsed_h:.1f}h ago)')
                print(f'    Script exits before auth until window opens (~{retry_time.strftime(\"%-I:%M %p\")})')
                print(f'    This is EXPECTED — no action needed, scheduler will handle it')
                sys.exit(0)
    except Exception:
        pass

if not os.path.exists(token_file):
    print('❌  No token — browser auth required on first run')
    print('    FIX: Run the upload interactively once to generate the token')
    sys.exit(0)

try:
    d = json.load(open(token_file))
    expiry_str = d.get('token_expiry') or d.get('expiry')
    if expiry_str:
        expiry_str_clean = expiry_str.replace('Z', '+00:00')
        try:
            expiry = datetime.fromisoformat(expiry_str_clean)
            now = datetime.now(timezone.utc)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now:
                print(f'⚠️   Token expired at {expiry_str}')
                print('    FIX: rm ~/.youtube_upload_token.json  then re-run interactively once')
            else:
                delta = expiry - now
                print(f'✅  Token valid (expires in {int(delta.total_seconds()/60)} minutes)')
        except Exception:
            print(f'✅  Token file exists (expiry field: {expiry_str})')
    else:
        print('✅  Token file exists (no expiry field — likely a refresh token, OK)')
    scopes = d.get('scopes') or d.get('token_uri', '')
    print(f'    Scopes/URI hint: {str(scopes)[:80]}')
except Exception as e:
    print(f'❌  Could not parse token: {e}')
    print('    FIX: rm ~/.youtube_upload_token.json  then re-run interactively once')
"
```

## Step 4 — Check venv and key packages

```bash
/Users/ravigajul/Downloads/PhotoOrganizer/.venv/bin/python3 -c "
packages = ['googleapiclient', 'google.auth', 'google_auth_oauthlib']
for pkg in packages:
    try:
        __import__(pkg.replace('-', '_').split('.')[0])
        print(f'✅  {pkg}')
    except ImportError:
        print(f'❌  {pkg} — FIX: .venv/bin/pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib')

# Optional: Vision API
try:
    import google.cloud.vision
    print('✅  google-cloud-vision (nudity screening available)')
except ImportError:
    print('⚠️   google-cloud-vision not installed (--screen-nudity will not work)')
    print('    FIX: .venv/bin/pip install google-cloud-vision')
" 2>/dev/null || echo "❌  venv Python not found — run: python3 -m venv .venv"
```

## Step 5 — Check launchd scheduler

```bash
launchctl list com.ravigajul.youtube-upload 2>&1 | python3 -c "
import sys
output = sys.stdin.read().strip()
if 'Could not find service' in output or 'No such process' in output or output == '':
    print('❌  Scheduler NOT loaded')
    print('    FIX: launchctl load ~/Library/LaunchAgents/com.ravigajul.youtube-upload.plist')
else:
    import re
    exit_match = re.search(r'LastExitStatus\s*=\s*(\d+)', output)
    if exit_match:
        code = int(exit_match.group(1))
        if code == 0:
            print('✅  Scheduler loaded, last run succeeded (exit 0)')
        else:
            print(f'⚠️   Scheduler loaded, last run FAILED (exit {code})')
            print('    FIX: Check the log — tail -40 ~/Desktop/YouTube_Upload/launchd.log')
    else:
        print('✅  Scheduler loaded')
        print(f'    Raw: {output[:120]}')
"
```

## Step 6 — Quick source media count

```bash
python3 -c "
import os
media_dir = os.path.expanduser('~/Desktop/MyKidsMedia')
if not os.path.exists(media_dir):
    print('❌  ~/Desktop/MyKidsMedia not found')
else:
    exts = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}
    count = sum(1 for root, _, files in os.walk(media_dir) for f in files if os.path.splitext(f.lower())[1] in exts)
    size_bytes = sum(os.path.getsize(os.path.join(r, f)) for r, _, files in os.walk(media_dir) for f in files if os.path.splitext(f.lower())[1] in exts)
    size_gb = size_bytes / 1e9
    print(f'✅  Source media: {count} videos, {size_gb:.1f} GB')
    if count == 0:
        print('⚠️   No video files found — check file extensions or folder contents')
"
```

## Step 7 — Summary and recommended next action

Based on all the above:

- If everything is ✅ → say **"All systems go — run `/resume-upload` to start or continue uploading."**
- If token shows `ℹ️` (quota window not open) → say **"Everything is fine — waiting for the 24h quota window to open. Scheduler will resume automatically."**
- If `client_secrets.json` is missing → say **"Run `/setup-youtube-api` to complete first-time setup."**
- If the token is expired/missing (❌) → say **"Delete the stale token and re-run interactively once (see Step 3 fix)."**
- If the scheduler is not loaded → say **"Load the plist with the command in Step 5."**
- If venv packages are missing → say **"Install missing packages with the commands in Step 4."**

Give one clear sentence summarising overall health and the single most important action to take next.
