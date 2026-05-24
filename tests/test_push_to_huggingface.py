import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.push_to_huggingface import BRRRDLE_REMOTE_PATHS, HuggingFaceUploader


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
