"""
Unit tests for organize_videos_for_youtube.py

Run:  .venv/bin/python3 -m pytest test_organize.py -v
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import organize_videos_for_youtube as ov


# ---------------------------------------------------------------------------
# format_video_title
# ---------------------------------------------------------------------------

class TestFormatVideoTitle:
    def test_plain_name_with_date(self):
        d = datetime(2024, 6, 1)
        assert ov.format_video_title("IMG_8344.MOV", d) == "Jun 1, 2024 - IMG 8344"

    def test_strips_date_prefix_from_stem(self):
        d = datetime(2024, 6, 1)
        assert ov.format_video_title("2024-06-01_IMG_8344.MOV", d) == "Jun 1, 2024 - IMG 8344"

    def test_strips_yyyymmdd_prefix(self):
        d = datetime(2024, 6, 1)
        assert ov.format_video_title("20240601_party.MOV", d) == "Jun 1, 2024 - party"

    def test_returns_only_date_when_stem_empty_after_strip(self):
        d = datetime(2024, 6, 1)
        # After stripping the date prefix there is nothing left
        assert ov.format_video_title("2024-06-01.MOV", d) == "Jun 1, 2024"

    def test_single_digit_day(self):
        d = datetime(2025, 3, 5)
        assert ov.format_video_title("IMG_0434.MOV", d) == "Mar 5, 2025 - IMG 0434"


# ---------------------------------------------------------------------------
# get_file_date
# ---------------------------------------------------------------------------

class TestGetFileDate:
    def test_yyyymmdd_in_name(self, tmp_path):
        f = tmp_path / "20240601_video.MOV"
        f.touch()
        assert ov.get_file_date(str(f)) == datetime(2024, 6, 1)

    def test_yyyy_mm_dd_in_name(self, tmp_path):
        f = tmp_path / "2025-03-05_clip.mp4"
        f.touch()
        assert ov.get_file_date(str(f)) == datetime(2025, 3, 5)

    def test_falls_back_to_mtime(self, tmp_path):
        f = tmp_path / "no_date_here.MOV"
        f.touch()
        result = ov.get_file_date(str(f))
        assert isinstance(result, datetime)


# ---------------------------------------------------------------------------
# organize_by_year — duplicate filename dedup (regression: counter compounding)
# ---------------------------------------------------------------------------

class TestOrganizeByYearDedup:
    """Regression test: before the fix, the counter would compound (_1_2_3...)
    when multiple files mapped to the same destination name."""

    def _make_files(self, tmp_path, names):
        """Create real source files and return file-info dicts."""
        files = []
        for name in names:
            p = tmp_path / name
            p.write_bytes(b"fake video")
            files.append({
                'path': p,
                'date': datetime(2024, 6, 1),
                'size': 10,
                'year': '2024',
            })
        return files

    def test_two_same_name_files_get_counter_suffix(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        out = tmp_path / "out"
        out.mkdir()

        # Two files that will both map to the same dest name after date-prefixing
        # Use the same date embedded in the filename so they resolve to the same dest
        f1 = src / "20240601_clip.MOV"
        f2 = src / "20240601_clip_copy.MOV"
        f1.write_bytes(b"v1")
        f2.write_bytes(b"v2")

        ov.organize_by_year([f1, f2], str(out), mode='copy')

        year_dir = out / "2024"
        names = [p.name for p in year_dir.iterdir()]
        # Neither file should have a compounded suffix like _1_2
        assert not any("_1_2" in n or "_1_1" in n for n in names), \
            f"Compounded suffix detected: {names}"

    def test_three_colliding_files_get_distinct_names(self, tmp_path):
        """Regression: the old code re-read dest.stem each loop iteration,
        causing _1_2_3... compounding.  Fixed by capturing original_stem once."""
        src = tmp_path / "src"
        src.mkdir()
        out = tmp_path / "out"
        out.mkdir()

        # Three files with the exact same date-embedded name so all produce the
        # same destination after date-prefix logic
        files = []
        for fname in ["20240601_same.MOV", "20240601_same_a.MOV", "20240601_same_b.MOV"]:
            p = src / fname
            p.write_bytes(b"x")
            files.append(p)

        ov.organize_by_year(files, str(out), mode='copy')

        year_dir = out / "2024"
        names = sorted(p.name for p in year_dir.iterdir())
        # All names must be unique
        assert len(names) == len(set(names)), f"Duplicate names found: {names}"
        # No name should contain a doubled counter pattern like _1_2
        for n in names:
            stem = Path(n).stem
            assert "_1_2" not in stem and "_2_3" not in stem, \
                f"Counter compounding detected in: {n}"


# ---------------------------------------------------------------------------
# verify_and_clean_progress — SKIPPED_ entries must not be removed
# ---------------------------------------------------------------------------

class TestVerifyAndCleanProgress:
    def _make_progress(self, tmp_path, entries):
        pf = str(tmp_path / "upload_progress.json")
        with open(pf, 'w') as f:
            json.dump(entries, f)
        return pf

    def test_skipped_entries_are_never_removed(self, tmp_path):
        entries = {
            "IMG_8074.MOV": {"title": "Nov 13, 2024 - IMG 8074", "year": "2024",
                             "video_id": "SKIPPED_CONTENT_FILTERED"},
            "IMG_8099.MOV": {"title": "Nov 15, 2024 - IMG 8099", "year": "2024",
                             "video_id": "SKIPPED_CONTENT_FILTERED"},
        }
        pf = self._make_progress(tmp_path, entries)

        # YouTube returns nothing — as if all IDs are missing
        youtube = MagicMock()
        youtube.videos().list().execute.return_value = {'items': []}

        ov.verify_and_clean_progress(youtube, entries, pf)

        # Entries must still be present
        assert "IMG_8074.MOV" in entries
        assert "IMG_8099.MOV" in entries

    def test_missing_real_video_is_removed(self, tmp_path):
        entries = {
            "REAL_VIDEO.MOV": {"title": "Jan 1, 2024 - REAL VIDEO", "year": "2024",
                               "video_id": "abc123"},
        }
        pf = self._make_progress(tmp_path, entries)

        # YouTube returns nothing — video was silently deleted
        youtube = MagicMock()
        youtube.videos().list().execute.return_value = {'items': []}

        ov.verify_and_clean_progress(youtube, entries, pf)

        assert "REAL_VIDEO.MOV" not in entries

    def test_existing_real_video_is_kept(self, tmp_path):
        entries = {
            "GOOD_VIDEO.MOV": {"title": "Jan 2, 2024 - GOOD VIDEO", "year": "2024",
                               "video_id": "xyz999"},
        }
        pf = self._make_progress(tmp_path, entries)

        youtube = MagicMock()
        youtube.videos().list().execute.return_value = {
            'items': [{'id': 'xyz999'}]
        }

        ov.verify_and_clean_progress(youtube, entries, pf)

        assert "GOOD_VIDEO.MOV" in entries

    def test_mixed_skipped_and_real(self, tmp_path):
        entries = {
            "SKIP.MOV":  {"title": "skipped", "year": "2024",
                          "video_id": "SKIPPED_CONTENT_FILTERED"},
            "GONE.MOV":  {"title": "gone",    "year": "2024", "video_id": "gone111"},
            "ALIVE.MOV": {"title": "alive",   "year": "2024", "video_id": "alive22"},
        }
        pf = self._make_progress(tmp_path, entries)

        youtube = MagicMock()
        youtube.videos().list().execute.return_value = {
            'items': [{'id': 'alive22'}]   # only ALIVE.MOV exists
        }

        ov.verify_and_clean_progress(youtube, entries, pf)

        assert "SKIP.MOV"  in entries   # preserved — intentionally skipped
        assert "GONE.MOV"  not in entries  # removed — disappeared from YouTube
        assert "ALIVE.MOV" in entries   # preserved — still live


# ---------------------------------------------------------------------------
# acquire_upload_lock / release_upload_lock
# ---------------------------------------------------------------------------

class TestUploadLock:
    def _progress_path(self, tmp_path):
        return str(tmp_path / "upload_progress.json")

    def test_acquire_fresh_lock(self, tmp_path):
        pf = self._progress_path(tmp_path)
        assert ov.acquire_upload_lock(pf) is True
        lock = tmp_path / "upload.lock"
        assert lock.exists()
        assert int(lock.read_text()) == os.getpid()

    def test_acquire_stale_lock(self, tmp_path):
        """A lock file with a dead PID should be taken over."""
        pf = self._progress_path(tmp_path)
        lock = tmp_path / "upload.lock"
        lock.write_text("99999999")  # almost certainly a dead PID
        assert ov.acquire_upload_lock(pf) is True

    def test_acquire_live_lock_returns_false(self, tmp_path):
        """A lock file with the current process's PID means we're already running."""
        pf = self._progress_path(tmp_path)
        lock = tmp_path / "upload.lock"
        lock.write_text(str(os.getpid()))
        assert ov.acquire_upload_lock(pf) is False

    def test_release_removes_lock(self, tmp_path):
        pf = self._progress_path(tmp_path)
        ov.acquire_upload_lock(pf)
        ov.release_upload_lock(pf)
        assert not (tmp_path / "upload.lock").exists()

    def test_release_no_file_is_silent(self, tmp_path):
        pf = self._progress_path(tmp_path)
        # Should not raise even if lock was never created
        ov.release_upload_lock(pf)


# ---------------------------------------------------------------------------
# check_upload_window
# ---------------------------------------------------------------------------

class TestCheckUploadWindow:
    def _progress_path(self, tmp_path):
        return str(tmp_path / "upload_progress.json")

    def test_first_run_no_history(self, tmp_path):
        pf = self._progress_path(tmp_path)
        assert ov.check_upload_window(pf) is True

    def test_enough_time_elapsed(self, tmp_path):
        pf = self._progress_path(tmp_path)
        meta = pf.replace('upload_progress.json', 'upload_meta.json')
        last_end = datetime.now() - timedelta(hours=25)
        with open(meta, 'w') as f:
            json.dump({'last_session_ended_at': last_end.isoformat()}, f)
        assert ov.check_upload_window(pf) is True

    def test_too_soon_returns_false(self, tmp_path):
        pf = self._progress_path(tmp_path)
        meta = pf.replace('upload_progress.json', 'upload_meta.json')
        last_end = datetime.now() - timedelta(hours=2)
        with open(meta, 'w') as f:
            json.dump({'last_session_ended_at': last_end.isoformat()}, f)

        with patch.object(ov, 'schedule_retry_launchd'):
            result = ov.check_upload_window(pf)
        assert result is False
