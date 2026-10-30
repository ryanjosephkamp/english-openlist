"""
Tests for the working copies the nightly edits.

Since huggingface_hub 1.32.0 the cache stores LFS and Xet payloads read-only.
The download step copied them with `shutil.copy2`, which carries the mode
across, so the copies in initial_deliverables/ were read-only and every night
from 2026-09-19 failed with PermissionError on its first write. These tests hold
the fix in place: the copies are always writable, whatever mode the source has,
and the download step refuses to finish when they are not.
"""

import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.download_from_huggingface as download  # noqa: E402
from scripts.download_from_huggingface import (  # noqa: E402
    WORKING_COPY_MODE,
    writable_copy,
    unwritable,
)

pytestmark = pytest.mark.skipif(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX modes and a user that file modes apply to",
)


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def read_only_blob(tmp_path: Path, text: str = "steamship\n") -> Path:
    """A file shaped like a shared blob in the hub's cache: mode 0o444."""
    blob = tmp_path / "cache" / "blob"
    blob.parent.mkdir(parents=True)
    blob.write_text(text, encoding="utf-8")
    os.chmod(blob, 0o444)
    return blob


def test_a_copy_of_a_read_only_blob_is_writable(tmp_path):
    blob = read_only_blob(tmp_path)
    dest = writable_copy(blob, tmp_path / "work" / "merged_valid_dict.json")

    assert dest.read_text(encoding="utf-8") == "steamship\n"
    assert mode(dest) == WORKING_COPY_MODE
    with open(dest, "a", encoding="utf-8") as f:
        f.write("horrid\n")


def test_copy2_is_what_made_the_copies_read_only(tmp_path):
    # The failure the fix replaces, kept as a fact about the standard library:
    # copy2 copies the mode, so a read-only source gives a read-only copy.
    import shutil

    blob = read_only_blob(tmp_path)
    dest = tmp_path / "copy2"
    shutil.copy2(blob, dest)
    assert not os.access(dest, os.W_OK)


def test_the_source_blob_is_left_as_it_was(tmp_path):
    blob = read_only_blob(tmp_path)
    writable_copy(blob, tmp_path / "work" / "copy")
    assert mode(blob) == 0o444


def test_a_read_only_copy_from_an_earlier_run_is_replaced(tmp_path):
    blob = read_only_blob(tmp_path, "initial\n")
    dest = tmp_path / "work" / "merged_invalid_words.txt"
    dest.parent.mkdir(parents=True)
    dest.write_text("stale\n", encoding="utf-8")
    os.chmod(dest, 0o444)

    writable_copy(blob, dest)
    assert dest.read_text(encoding="utf-8") == "initial\n"
    assert os.access(dest, os.W_OK)


def test_a_symlinked_snapshot_entry_copies_its_target(tmp_path):
    # Snapshot folders hold symlinks into the blob store.
    blob = read_only_blob(tmp_path, "rallying\n")
    link = tmp_path / "snapshot" / "data" / "merged_valid_words.txt"
    link.parent.mkdir(parents=True)
    link.symlink_to(blob)

    dest = writable_copy(link, tmp_path / "work" / "merged_valid_words.txt")
    assert not dest.is_symlink()
    assert dest.read_text(encoding="utf-8") == "rallying\n"
    assert os.access(dest, os.W_OK)


def test_unwritable_names_only_existing_read_only_files(tmp_path):
    writable = tmp_path / "writable"
    writable.write_text("x", encoding="utf-8")
    locked = tmp_path / "locked"
    locked.write_text("x", encoding="utf-8")
    os.chmod(locked, 0o444)

    assert unwritable([writable, locked, tmp_path / "missing"]) == [locked]


def test_snapshot_download_leaves_writable_copies(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot"
    (snapshot / "data").mkdir(parents=True)
    for name in ("merged_valid_words.txt", "merged_valid_dict.json", "merged_invalid_words.txt"):
        path = snapshot / "data" / name
        path.write_text("obtuse\n", encoding="utf-8")
        os.chmod(path, 0o444)

    target = tmp_path / "initial_deliverables"
    monkeypatch.setattr(download, "INITIAL_DELIVERABLES", target)
    monkeypatch.setattr(download, "_snapshot_download_with_retry", lambda **_: str(snapshot))

    assert download.HuggingFaceDownloader(token="").download_with_snapshot(skip_large_dicts=True)
    copies = sorted(target.iterdir())
    assert [p.name for p in copies] == [
        "merged_invalid_words.txt", "merged_valid_dict.json", "merged_valid_words.txt",
    ]
    assert unwritable(copies) == []


def test_the_download_step_fails_when_a_copy_is_not_writable(tmp_path, monkeypatch, capsys):
    target = tmp_path / "initial_deliverables"
    target.mkdir()
    locked = target / "merged_valid_dict.json"
    locked.write_text("{}", encoding="utf-8")
    os.chmod(locked, 0o444)

    monkeypatch.setattr(download, "INITIAL_DELIVERABLES", target)
    monkeypatch.setattr(download, "VALID_WORDS_FILE", target / "merged_valid_words.txt")
    monkeypatch.setattr(download, "VALID_DICT_FILE", locked)
    monkeypatch.setattr(download, "INVALID_WORDS_FILE", target / "merged_invalid_words.txt")
    monkeypatch.setattr(download, "INVALID_DICT_FILE", target / "merged_invalid_dict.json")
    monkeypatch.setattr(
        download.HuggingFaceDownloader, "download_with_snapshot", lambda self, **_: True
    )
    monkeypatch.setattr(sys, "argv", ["download_from_huggingface.py", "--skip-large-dicts"])

    assert download.main() == 1
    assert "Not writable" in capsys.readouterr().out
