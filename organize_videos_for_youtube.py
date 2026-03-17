#!/usr/bin/env python3
"""
=============================================================================
  📹 Kids Videos Organizer for YouTube Upload
=============================================================================
  Exports videos from your Mac Photos library (or any folder) and organizes
  them into year-based folders, ready for bulk upload to YouTube.
  
  Usage:
    # Option 1: Scan exported photos folder
    python3 organize_videos_for_youtube.py /path/to/exported/photos

    # Option 2: Scan a specific folder of videos
    python3 organize_videos_for_youtube.py /path/to/videos

    # Option 3: Scan with custom output directory
    python3 organize_videos_for_youtube.py /path/to/source --output ~/Desktop/YouTube_Upload

    # Option 4: Copy files instead of creating symlinks (takes more space but safer)
    python3 organize_videos_for_youtube.py /path/to/source --copy

    # Option 5: Actually move files (frees space from original location)
    python3 organize_videos_for_youtube.py /path/to/source --move

  After running, you'll have folders like:
    YouTube_Upload/
    ├── 2023/
    │   ├── 2023-01-15_baby_first_steps.MOV
    │   ├── 2023-03-22_park_day.mp4
    │   └── ...
    ├── 2024/
    │   ├── 2024-06-01_birthday.MOV
    │   └── ...
    └── 2025/
        └── ...

  Then drag each year's folder into YouTube Studio to upload!
=============================================================================
"""

import os
import sys
import argparse
import shutil
import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Video extensions to look for
VIDEO_EXTENSIONS = {
    '.mov', '.mp4', '.m4v', '.avi', '.mkv', '.wmv', '.flv', '.webm',
    '.3gp', '.mts', '.m2ts', '.ts', '.vob', '.mpg', '.mpeg'
}

# Photo extensions (for summary/reporting)
PHOTO_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.heic', '.heif', '.tiff', '.tif',
    '.raw', '.cr2', '.nef', '.arw', '.dng', '.bmp', '.gif', '.webp'
}


def get_file_date(filepath):
    """
    Extract the best available date from a file.
    Priority: filename date pattern > file modification date > file creation date
    """
    filename = os.path.basename(filepath)
    
    # Try to extract date from common filename patterns
    # iPhone pattern: IMG_20230115_123456.MOV or 20230115_123456.MOV
    import re
    
    # Pattern: YYYYMMDD in filename
    match = re.search(r'(20[12]\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])', filename)
    if match:
        try:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return datetime(year, month, day)
        except ValueError:
            pass
    
    # Pattern: YYYY-MM-DD in filename
    match = re.search(r'(20[12]\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])', filename)
    if match:
        try:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return datetime(year, month, day)
        except ValueError:
            pass
    
    # Fall back to file metadata
    stat = os.stat(filepath)
    
    # On macOS, st_birthtime gives the actual creation time
    if hasattr(stat, 'st_birthtime'):
        return datetime.fromtimestamp(stat.st_birthtime)
    
    # Otherwise use modification time
    return datetime.fromtimestamp(stat.st_mtime)


def format_size(size_bytes):
    """Format bytes into human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def scan_directory(source_dir, recursive=True):
    """Scan directory for video and photo files."""
    videos = []
    photos = []
    other = []
    
    source_path = Path(source_dir)
    
    if recursive:
        all_files = source_path.rglob('*')
    else:
        all_files = source_path.glob('*')
    
    for filepath in all_files:
        if filepath.is_file() and not filepath.name.startswith('.'):
            ext = filepath.suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                videos.append(filepath)
            elif ext in PHOTO_EXTENSIONS:
                photos.append(filepath)
            else:
                other.append(filepath)
    
    return videos, photos, other


def organize_by_year(files, output_dir, mode='symlink', file_type='videos'):
    """Organize files into year-based folders."""
    output_path = Path(output_dir)
    year_stats = defaultdict(lambda: {'count': 0, 'size': 0, 'files': []})
    errors = []
    
    for filepath in files:
        try:
            file_date = get_file_date(filepath)
            year = str(file_date.year)
            file_size = filepath.stat().st_size
            
            # Create year directory
            year_dir = output_path / year
            year_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a clean filename with date prefix for sorting
            date_prefix = file_date.strftime('%Y-%m-%d')
            original_name = filepath.name
            
            # Add date prefix if not already present
            if not original_name.startswith(('20', '19')):
                new_name = f"{date_prefix}_{original_name}"
            else:
                new_name = original_name
            
            dest = year_dir / new_name
            
            # Handle duplicates
            counter = 1
            while dest.exists():
                stem = dest.stem
                suffix = dest.suffix
                dest = year_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Copy, move, or symlink
            if mode == 'copy':
                shutil.copy2(filepath, dest)
            elif mode == 'move':
                shutil.move(str(filepath), str(dest))
            else:  # symlink
                os.symlink(filepath.resolve(), dest)
            
            year_stats[year]['count'] += 1
            year_stats[year]['size'] += file_size
            year_stats[year]['files'].append({
                'name': new_name,
                'size': file_size,
                'date': file_date.isoformat()
            })
            
        except Exception as e:
            errors.append(f"  ⚠️  Error processing {filepath.name}: {e}")
    
    return dict(year_stats), errors


def print_summary(video_stats, photo_stats, output_dir, errors):
    """Print a nice summary of what was organized."""
    print("\n" + "=" * 70)
    print("  📹 ORGANIZATION COMPLETE!")
    print("=" * 70)
    
    print(f"\n  📂 Output folder: {output_dir}")
    
    if video_stats:
        print(f"\n  🎬 VIDEOS (ready for YouTube upload):")
        print(f"  {'─' * 50}")
        total_videos = 0
        total_size = 0
        for year in sorted(video_stats.keys()):
            stats = video_stats[year]
            count = stats['count']
            size = format_size(stats['size'])
            total_videos += stats['count']
            total_size += stats['size']
            print(f"    📁 {year}/  →  {count} videos  ({size})")
        print(f"  {'─' * 50}")
        print(f"    Total: {total_videos} videos  ({format_size(total_size)})")
    
    if photo_stats:
        print(f"\n  📷 PHOTOS (organized by year):")
        print(f"  {'─' * 50}")
        total_photos = 0
        total_size = 0
        for year in sorted(photo_stats.keys()):
            stats = photo_stats[year]
            count = stats['count']
            size = format_size(stats['size'])
            total_photos += stats['count']
            total_size += stats['size']
            print(f"    📁 {year}/  →  {count} photos  ({size})")
        print(f"  {'─' * 50}")
        print(f"    Total: {total_photos} photos  ({format_size(total_size)})")
    
    if errors:
        print(f"\n  ⚠️  {len(errors)} files had issues:")
        for error in errors[:10]:
            print(error)
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    
    print()


def print_youtube_instructions(output_dir):
    """Print step-by-step YouTube upload instructions."""
    print("=" * 70)
    print("  📤 HOW TO UPLOAD TO YOUTUBE (Year by Year)")
    print("=" * 70)
    print(f"""
  STEP 1: Open YouTube Studio
    → Go to https://studio.youtube.com
    → Sign in to your Google account

  STEP 2: Create a playlist for each year
    → Click "Playlists" in the left sidebar
    → Click "New Playlist" for each year (e.g., "Baby 2023", "Baby 2024")
    → Set playlist visibility to "Unlisted"

  STEP 3: Upload one year at a time
    → Click the "CREATE" button (top right) → "Upload videos"
    → Open Finder and navigate to: {output_dir}
    → Open a year folder (e.g., 2024/)
    → Select ALL videos (Cmd+A) and drag into YouTube upload window
    → While they upload, set for ALL videos:
        ✅ Visibility: "Unlisted"  
        ✅ Audience: "Yes, it's made for kids" (important for child content)
        ✅ Add to the corresponding year playlist

  STEP 4: Share with family
    → Go to your playlist → Click "Share" → Copy link
    → Send the playlist link to family members
    → They can watch without a YouTube account!

  STEP 5: Free up iPhone space
    → Once uploads are verified, delete videos from your iPhone
    → Settings → General → iPhone Storage → Photos → Review Videos

  💡 TIPS:
    • YouTube allows up to 15-minute videos by default
    • Verify your account to upload up to 12 hours / 256 GB per video
      (YouTube Studio → Settings → Channel → Feature eligibility)
    • Upload overnight on WiFi for large batches
    • YouTube processing takes time — 4K videos may take hours
    • You can upload ~50-100 videos per batch easily
""")


def format_video_title(filename, file_date):
    """Convert filename + date into a clean YouTube title.

    Example: '2024-06-01_birthday_party.MOV' -> 'Jun 1, 2024 - birthday party'
    """
    import re
    stem = Path(filename).stem
    # Strip leading YYYY-MM-DD_ or YYYYMMDD_ prefix
    stem = re.sub(r'^20\d{2}[-_]\d{2}[-_]\d{2}[-_]?', '', stem)
    stem = re.sub(r'^20\d{6}[-_]?', '', stem)
    # Replace underscores/hyphens with spaces and strip
    stem = stem.replace('_', ' ').replace('-', ' ').strip()
    # Format date as "Jun 1, 2024"
    date_str = file_date.strftime('%b %-d, %Y')
    if stem:
        return f"{date_str} - {stem}"
    return date_str


def get_youtube_service(client_secrets_path):
    """Authenticate with YouTube Data API v3 via OAuth2.

    Token is cached in ~/.youtube_upload_token.json so the browser
    only opens once.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("\n  ❌ Missing dependencies. Install them with:")
        print("     pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib\n")
        sys.exit(1)

    SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
              'https://www.googleapis.com/auth/youtube',
              'https://www.googleapis.com/auth/cloud-platform']
    token_path = os.path.expanduser('~/.youtube_upload_token.json')
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_path):
                print(f"\n  ❌ client_secrets.json not found at: {client_secrets_path}")
                print("  Please follow the setup instructions and try again.\n")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds), creds


def get_or_create_playlist(youtube, year):
    """Find or create an unlisted playlist named 'Kids Videos {year}'.

    Returns the playlist ID.
    """
    playlist_title = f"Aarav's Videos {year}"

    # Search existing playlists
    response = youtube.playlists().list(part='snippet', mine=True, maxResults=50).execute()
    for item in response.get('items', []):
        if item['snippet']['title'] == playlist_title:
            return item['id']

    # Create new playlist
    result = youtube.playlists().insert(
        part='snippet,status',
        body={
            'snippet': {'title': playlist_title},
            'status': {'privacyStatus': 'unlisted'}
        }
    ).execute()
    return result['id']


def upload_video(youtube, filepath, title, playlist_id):
    """Upload a single video to YouTube and add it to a playlist.

    Returns the video ID.
    """
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(filepath), resumable=True)
    request = youtube.videos().insert(
        part='snippet,status',
        body={
            'snippet': {'title': title},
            'status': {
                'privacyStatus': 'unlisted'
            }
        },
        media_body=media
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response['id']

    # Add to playlist
    youtube.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {'kind': 'youtube#video', 'videoId': video_id}
            }
        }
    ).execute()

    return video_id


def verify_and_clean_progress(youtube, uploaded, progress_file):
    """Check all tracked video IDs actually exist on YouTube.

    When YouTube hits an upload limit it sometimes silently removes recently
    uploaded videos. This scans the progress file, drops any ghost entries,
    and re-saves so the next run will re-upload the missing ones.
    """
    if not uploaded:
        return

    all_keys = list(uploaded.keys())
    all_video_ids = [uploaded[k]['video_id'] for k in all_keys]

    found_ids = set()
    for i in range(0, len(all_video_ids), 50):
        batch = all_video_ids[i:i + 50]
        try:
            resp = youtube.videos().list(part='status', id=','.join(batch)).execute()
            for item in resp.get('items', []):
                found_ids.add(item['id'])
        except Exception:
            return  # If the check itself fails, leave progress untouched

    missing_keys = [k for k in all_keys if uploaded[k]['video_id'] not in found_ids]
    if missing_keys:
        print(f"\n  ⚠️  {len(missing_keys)} video(s) were accepted by YouTube but are no longer there.")
        print(f"     Removing them from progress so they will be re-uploaded:\n")
        for k in missing_keys:
            print(f"       - {uploaded[k]['title']}")
            del uploaded[k]
        with open(progress_file, 'w') as f:
            json.dump(uploaded, f, indent=2)
        print(f"\n     Progress file updated — these will be re-uploaded on the next run.")


def _exit_on_api_error(e, progress_file, uploaded):
    """Check for HTTP errors and exit immediately if a fatal API error occurs."""
    try:
        from googleapiclient.errors import HttpError as _HttpError
        if isinstance(e, _HttpError):
            status = e.resp.status
            try:
                details = json.loads(e.content.decode())
                reason = details.get('error', {}).get('errors', [{}])[0].get('reason', '')
                message = details.get('error', {}).get('message', str(e))
            except Exception:
                reason = ''
                message = str(e)

            if status == 400 and 'uploadLimitExceeded' in reason:
                print(f"\n  ❌ YouTube daily upload limit reached.")
                print(f"     You've hit YouTube's daily upload cap for this channel.")
                print(f"     Quota resets at midnight Pacific Time — re-run tomorrow with --resume.")
                print(f"     Progress saved ({len(uploaded)} videos uploaded).")
                print(f"  📄 Progress file: {progress_file}")
                sys.exit(1)
            elif status == 403:
                if 'quotaExceeded' in reason or 'dailyLimitExceeded' in reason:
                    print(f"\n  ❌ YouTube API quota exceeded.")
                    print(f"     Reason: {reason}")
                    print(f"     Progress saved ({len(uploaded)} videos uploaded).")
                    print(f"     Re-run tomorrow with --resume to continue.\n")
                else:
                    print(f"\n  ❌ YouTube API returned 403 Forbidden.")
                    print(f"     {message}")
                    print(f"     Progress saved ({len(uploaded)} videos uploaded).")
                    print(f"     Fix the issue then re-run with --resume.\n")
                print(f"  📄 Progress file: {progress_file}")
                sys.exit(1)
    except ImportError:
        pass


def screen_video_for_nudity(filepath, creds, max_frames=8):
    """Sample frames from a video and check for nudity using Google Cloud Vision SafeSearch.

    Extracts up to *max_frames* frames evenly spaced, runs SafeSearch on each via
    the Vision API (same GCP project / OAuth credentials as YouTube), and returns
    (flagged, detail_str).  Flags if any frame scores LIKELY or VERY_LIKELY for
    'adult' or 'racy' content — matching roughly what YouTube's own pipeline checks.
    """
    import subprocess
    import tempfile
    from google.cloud import vision as gv
    from google.oauth2.credentials import Credentials as _Creds

    # Build a Vision client using the same OAuth token
    vision_client = gv.ImageAnnotatorClient(credentials=creds)

    # Likelihood levels we consider a flag (LIKELY=4, VERY_LIKELY=5)
    FLAG_THRESHOLD = gv.Likelihood.LIKELY

    # Get video duration via ffprobe
    probe = subprocess.run(
        ['/opt/homebrew/bin/ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(filepath)],
        capture_output=True, text=True
    )
    try:
        duration = float(json.loads(probe.stdout)['format']['duration'])
    except Exception:
        duration = 60.0

    interval = max(1.0, duration / max_frames)

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            '/opt/homebrew/bin/ffmpeg', '-i', str(filepath),
            '-vf', f'fps=1/{interval:.2f}',
            '-frames:v', str(max_frames),
            f'{tmpdir}/frame_%04d.jpg',
            '-hide_banner', '-loglevel', 'error'
        ]
        try:
            subprocess.run(cmd, check=True, timeout=120)
        except Exception as e:
            print(f"  ⚠️  Frame extraction failed for {filepath.name}: {e}")
            return False, ''

        frames = sorted(Path(tmpdir).glob('*.jpg'))
        if not frames:
            return False, ''

        for frame in frames:
            try:
                with open(frame, 'rb') as fh:
                    image = gv.Image(content=fh.read())
                result = vision_client.safe_search_detection(image=image)
                safe = result.safe_search_annotation
                if safe.adult >= FLAG_THRESHOLD:
                    return True, f'adult content detected (frame {frame.name})'
                if safe.racy >= FLAG_THRESHOLD:
                    return True, f'racy content detected (frame {frame.name})'
            except Exception as e:
                err_str = str(e)
                if 'BILLING_DISABLED' in err_str or 'billing' in err_str.lower():
                    return None, 'billing_disabled'
                # Other transient errors — skip this frame, continue
                continue

    return False, ''


RETRY_PLIST_LABEL = 'com.ravigajul.youtube-upload-retry'
RETRY_PLIST_PATH = os.path.expanduser(
    f'~/Library/LaunchAgents/{RETRY_PLIST_LABEL}.plist'
)
MAIN_PLIST_SCHEDULE = (10, 45)  # hour, minute of the regular daily run


def _meta_file(progress_file):
    return progress_file.replace('upload_progress.json', 'upload_meta.json')


def record_session_end(progress_file):
    """Stamp the current time as the end of this upload session."""
    meta = _meta_file(progress_file)
    data = {}
    if os.path.exists(meta):
        with open(meta) as f:
            data = json.load(f)
    data['last_session_ended_at'] = datetime.now().isoformat()
    with open(meta, 'w') as f:
        json.dump(data, f, indent=2)


def get_last_session_end(progress_file):
    """Return datetime of last session end, or None."""
    meta = _meta_file(progress_file)
    if not os.path.exists(meta):
        return None
    try:
        with open(meta) as f:
            val = json.load(f).get('last_session_ended_at')
        return datetime.fromisoformat(val) if val else None
    except Exception:
        return None


def cleanup_retry_plist():
    """Unload and delete the one-shot retry plist if it exists."""
    import subprocess
    if os.path.exists(RETRY_PLIST_PATH):
        subprocess.run(['launchctl', 'unload', RETRY_PLIST_PATH],
                       capture_output=True)
        os.remove(RETRY_PLIST_PATH)


def schedule_retry_launchd(run_at):
    """Create and load a one-shot launchd plist to retry at *run_at*."""
    import subprocess
    script = os.path.abspath(__file__)
    venv_python = os.path.join(os.path.dirname(script), '.venv', 'bin', 'python3')
    source = os.path.expanduser('~/Desktop/MyKidsMedia')

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{RETRY_PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{venv_python}</string>
        <string>{script}</string>
        <string>{source}</string>
        <string>--videos-only</string>
        <string>--upload</string>
        <string>--resume</string>
        <string>--notify-email</string>
        <string>--screen-nudity</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Month</key>  <integer>{run_at.month}</integer>
        <key>Day</key>    <integer>{run_at.day}</integer>
        <key>Hour</key>   <integer>{run_at.hour}</integer>
        <key>Minute</key> <integer>{run_at.minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{os.path.expanduser('~/Desktop/YouTube_Upload/launchd.log')}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.expanduser('~/Desktop/YouTube_Upload/launchd.log')}</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>"""

    cleanup_retry_plist()  # Remove any previous one-shot first
    with open(RETRY_PLIST_PATH, 'w') as f:
        f.write(plist)
    subprocess.run(['launchctl', 'load', RETRY_PLIST_PATH], capture_output=True)


def check_upload_window(progress_file, notify_email=False):
    """Check whether 24 h have elapsed since the last session.

    If not enough time has passed:
      - Computes retry_time = last_end + 24 h + 5 min
      - If retry_time falls before the next regular 10:45 AM run, schedules
        a one-shot launchd retry and returns False (caller should exit).
      - If the regular schedule will fire first, just returns False (no plist needed).

    Returns True if it is safe to proceed with uploading.
    """
    last_end = get_last_session_end(progress_file)
    if last_end is None:
        return True  # First ever run — no history

    from datetime import timedelta
    elapsed_h = (datetime.now() - last_end).total_seconds() / 3600
    if elapsed_h >= 23.5:  # 30-min grace buffer
        return True

    retry_time = last_end + timedelta(hours=24, minutes=5)
    now = datetime.now()

    # Next regular 10:45 AM run
    next_regular = now.replace(hour=MAIN_PLIST_SCHEDULE[0],
                               minute=MAIN_PLIST_SCHEDULE[1],
                               second=0, microsecond=0)
    if next_regular <= now:
        from datetime import timedelta as _td
        next_regular += _td(days=1)

    wait_h = (retry_time - now).total_seconds() / 3600
    print(f"\n  ⏰ Only {elapsed_h:.1f}h since last upload session (need 24h).")

    schedule_retry_launchd(retry_time)
    msg = (f"     Quota window not open yet — retry scheduled for "
           f"{retry_time.strftime('%b %-d at %-I:%M %p')} "
           f"({wait_h:.1f}h from now).\n")
    print(msg)
    if notify_email:
        send_status_email(
            "⏰ YouTube Upload — retry rescheduled",
            f"Upload skipped: only {elapsed_h:.1f}h since last session.\n"
            f"Retry scheduled for {retry_time.strftime('%b %-d, %Y at %-I:%M %p')}."
        )

    return False


def load_skip_list(progress_file):
    """Load the list of filenames permanently skipped due to policy violations."""
    skip_file = progress_file.replace('upload_progress.json', 'upload_skipped.json')
    if os.path.exists(skip_file):
        with open(skip_file) as f:
            return json.load(f), skip_file
    return {}, skip_file


def save_to_skip_list(filename, title, reason, skip_file, skipped):
    """Permanently skip a video — it will never be retried."""
    skipped[filename] = {'title': title, 'reason': reason, 'skipped_at': datetime.now().isoformat()}
    with open(skip_file, 'w') as f:
        json.dump(skipped, f, indent=2)
    print(f"  🚫 Permanently skipped: {title}")
    print(f"     Reason: {reason}")
    print(f"     (Added to upload_skipped.json — will not be retried)")


def upload_all_videos(youtube, video_stats, output_dir, progress_file, resume=False, screen_nudity=False, creds=None):
    """Upload all organized videos to YouTube, with resume support."""
    from googleapiclient.errors import HttpError

    uploaded = {}
    if resume and os.path.exists(progress_file):
        with open(progress_file) as f:
            uploaded = json.load(f)
        print(f"  ↩️  Resuming — {len(uploaded)} videos already uploaded\n")

    skipped, skip_file = load_skip_list(progress_file)
    if skipped:
        print(f"  🚫 {len(skipped)} video(s) permanently skipped (policy violations — see upload_skipped.json)\n")

    total = sum(s['count'] for s in video_stats.values())
    done = len(uploaded)

    print(f"  📤 Uploading {total} videos to YouTube...\n")

    for year in sorted(video_stats.keys()):
        files_in_year = sorted(video_stats[year]['files'], key=lambda f: f['date'])
        print(f"  📁 {year} — creating/finding playlist...")
        try:
            playlist_id = get_or_create_playlist(youtube, year)
        except HttpError as e:
            _exit_on_api_error(e, progress_file, uploaded)
            print(f"\n  ❌ Failed to create/find playlist for {year}: {e}\n")
            sys.exit(1)
        print(f"     Playlist: Aarav's Videos {year}  (id: {playlist_id})\n")

        year_dir = Path(output_dir) / year

        for file_info in files_in_year:
            filename = file_info['name']
            if filename in uploaded:
                done += 1
                continue
            if filename in skipped:
                done += 1
                continue

            filepath = year_dir / filename
            if not filepath.exists():
                print(f"  ⚠️  File not found, skipping: {filename}")
                continue

            file_date = datetime.fromisoformat(file_info['date'])
            title = format_video_title(filename, file_date)
            size = format_size(file_info['size'])
            done += 1

            print(f"  [{done:>{len(str(total))}}/{total}]  {title}  ({size})")

            if screen_nudity:
                print(f"        🔍 Screening for nudity...", end='', flush=True)
                flagged, detail = screen_video_for_nudity(filepath, creds)
                if flagged is None:
                    if detail == 'billing_disabled':
                        print(f"\n\n  ⚠️  Google Cloud Vision API requires billing to be enabled.")
                        print(f"     Enable billing at: https://console.cloud.google.com/billing/enable?project=1030325330707")
                        print(f"     Nudity screening disabled for this session — uploads will continue unscreened.\n")
                    screen_nudity = False  # disable for rest of session
                elif flagged:
                    print(f"  FLAGGED — {detail}")
                    save_to_skip_list(filename, title, f'nudity_prescreened: {detail}', skip_file, skipped)
                    continue
                else:
                    print(f"  OK")

            try:
                video_id = upload_video(youtube, filepath, title, playlist_id)
                uploaded[filename] = {'video_id': video_id, 'title': title, 'year': year}
                with open(progress_file, 'w') as f:
                    json.dump(uploaded, f, indent=2)
                time.sleep(1)  # Gentle rate limiting
            except HttpError as e:
                # Check for policy violation — skip permanently rather than retrying
                try:
                    details = json.loads(e.content.decode())
                    reason = details.get('error', {}).get('errors', [{}])[0].get('reason', '')
                    message = details.get('error', {}).get('message', '')
                except Exception:
                    reason, message = '', str(e)

                if 'policyViolation' in reason or 'childSafety' in reason or (e.resp.status == 400 and 'policy' in message.lower()):
                    save_to_skip_list(filename, title, message or reason, skip_file, skipped)
                    continue

                verify_and_clean_progress(youtube, uploaded, progress_file)
                _exit_on_api_error(e, progress_file, uploaded)
                print(f"         ⚠️  Upload failed (HTTP {e.resp.status}): {e}")
                sys.exit(1)
            except Exception as e:
                print(f"         ⚠️  Upload failed: {e}")

    print(f"\n  ✅ Upload complete! {len(uploaded)}/{total} videos uploaded.")
    print(f"  📄 Progress saved to: {progress_file}")
    print(f"  🎬 View your channel: https://studio.youtube.com\n")


def print_upload_preview(video_stats, output_dir):
    """Print a dry-run preview of what would be uploaded."""
    print("\n  📋 UPLOAD PREVIEW  (dry run — nothing will be uploaded)")
    print("  " + "═" * 58)

    total_videos = 0
    total_bytes = 0

    for year in sorted(video_stats.keys()):
        files_in_year = sorted(video_stats[year]['files'], key=lambda f: f['date'])
        count = len(files_in_year)
        print(f"\n  Playlist: Aarav's Videos {year}  (will be created if needed)")

        for i, file_info in enumerate(files_in_year, 1):
            file_date = datetime.fromisoformat(file_info['date'])
            title = format_video_title(file_info['name'], file_date)
            size = format_size(file_info['size'])
            print(f"    [{i:>{len(str(count))}}/{count}]  {title:<45}  ({size})")
            total_bytes += file_info['size']

        total_videos += count

    print(f"\n  {'─' * 58}")
    print(f"  Total: {total_videos} videos  ({format_size(total_bytes)})  across {len(video_stats)} playlists")
    print(f"  Visibility: Unlisted")
    print(f"\n  To upload, run the same command with --upload instead of --upload-dry-run\n")


def load_email_config():
    """Load Gmail credentials from ~/.youtube_upload_email.json."""
    config_path = os.path.expanduser('~/.youtube_upload_email.json')
    if not os.path.exists(config_path):
        return None
    with open(config_path) as f:
        return json.load(f)


def send_status_email(subject, body):
    """Send a status email to yourself via Gmail SMTP + App Password.

    Reads 'email' and 'app_password' from ~/.youtube_upload_email.json.
    """
    import smtplib
    from email.mime.text import MIMEText

    config = load_email_config()
    if not config:
        print("  ⚠️  Email notification skipped — ~/.youtube_upload_email.json not found")
        return

    gmail = config.get('email')
    app_password = config.get('app_password')
    if not gmail or not app_password:
        print("  ⚠️  Email notification skipped — missing 'email' or 'app_password' in config")
        return

    msg = MIMEText(body, 'plain')
    msg['From'] = gmail
    msg['To'] = gmail
    msg['Subject'] = subject

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail, app_password)
            server.send_message(msg)
        print(f"  📧 Status email sent to {gmail}")
    except Exception as e:
        print(f"  ⚠️  Failed to send email notification: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Organize videos (and photos) by year for YouTube upload',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Organize videos from exported Photos library
  python3 organize_videos_for_youtube.py ~/Pictures/PhotosExport
  
  # Organize with copy mode (duplicates files)
  python3 organize_videos_for_youtube.py ~/Pictures/PhotosExport --copy
  
  # Organize and move files (frees original space)
  python3 organize_videos_for_youtube.py ~/Pictures/PhotosExport --move
  
  # Custom output location
  python3 organize_videos_for_youtube.py ~/Photos --output ~/Desktop/ForYouTube
  
  # Videos only (skip photos)
  python3 organize_videos_for_youtube.py ~/Photos --videos-only
        """
    )
    
    parser.add_argument('source', help='Source directory containing photos/videos')
    parser.add_argument('--output', '-o', default=None,
                        help='Output directory (default: ~/Desktop/YouTube_Upload)')
    parser.add_argument('--copy', action='store_true',
                        help='Copy files (uses more disk space but safer)')
    parser.add_argument('--move', action='store_true',
                        help='Move files (frees space from original location)')
    parser.add_argument('--videos-only', action='store_true',
                        help='Only organize video files, skip photos')
    parser.add_argument('--photos-only', action='store_true',
                        help='Only organize photo files, skip videos')
    parser.add_argument('--no-recursive', action='store_true',
                        help='Do not scan subdirectories')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without actually doing it')
    parser.add_argument('--export-report', action='store_true',
                        help='Save a JSON report of all organized files')
    parser.add_argument('--upload-dry-run', action='store_true',
                        help='Preview what would be uploaded to YouTube (titles, playlists, sizes) — safe, no files touched')
    parser.add_argument('--upload', action='store_true',
                        help='Upload organized videos to YouTube via API (read-only — never deletes your files)')
    parser.add_argument('--client-secrets', default='client_secrets.json',
                        help='Path to Google OAuth client_secrets.json (default: ./client_secrets.json)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume a previously interrupted upload session')
    parser.add_argument('--notify-email', action='store_true',
                        help='Send a Gmail status notification after upload completes (reads credentials from ~/.youtube_upload_email.json)')
    parser.add_argument('--screen-nudity', action='store_true',
                        help='Pre-screen each video for nudity before uploading (uses NudeNet + ffmpeg). '
                             'Flagged videos are added to upload_skipped.json and never uploaded.')
    
    args = parser.parse_args()
    
    # Validate source directory
    source = os.path.expanduser(args.source)
    if not os.path.isdir(source):
        print(f"\n  ❌ Source directory not found: {source}")
        print(f"  Please check the path and try again.\n")
        
        # Helpful hints for Mac users
        print("  💡 Common locations for photos on Mac:")
        print("     ~/Pictures/Photos Library.photoslibrary  (requires export first)")
        print("     ~/Pictures/")
        print("     ~/Desktop/")
        print("     ~/Downloads/")
        print()
        print("  📱 To export from Photos app:")
        print("     1. Open Photos app on your Mac")
        print("     2. Select photos/videos (Cmd+A for all)")
        print("     3. File → Export → Export Unmodified Originals")
        print("     4. Choose a destination folder")
        print("     5. Run this script on that folder")
        print()
        sys.exit(1)
    
    # Set output directory
    if args.output:
        output_dir = os.path.expanduser(args.output)
    else:
        output_dir = os.path.expanduser('~/Desktop/YouTube_Upload')
    
    # Determine mode
    if args.move:
        mode = 'move'
        mode_label = "MOVING"
    elif args.copy:
        mode = 'copy'
        mode_label = "COPYING"
    else:
        mode = 'symlink'
        mode_label = "LINKING (symlinks — no extra space used)"
    
    # Scan source directory
    print(f"\n  🔍 Scanning: {source}")
    print(f"     Mode: {mode_label}")
    
    videos, photos, _ = scan_directory(source, recursive=not args.no_recursive)
    
    print(f"\n  Found:")
    print(f"    🎬 {len(videos)} videos ({format_size(sum(f.stat().st_size for f in videos))})")
    print(f"    📷 {len(photos)} photos ({format_size(sum(f.stat().st_size for f in photos))})")
    
    if len(videos) == 0 and len(photos) == 0:
        print("\n  ❌ No media files found in the source directory!")
        print("     Make sure you've exported from the Photos app first.\n")
        sys.exit(1)
    
    # Dry run check
    if args.dry_run:
        print(f"\n  🏃 DRY RUN — showing what would happen:\n")
        
        if videos and not args.photos_only:
            print("  Videos by year:")
            year_counts = defaultdict(int)
            for v in videos:
                year = str(get_file_date(v).year)
                year_counts[year] += 1
            for year in sorted(year_counts):
                print(f"    {year}: {year_counts[year]} videos")
        
        if photos and not args.videos_only:
            print("  Photos by year:")
            year_counts = defaultdict(int)
            for p in photos:
                year = str(get_file_date(p).year)
                year_counts[year] += 1
            for year in sorted(year_counts):
                print(f"    {year}: {year_counts[year]} photos")
        
        print(f"\n  Output would be in: {output_dir}")
        print("  (Run without --dry-run to actually organize files)\n")
        sys.exit(0)
    
    # Confirm before proceeding
    if mode == 'move':
        print(f"\n  ⚠️  WARNING: Move mode will REMOVE files from the original location!")
        response = input("  Continue? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("  Cancelled.\n")
            sys.exit(0)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    all_errors = []
    video_stats = {}
    photo_stats = {}
    
    # Organize videos
    if videos and not args.photos_only:
        print(f"\n  🎬 Organizing {len(videos)} videos by year...")
        video_output = os.path.join(output_dir, 'Videos')
        video_stats, v_errors = organize_by_year(videos, video_output, mode, 'videos')
        all_errors.extend(v_errors)
    
    # Organize photos
    if photos and not args.videos_only:
        print(f"  📷 Organizing {len(photos)} photos by year...")
        photo_output = os.path.join(output_dir, 'Photos')
        photo_stats, p_errors = organize_by_year(photos, photo_output, mode, 'photos')
        all_errors.extend(p_errors)
    
    # Print summary
    print_summary(video_stats, photo_stats, output_dir, all_errors)

    # Upload dry-run preview
    if args.upload_dry_run and video_stats:
        print_upload_preview(video_stats, video_output)

    # Actual YouTube upload
    if args.upload and video_stats:
        client_secrets = os.path.expanduser(args.client_secrets)
        progress_file = os.path.join(video_output, 'upload_progress.json')

        # Snapshot count before this session for the email summary
        count_before = 0
        if os.path.exists(progress_file):
            with open(progress_file) as f:
                count_before = len(json.load(f))

        total_videos = sum(s['count'] for s in video_stats.values())

        # Guard: don't start if we're still inside the 24h quota window
        if not check_upload_window(progress_file, notify_email=args.notify_email):
            sys.exit(0)

        youtube, creds = get_youtube_service(client_secrets)
        exit_status = 'success'
        exit_note = ''
        try:
            upload_all_videos(youtube, video_stats, video_output, progress_file, resume=args.resume, screen_nudity=args.screen_nudity, creds=creds)
        except SystemExit:
            exit_status = 'stopped'
            exit_note = 'Upload stopped early — quota exceeded or fatal error. Check the log for details.'
            raise
        finally:
            # Always stamp session end time and remove any stale retry plist
            record_session_end(progress_file)
            cleanup_retry_plist()
            if args.notify_email:
                # Read final progress
                if os.path.exists(progress_file):
                    with open(progress_file) as f:
                        uploaded = json.load(f)
                else:
                    uploaded = {}
                count_after = len(uploaded)
                uploaded_today = count_after - count_before
                year_counts = {}
                for v in uploaded.values():
                    year_counts[v['year']] = year_counts.get(v['year'], 0) + 1
                pct = int(100 * count_after / total_videos) if total_videos else 0
                run_time = datetime.now().strftime('%b %-d, %Y at %-I:%M %p')
                status_label = 'Completed' if exit_status == 'success' else 'Stopped early'
                status_icon = '✅' if exit_status == 'success' else '⚠️'
                remaining = total_videos - count_after

                subject = (
                    f"{status_icon} YouTube Upload — {uploaded_today} video(s) uploaded "
                    f"({count_after}/{total_videos} total)"
                )
                lines = [
                    f"YouTube Upload Status — {run_time}",
                    "",
                    f"Status:          {status_label}",
                    f"Uploaded today:  {uploaded_today} video(s)",
                    f"Total so far:    {count_after} / {total_videos} ({pct}%)",
                    "",
                    "Breakdown by year:",
                ]
                for yr in sorted(year_counts):
                    lines.append(f"  {yr}: {year_counts[yr]} videos")
                if exit_note:
                    lines += ["", f"Note: {exit_note}"]
                if remaining > 0:
                    from datetime import timedelta
                    next_run = datetime.now() + timedelta(hours=24, minutes=5)
                    lines += ["", f"Remaining: {remaining} video(s) — next attempt ~{next_run.strftime('%b %-d at %-I:%M %p')} (auto-rescheduled if within quota window)"]
                else:
                    lines += ["", "All videos uploaded!"]
                send_status_email(subject, "\n".join(lines))
    
    # Export report if requested
    if args.export_report:
        report = {
            'source': source,
            'output': output_dir,
            'mode': mode,
            'timestamp': datetime.now().isoformat(),
            'videos': {year: {'count': s['count'], 'size_bytes': s['size']} 
                       for year, s in video_stats.items()},
            'photos': {year: {'count': s['count'], 'size_bytes': s['size']} 
                       for year, s in photo_stats.items()},
            'errors': all_errors
        }
        report_path = os.path.join(output_dir, 'organization_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"  📄 Report saved to: {report_path}\n")
    
    # Print YouTube upload instructions
    if video_stats:
        print_youtube_instructions(os.path.join(output_dir, 'Videos'))
    
    # Final helpful note about Photos app export
    print("=" * 70)
    print("  📱 REMINDER: HOW TO EXPORT FROM MAC PHOTOS APP")
    print("=" * 70)
    print(f"""
  If you haven't exported yet, here's how:

  1. Open the Photos app on your Mac
  2. In the sidebar, you can filter by "Videos" under Media Types
  3. Select the videos you want (Cmd+A for all)
  4. Go to File → Export → Export Unmodified Originals...
  5. Choose a folder (e.g., ~/Desktop/MyPhotosExport)
  6. Wait for export to complete
  7. Then run:
     python3 {os.path.basename(__file__)} ~/Desktop/MyPhotosExport

  For ALL media (photos + videos):
  1. Select all media in Photos app (Cmd+A)
  2. File → Export → Export Unmodified Originals
  3. Run this script on the exported folder
""")


if __name__ == '__main__':
    main()