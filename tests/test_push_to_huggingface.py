import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.push_to_huggingface import (
    BRRRDLE_REMOTE_PATHS,
    RELEASE_EXCLUDES,
    HuggingFaceUploader,
)


class FakeHfApi:
    def __init__(self):
        self.uploads = []

    def upload_folder(self, **kwargs):
        self.uploads.append(kwargs)


def test_upload_brrrdle_artifacts_uploads_to_latest_and_data_paths(tmp_path):
    brrrdle_dir = tmp_path / "output" / "2026-05-24" / "brrrdle"
    brrrdle_dir.mkdir(parents=True)
    (brrrdle_dir / "brrrdle_words.txt").write_text("apple\n")
    fake_api = FakeHfApi()
    uploader = HuggingFaceUploader(token="fake-token", repo_id="owner/repo")
    uploader.api = fake_api
    uploader.authenticate = lambda: True
    uploader.ensure_repo_exists = lambda: True

    assert uploader.upload_brrrdle_artifacts(brrrdle_dir=brrrdle_dir)

    assert [upload["path_in_repo"] for upload in fake_api.uploads] == list(BRRRDLE_REMOTE_PATHS)
    assert all(upload["folder_path"] == str(brrrdle_dir) for upload in fake_api.uploads)
    assert all(upload["repo_id"] == "owner/repo" for upload in fake_api.uploads)
    assert all(upload["repo_type"] == "dataset" for upload in fake_api.uploads)


def test_upload_brrrdle_artifacts_fails_when_directory_missing(tmp_path):
    fake_api = FakeHfApi()
    uploader = HuggingFaceUploader(token="fake-token", repo_id="owner/repo")
    uploader.api = fake_api

    assert not uploader.upload_brrrdle_artifacts(brrrdle_dir=tmp_path / "missing")
    assert fake_api.uploads == []


def _release_dir(tmp_path):
    """A release directory shaped like the one the daily run produces."""
    release = tmp_path / "output" / "2026-08-11"
    (release / "brrrdle").mkdir(parents=True)
    (release / "CHANGELOG.md").write_text("# 2026-08-11\n")
    (release / "update_stats.json").write_text("{}\n")
    (release / "merged_valid_dict.json").write_text("{}\n")
    (release / "merged_valid_words.txt").write_text("alpha\n")
    (release / "brrrdle" / "brrrdle_words.txt").write_text("alpha\n")
    return release


def test_upload_release_excludes_the_full_lists_from_the_dated_folder(tmp_path):
    """
    releases/{date}/ is the record of what changed that day. The full lists live
    in data/ and latest/, one copy each -- shipping them per release put 168
    near-identical 290 MB snapshots on the Hub.
    """
    fake_api = FakeHfApi()
    uploader = HuggingFaceUploader(token="fake-token", repo_id="owner/repo")
    uploader.api = fake_api
    uploader.authenticate = lambda: True
    uploader.ensure_repo_exists = lambda: True

    assert uploader.upload_release(
        release_dir=_release_dir(tmp_path), release_date="2026-08-11"
    )

    dated, latest = fake_api.uploads
    assert dated["path_in_repo"] == "releases/2026-08-11"
    assert set(dated["ignore_patterns"]) == set(RELEASE_EXCLUDES)
    for pattern in ("merged_valid_dict.json", "merged_valid_words.txt", "brrrdle/**"):
        assert pattern in dated["ignore_patterns"]

    # latest/ is the current snapshot and still gets everything.
    assert latest["path_in_repo"] == "latest"
    assert not latest.get("ignore_patterns")
