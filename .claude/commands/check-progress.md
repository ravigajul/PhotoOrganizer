# Check Upload Progress

Show the current YouTube upload status for this project: how many videos have been uploaded, year breakdown, % complete, scheduler status, and any errors from recent runs.

## Step 1 — Upload counts

Run this to get the breakdown:

```bash
python3 -c "
import json, os, sys

TOTAL_VIDEOS = 1308
YEARS = {2024: 190, 2025: 993, 2026: 125}
progress_file = os.path.expanduser('~/Desktop/YouTube_Upload/Videos/upload_progress.json')

if not os.path.exists(progress_file):
    print('No progress file found — upload has not started yet.')
    sys.exit(0)

d = json.load(open(progress_file))
uploaded = len(d)
remaining = TOTAL_VIDEOS - uploaded
pct = uploaded / TOTAL_VIDEOS * 100

print(f'Uploaded : {uploaded} / {TOTAL_VIDEOS}  ({pct:.1f}%)')
print(f'Remaining: {remaining} videos')
print()

# Year breakdown: uploaded vs total
years_done = {}
for v in d.values():
    y = v['year']
    years_done[y] = years_done.get(y, 0) + 1

print('Year     Done   Total  Left')
print('----     ----   -----  ----')
for y, total in sorted(YEARS.items()):
    done = years_done.get(str(y), years_done.get(y, 0))
    left = total - done
    bar = '█' * int(done / total * 20) + '░' * (20 - int(done / total * 20))
    print(f'{y}     {done:4d}   {total:4d}   {left:4d}  {bar}')

print()
# Most recent uploads
recent = sorted(d.items(), key=lambda x: x[0])[-5:]
print('Last 5 uploaded:')
for fname, info in recent:
    print(f'  {info[\"title\"]}')
"
```

## Step 2 — Scheduler status

```bash
launchctl list com.ravigajul.youtube-upload 2>&1 | grep -E "LastExitStatus|OnDemand|Label"
```

Interpret the output:
- `LastExitStatus = 0` — last run succeeded
- `LastExitStatus != 0` — last run failed; check the log in Step 3

## Step 3 — Recent log (last 30 lines)

```bash
tail -30 ~/Desktop/YouTube_Upload/launchd.log 2>/dev/null || echo "No log file yet"
```

Look for these patterns and explain what they mean:

| Pattern in log | Meaning | Fix |
| --- | --- | --- |
| `quotaExceeded` | Hit YouTube's 10,000 unit daily quota | Wait ~24 hours, then it auto-resumes |
| `invalid_grant` / `Token has been expired` | OAuth token expired | Run: `rm ~/.youtube_upload_token.json` then re-run interactively once |
| `File not found, skipping` | Source file missing or symlink broken | Re-run without `--resume` to re-organise |
| `Uploaded:` lines | Normal progress | All good |

## Step 4 — Summary and next action

Based on the above, give the user a clear one-line status and the exact command to run next if action is needed.

**If token expired (`invalid_grant`):**
```bash
rm ~/.youtube_upload_token.json
# Then run interactively (browser will open once for re-auth):
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload --resume --screen-nudity --notify-email
```

**If quota exceeded:**
> No action needed — the launchd scheduler will auto-retry. You can also manually resume after ~24h:
```bash
cd /Users/ravigajul/Downloads/PhotoOrganizer
.venv/bin/python3 organize_videos_for_youtube.py ~/Desktop/MyKidsMedia --videos-only --upload --resume --screen-nudity --notify-email
```

**If all looks good:**
> Upload is running normally via the daily schedule. Nothing to do.
