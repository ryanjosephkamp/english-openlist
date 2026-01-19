"""
Hugging Face Dataset Uploader
Uploads release files to Hugging Face Datasets Hub.

This module:
- Authenticates with Hugging Face
- Creates/updates dataset repository
- Uploads FULL word lists (complete dataset) to data/ folder
- Uploads release/changelog files to releases/{date}/ folder
- Updates dataset card (README)

IMPORTANT: Users can download the FULL word lists from:
- data/merged_valid_words.txt
- data/merged_valid_dict.json
- data/merged_invalid_words.txt
- data/merged_invalid_dict.json

Daily releases (delta files) are stored in releases/{date}/
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from huggingface_hub import HfApi, login, create_repo
from huggingface_hub.utils import RepositoryNotFoundError

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    HF_TOKEN, HF_DATASET_REPO, HF_DATASET_PRIVATE,
    get_release_date, get_release_dir, PHASE3_ROOT,
    VALID_WORDS_FILE, VALID_DICT_FILE, INVALID_WORDS_FILE, INVALID_DICT_FILE
)

logger = logging.getLogger(__name__)


class HuggingFaceUploader:
    """
    Uploads English OpenList releases to Hugging Face Datasets.
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        repo_id: Optional[str] = None
    ):
        self.token = token or HF_TOKEN
        self.repo_id = repo_id or HF_DATASET_REPO
        self.api = HfApi()
        
        if not self.token:
            logger.warning("HF_TOKEN not set. Uploads will fail.")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Hugging Face Hub.
        
        Returns:
            True if authentication successful
        """
        if not self.token:
            logger.error("No Hugging Face token provided")
            return False
        
        try:
            login(token=self.token)
            logger.info("Authenticated with Hugging Face Hub")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def ensure_repo_exists(self) -> bool:
        """
        Create the dataset repository if it doesn't exist.
        
        Returns:
            True if repo exists or was created
        """
        try:
            # Check if repo exists
            self.api.repo_info(
                repo_id=self.repo_id,
                repo_type="dataset"
            )
            logger.info(f"Repository {self.repo_id} exists")
            return True
            
        except RepositoryNotFoundError:
            # Create the repo
            try:
                create_repo(
                    repo_id=self.repo_id,
                    repo_type="dataset",
                    private=HF_DATASET_PRIVATE,
                    exist_ok=True
                )
                logger.info(f"Created repository {self.repo_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to create repository: {e}")
                return False
        except Exception as e:
            logger.error(f"Error checking repository: {e}")
            return False
    
    def upload_release(
        self,
        release_dir: Optional[Path] = None,
        release_date: Optional[str] = None
    ) -> bool:
        """
        Upload a release to Hugging Face.
        
        Args:
            release_dir: Directory containing release files
            release_date: Date string for release folder name
            
        Returns:
            True if upload successful
        """
        release_dir = release_dir or get_release_dir()
        release_date = release_date or get_release_date()
        
        if not release_dir.exists():
            logger.error(f"Release directory not found: {release_dir}")
            return False
        
        if not self.authenticate():
            return False
        
        if not self.ensure_repo_exists():
            return False
        
        try:
            # Upload to releases/{date}/ folder (daily changes only)
            self.api.upload_folder(
                folder_path=str(release_dir),
                path_in_repo=f"releases/{release_date}",
                repo_id=self.repo_id,
                repo_type="dataset",
                commit_message=f"Daily update: {release_date}"
            )
            logger.info(f"Uploaded release {release_date}")
            
            # Also update the 'latest' folder with release files
            self.api.upload_folder(
                folder_path=str(release_dir),
                path_in_repo="latest",
                repo_id=self.repo_id,
                repo_type="dataset",
                commit_message=f"Update latest to {release_date}"
            )
            logger.info("Updated 'latest' folder")
            
            return True
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def upload_full_wordlists(self) -> bool:
        """
        Upload the FULL word lists to Hugging Face.
        
        This uploads the complete merged word lists and dictionaries to the
        data/ folder, allowing users to download the full dataset.
        
        Files uploaded:
        - data/merged_valid_words.txt     - Complete valid word list
        - data/merged_valid_dict.json     - Complete valid dictionary with metadata
        - data/merged_invalid_words.txt   - Complete invalid word list  
        - data/merged_invalid_dict.json   - Complete invalid dictionary
        
        Returns:
            True if upload successful
        """
        if not self.authenticate():
            return False
        
        if not self.ensure_repo_exists():
            return False
        
        files_to_upload = [
            (VALID_WORDS_FILE, "data/merged_valid_words.txt"),
            (VALID_DICT_FILE, "data/merged_valid_dict.json"),
            (INVALID_WORDS_FILE, "data/merged_invalid_words.txt"),
            (INVALID_DICT_FILE, "data/merged_invalid_dict.json"),
        ]
        
        all_success = True
        for local_path, remote_path in files_to_upload:
            if not local_path.exists():
                logger.warning(f"File not found, skipping: {local_path}")
                continue
            
            try:
                self.api.upload_file(
                    path_or_fileobj=str(local_path),
                    path_in_repo=remote_path,
                    repo_id=self.repo_id,
                    repo_type="dataset",
                    commit_message=f"Update full wordlist: {remote_path}"
                )
                logger.info(f"Uploaded {local_path.name} to {remote_path}")
            except Exception as e:
                logger.error(f"Failed to upload {local_path.name}: {e}")
                all_success = False
        
        return all_success
    
    def upload_dataset_card(self, readme_path: Optional[Path] = None) -> bool:
        """
        Upload or update the dataset card (README.md).
        
        Args:
            readme_path: Path to README.md file
            
        Returns:
            True if upload successful
        """
        readme_path = readme_path or (PHASE3_ROOT / "templates" / "dataset_card.md")
        
        if not readme_path.exists():
            logger.warning(f"Dataset card not found: {readme_path}")
            return False
        
        try:
            self.api.upload_file(
                path_or_fileobj=str(readme_path),
                path_in_repo="README.md",
                repo_id=self.repo_id,
                repo_type="dataset",
                commit_message="Update dataset card"
            )
            logger.info("Updated dataset card")
            return True
        except Exception as e:
            logger.error(f"Failed to upload dataset card: {e}")
            return False


def main():
    """Main entry point for Hugging Face upload."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload English OpenList to Hugging Face")
    parser.add_argument("--release-dir", type=Path, help="Release directory to upload")
    parser.add_argument("--date", type=str, help="Release date (YYYY-MM-DD)")
    parser.add_argument("--skip-full", action="store_true", help="Skip uploading full word lists")
    parser.add_argument("--only-full", action="store_true", help="Only upload full word lists (skip release)")
    parser.add_argument("--update-readme", action="store_true", help="Update the dataset card (README.md)")
    args = parser.parse_args()
    
    uploader = HuggingFaceUploader()
    success = True
    
    # Upload the release (daily changes) unless --only-full is set
    if not args.only_full:
        release_success = uploader.upload_release(
            release_dir=args.release_dir,
            release_date=args.date
        )
        if release_success:
            print("✓ Uploaded release files")
        else:
            print("✗ Failed to upload release files")
            success = False
    
    # Upload full word lists unless --skip-full is set
    if not args.skip_full:
        full_success = uploader.upload_full_wordlists()
        if full_success:
            print("✓ Uploaded full word lists to data/")
        else:
            print("✗ Failed to upload full word lists")
            success = False
    
    # Update the dataset card (README.md)
    readme_success = uploader.upload_dataset_card()
    if readme_success:
        print("✓ Updated dataset card")
    else:
        print("✗ Failed to update dataset card")
        # Don't fail the whole upload if README fails
    
    if success:
        print("\nUpload successful!")
        return 0
    else:
        print("\nUpload completed with errors!")
        return 1


if __name__ == "__main__":
    exit(main())
