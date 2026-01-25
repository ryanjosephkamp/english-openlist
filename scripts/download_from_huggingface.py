"""
Hugging Face Dataset Downloader
Downloads word lists from Hugging Face Datasets Hub.

This module:
- Authenticates with Hugging Face (if token available)
- Downloads the FULL word lists from the data/ folder
- Saves them to initial_deliverables/ for use by update scripts

This is used by GitHub Actions to bootstrap the environment before
running the daily update pipeline.
"""

import logging
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download, HfApi

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    HF_TOKEN, HF_DATASET_REPO,
    VALID_WORDS_FILE, VALID_DICT_FILE, INVALID_WORDS_FILE, INVALID_DICT_FILE,
    INITIAL_DELIVERABLES
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class HuggingFaceDownloader:
    """
    Downloads English OpenList data from Hugging Face Datasets.
    """
    
    def __init__(self, token: str = None, repo_id: str = None):
        self.token = token or HF_TOKEN
        self.repo_id = repo_id or HF_DATASET_REPO
        self.api = HfApi()
    
    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Download a single file from Hugging Face.
        
        Args:
            remote_path: Path in the HF repository (e.g., "data/merged_valid_words.txt")
            local_path: Local path to save the file
            
        Returns:
            True if download successful
        """
        try:
            # Ensure parent directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            downloaded_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=remote_path,
                repo_type="dataset",
                token=self.token if self.token else None,
                local_dir=str(local_path.parent.parent),  # Go up to get correct subpath
                local_dir_use_symlinks=False
            )
            
            # Move to expected location if needed
            downloaded = Path(downloaded_path)
            if downloaded != local_path and downloaded.exists():
                # Copy content to expected path
                local_path.write_bytes(downloaded.read_bytes())
            
            logger.info(f"Downloaded {remote_path} -> {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {remote_path}: {e}")
            return False
    
    def download_all_wordlists(self, skip_large_dicts: bool = False) -> bool:
        """
        Download all word lists from Hugging Face.
        
        Downloads:
        - data/merged_valid_words.txt -> initial_deliverables/merged_valid_words.txt
        - data/merged_valid_dict.json -> initial_deliverables/merged_valid_dict.json
        - data/merged_invalid_words.txt -> initial_deliverables/merged_invalid_words.txt
        - data/merged_invalid_dict.json -> initial_deliverables/merged_invalid_dict.json (optional)
        
        Args:
            skip_large_dicts: If True, skip downloading the large invalid dict (11GB+)
        
        Returns:
            True if all required downloads successful
        """
        # Ensure output directory exists
        INITIAL_DELIVERABLES.mkdir(parents=True, exist_ok=True)
        
        files_to_download = [
            ("data/merged_valid_words.txt", VALID_WORDS_FILE),
            ("data/merged_valid_dict.json", VALID_DICT_FILE),
            ("data/merged_invalid_words.txt", INVALID_WORDS_FILE),
        ]
        
        # Only download the large invalid dict if not skipping
        if not skip_large_dicts:
            files_to_download.append(("data/merged_invalid_dict.json", INVALID_DICT_FILE))
        else:
            logger.info("Skipping large invalid dict download (--skip-large-dicts)")
        
        all_success = True
        for remote_path, local_path in files_to_download:
            success = self.download_file(remote_path, local_path)
            if not success:
                all_success = False
        
        return all_success
    
    def download_with_snapshot(self, skip_large_dicts: bool = False) -> bool:
        """
        Alternative download method using snapshot_download.
        Downloads only the data/ folder.
        
        Args:
            skip_large_dicts: If True, skip downloading the large invalid dict (11GB+)
        
        Returns:
            True if download successful
        """
        from huggingface_hub import snapshot_download
        import shutil
        
        try:
            # Ensure output directory exists
            INITIAL_DELIVERABLES.mkdir(parents=True, exist_ok=True)
            
            # Define patterns - exclude the huge invalid dict if requested
            allow_patterns = ["data/merged_valid_words.txt", 
                            "data/merged_valid_dict.json",
                            "data/merged_invalid_words.txt"]
            
            if not skip_large_dicts:
                allow_patterns.append("data/merged_invalid_dict.json")
            else:
                logger.info("Skipping large invalid dict download (--skip-large-dicts)")
            
            # Download the data folder
            local_dir = snapshot_download(
                repo_id=self.repo_id,
                repo_type="dataset",
                token=self.token if self.token else None,
                allow_patterns=allow_patterns,
                local_dir_use_symlinks=False
            )
            
            # Copy files from data/ to initial_deliverables/
            data_dir = Path(local_dir) / "data"
            if data_dir.exists():
                for file in data_dir.iterdir():
                    dest = INITIAL_DELIVERABLES / file.name
                    shutil.copy2(file, dest)
                    logger.info(f"Copied {file.name} to {dest}")
            
            return True
            
        except Exception as e:
            logger.error(f"Snapshot download failed: {e}")
            return False


def main():
    """Main entry point for downloading from Hugging Face."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download English OpenList from Hugging Face")
    parser.add_argument("--method", choices=["individual", "snapshot"], default="snapshot",
                       help="Download method: individual files or snapshot")
    parser.add_argument("--skip-large-dicts", action="store_true",
                       help="Skip downloading the large invalid dict (11GB+) to save space")
    args = parser.parse_args()
    
    print("=" * 60)
    print("English OpenList - Download from Hugging Face")
    print("=" * 60)
    print(f"Repository: {HF_DATASET_REPO}")
    print(f"Target directory: {INITIAL_DELIVERABLES}")
    if args.skip_large_dicts:
        print("Skipping large dictionary files to save disk space")
    print()
    
    downloader = HuggingFaceDownloader()
    
    if args.method == "snapshot":
        success = downloader.download_with_snapshot(skip_large_dicts=args.skip_large_dicts)
    else:
        success = downloader.download_all_wordlists(skip_large_dicts=args.skip_large_dicts)
    
    if success:
        print("\n✓ Download successful!")
        
        # Show file sizes
        print("\nDownloaded files:")
        for f in INITIAL_DELIVERABLES.iterdir():
            if f.is_file() and not f.name.startswith('.'):
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  {f.name}: {size_mb:.2f} MB")
        
        return 0
    else:
        print("\n✗ Download failed!")
        return 1


if __name__ == "__main__":
    exit(main())
