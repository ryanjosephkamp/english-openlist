#!/usr/bin/env python3
"""
Manual Catch-Up Merger v4 - Correct HF subfolder + flattened files
Downloads ONLY from data/ subfolder and flattens them for DataUpdater.
"""
import sys
import json
from pathlib import Path
import subprocess
import shutil

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("Installing huggingface_hub...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
    from huggingface_hub import hf_hub_download

sys.path.append(str(Path(__file__).parent.parent))
from scripts.data_updater import DataUpdater

def download_minimal_from_hf():
    print("📥 Downloading ONLY the two valid files from HF (data/ subfolder)...")
    files = ["merged_valid_words.txt", "merged_valid_dict.json"]
    target_dir = Path("initial_deliverables")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for filename in files:
        hf_filename = f"data/{filename}"
        try:
            hf_hub_download(
                repo_id="ryanjosephkamp/english-openlist",
                filename=hf_filename,
                repo_type="dataset",
                local_dir=target_dir,
                local_dir_use_symlinks=False
            )
            # Flatten the file out of the data/ subfolder
            src = target_dir / "data" / filename
            dst = target_dir / filename
            if src.exists():
                shutil.move(src, dst)
                print(f"   ✅ Downloaded and flattened {filename}")
            else:
                print(f"   ⚠️  Downloaded but file not in expected location")
        except Exception as e:
            print(f"   ❌ Failed to download {filename}: {e}")
    
    # Tiny placeholders for invalid files (DataUpdater needs them)
    for placeholder in ["merged_invalid_words.txt", "merged_invalid_dict.json"]:
        path = target_dir / placeholder
        if not path.exists():
            path.write_text("# Placeholder - not used in this merge\n", encoding="utf-8")
            print(f"   ✅ Created tiny placeholder {placeholder}")
    
    return target_dir

def main():
    catchup_dir = Path("manual_catchup_2026-05")
    validated_file = catchup_dir / "oed_validated_words.json
