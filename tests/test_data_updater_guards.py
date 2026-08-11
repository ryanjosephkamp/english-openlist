"""
Guards against the invalid list being written over with nothing.

merged_invalid_words.txt was 91 MB on 2026-01-19 and 0 bytes on 2026-01-25, and
stayed that way for 199 days. The mechanism was a loop: the daily run downloaded
the file, got nothing, loaded an empty set, wrote that empty set back
unconditionally, uploaded it, and downloaded the same empty file the next
morning. merged_invalid_dict.json sat next to it through all of that and
survived, because its write was guarded by `if self.invalid_dict:` and the word
list's was not.

These tests hold that guard in place on both files and at both call sites.
"""

import sys
from pathlib import Path

import orjson
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.data_updater import MAX_SHRINK_RATIO, DataManager


def make_manager(tmp_path, invalid_words=(), invalid_dict=None):
    """A DataManager whose four paths are all inside tmp_path."""
    valid_words = tmp_path / "merged_valid_words.txt"
    valid_dict = tmp_path / "merged_valid_dict.json"
    invalid_words_path = tmp_path / "merged_invalid_words.txt"
    invalid_dict_path = tmp_path / "merged_invalid_dict.json"

    valid_words.write_text("alpha\nbeta\n", encoding="utf-8")
    valid_dict.write_bytes(orjson.dumps({"alpha": {}, "beta": {}}))
    invalid_words_path.write_text(
        "".join(f"{w}\n" for w in invalid_words), encoding="utf-8"
    )
    invalid_dict_path.write_bytes(orjson.dumps(invalid_dict or {}))

    manager = DataManager(
        valid_words_path=valid_words,
        valid_dict_path=valid_dict,
        invalid_words_path=invalid_words_path,
        invalid_dict_path=invalid_dict_path,
    )
    manager.load_data()
    return manager


# --- the decision itself -----------------------------------------------------

@pytest.mark.parametrize(
    "count, loaded, allowed",
    [
        (0, 0, False),          # nothing loaded, nothing to write: the 2026-01-25 case
        (0, 9_200_000, False),  # loaded a full list and would write an empty one
        (9_199_000, 9_200_000, True),   # an ordinary day: ~1,000 promoted out
        (4_599_999, 9_200_000, False),  # more than half the list vanished mid-run
        (4_600_000, 9_200_000, True),   # exactly half is the boundary, and allowed
        (5, 0, True),           # first population: nothing loaded, so nothing to lose
    ],
)
def test_may_write_invalid(tmp_path, count, loaded, allowed):
    manager = make_manager(tmp_path)
    assert manager._may_write_invalid(count, loaded, "test") is allowed


def test_shrink_threshold_matches_the_documented_ratio(tmp_path):
    manager = make_manager(tmp_path)
    loaded = 1000
    boundary = int(loaded * MAX_SHRINK_RATIO)
    assert manager._may_write_invalid(boundary, loaded, "test") is True
    assert manager._may_write_invalid(boundary - 1, loaded, "test") is False


# --- save_data(output_dir) ---------------------------------------------------

def test_empty_invalid_words_writes_no_release_file(tmp_path):
    """The regression: an empty set must not produce a 0-byte release file."""
    manager = make_manager(tmp_path)
    assert manager.invalid_words == set()

    out = tmp_path / "out"
    out.mkdir()
    manager.save_data(output_dir=out)

    assert not (out / "merged_invalid_words.txt").exists()
    assert not (out / "merged_invalid_dict.json").exists()
    # The valid list is unaffected by any of this.
    assert (out / "merged_valid_words.txt").read_text(encoding="utf-8").split() == [
        "alpha",
        "beta",
    ]


def test_populated_invalid_words_are_written(tmp_path):
    manager = make_manager(
        tmp_path,
        invalid_words=("qqqq", "xyzzy", "zzzz", "wwww"),
        invalid_dict={"qqqq": {"reason": "not a word"}},
    )

    out = tmp_path / "out"
    out.mkdir()
    manager.save_data(output_dir=out)

    written = (out / "merged_invalid_words.txt").read_text(encoding="utf-8").split()
    assert written == ["qqqq", "wwww", "xyzzy", "zzzz"]  # sorted
    assert orjson.loads((out / "merged_invalid_dict.json").read_bytes()) == {
        "qqqq": {"reason": "not a word"}
    }


def test_ordinary_promotion_still_writes(tmp_path):
    """~1,000 words promoted out of 9.2M is the normal case, not a wipe."""
    words = tuple(f"w{i:05d}" for i in range(2000))
    manager = make_manager(tmp_path, invalid_words=words)
    for word in words[:50]:
        manager.invalid_words.discard(word)

    out = tmp_path / "out"
    out.mkdir()
    manager.save_data(output_dir=out)

    assert len(
        (out / "merged_invalid_words.txt").read_text(encoding="utf-8").split()
    ) == 1950


def test_mass_disappearance_is_refused(tmp_path):
    """A partial load that still parses must not overwrite the good copy."""
    words = tuple(f"w{i:05d}" for i in range(2000))
    manager = make_manager(tmp_path, invalid_words=words)
    manager.invalid_words = set(words[:100])

    out = tmp_path / "out"
    out.mkdir()
    manager.save_data(output_dir=out)

    assert not (out / "merged_invalid_words.txt").exists()


# --- save_source_files() -----------------------------------------------------

def test_empty_invalid_words_leaves_source_file_untouched(tmp_path, monkeypatch):
    """
    The write that actually caused the damage. save_source_files() overwrites the
    files that get uploaded to Hugging Face, so an empty write here is what
    reached the dataset.
    """
    import config

    source_words = tmp_path / "src_invalid_words.txt"
    source_dict = tmp_path / "src_invalid_dict.json"
    source_words.write_text("qqqq\nxyzzy\n", encoding="utf-8")
    source_dict.write_bytes(orjson.dumps({"qqqq": {}}))

    monkeypatch.setattr(config, "VALID_WORDS_FILE", tmp_path / "src_valid_words.txt")
    monkeypatch.setattr(config, "VALID_DICT_FILE", tmp_path / "src_valid_dict.json")
    monkeypatch.setattr(config, "INVALID_WORDS_FILE", source_words)
    monkeypatch.setattr(config, "INVALID_DICT_FILE", source_dict)

    manager = make_manager(tmp_path)  # loads an empty invalid list
    manager.save_source_files()

    assert source_words.read_text(encoding="utf-8") == "qqqq\nxyzzy\n"
    assert orjson.loads(source_dict.read_bytes()) == {"qqqq": {}}


def test_source_files_are_written_when_data_is_present(tmp_path, monkeypatch):
    import config

    source_words = tmp_path / "src_invalid_words.txt"
    source_dict = tmp_path / "src_invalid_dict.json"
    source_words.write_text("stale\n", encoding="utf-8")
    source_dict.write_bytes(orjson.dumps({"stale": {}}))

    monkeypatch.setattr(config, "VALID_WORDS_FILE", tmp_path / "src_valid_words.txt")
    monkeypatch.setattr(config, "VALID_DICT_FILE", tmp_path / "src_valid_dict.json")
    monkeypatch.setattr(config, "INVALID_WORDS_FILE", source_words)
    monkeypatch.setattr(config, "INVALID_DICT_FILE", source_dict)

    manager = make_manager(
        tmp_path, invalid_words=("qqqq", "xyzzy"), invalid_dict={"qqqq": {}, "xyzzy": {}}
    )
    manager.save_source_files()

    assert source_words.read_text(encoding="utf-8").split() == ["qqqq", "xyzzy"]
    assert set(orjson.loads(source_dict.read_bytes())) == {"qqqq", "xyzzy"}


# --- the loop ----------------------------------------------------------------

def test_a_damaged_download_cannot_perpetuate_itself(tmp_path, monkeypatch):
    """
    End to end: given the exact conditions of 2026-01-25 -- a downloaded invalid
    list that is present but empty -- a run must leave nothing behind that would
    be uploaded and re-downloaded tomorrow.
    """
    import config

    remote_copy = tmp_path / "remote_invalid_words.txt"
    remote_copy.write_text("qqqq\nxyzzy\nzzzz\n", encoding="utf-8")

    monkeypatch.setattr(config, "VALID_WORDS_FILE", tmp_path / "src_valid_words.txt")
    monkeypatch.setattr(config, "VALID_DICT_FILE", tmp_path / "src_valid_dict.json")
    monkeypatch.setattr(config, "INVALID_WORDS_FILE", remote_copy)
    monkeypatch.setattr(config, "INVALID_DICT_FILE", tmp_path / "remote_invalid_dict.json")

    out = tmp_path / "out"
    out.mkdir()

    for _ in range(3):  # three consecutive damaged runs
        manager = make_manager(tmp_path)
        manager.save_data(output_dir=out)
        manager.save_source_files()

    assert remote_copy.read_text(encoding="utf-8") == "qqqq\nxyzzy\nzzzz\n"
    assert not (out / "merged_invalid_words.txt").exists()
