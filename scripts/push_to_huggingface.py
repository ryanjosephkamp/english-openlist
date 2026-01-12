"""
Hugging Face Dataset Uploader
Uploads release files to Hugging Face Datasets Hub.

This module:
- Authenticates with Hugging Face
- Creates/updates dataset repository
- Uploads release files with versioning
- Updates dataset card (README)
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
    get_release_date, get_release_dir, PHASE3_ROOT
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
            # Upload to releases/{date}/ folder
            self.api.upload_folder(
                folder_path=str(release_dir),
                path_in_repo=f"releases/{release_date}",
                repo_id=self.repo_id,
                repo_type="dataset",
                commit_message=f"Weekly update: {release_date}"
            )
            logger.info(f"Uploaded release {release_date}")
            
            # Also update the 'latest' folder
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
    args = parser.parse_args()
    
    uploader = HuggingFaceUploader()
    
    success = uploader.upload_release(
        release_dir=args.release_dir,
        release_date=args.date
    )
    
    if success:
        print("Upload successful!")
        return 0
    else:
        print("Upload failed!")
        return 1


if __name__ == "__main__":
    exit(main())
