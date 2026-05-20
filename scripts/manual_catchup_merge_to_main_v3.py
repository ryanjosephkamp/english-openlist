#!/usr/bin/env python3
"""
Manual Catch-Up Merger v3 - Minimal HF download (Colab-safe)
Downloads ONLY the two valid files from HF. Skips huge invalid dict.
Creates tiny placeholders for invalid files so DataUpdater works.
"""
import sys
import json
from pathlib import Path
import subprocess

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("Installing huggingface_hub...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
    from huggingface_hub import hf_hub_download

sys.path.append(str(Path(__file__).parent.parent))
from scripts.data_updater import DataUpdater

def download_minimal_from_hf():
    print("📥 Downloading ONLY needed valid files from Hugging Face...")
    files_to_download = [
        "merged_valid_words.txt",
        "merged_valid_dict.json"
    ]
    target_dir = Path("initial_deliverables")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for filename in files_to_download:
        try:
            hf_hub_download(
                repo_id="ryanjosephkamp/english-openlist",
                filename=filename,
                repo_type="dataset",
                local_dir=target_dir,
                local_dir_use_symlinks=False
            )
            print(f"   ✅ Downloaded {filename}")
        except Exception as e:
            print(f"   ❌ Failed to download {filename}: {e}")
    
    # Create tiny placeholders for the two invalid files (DataUpdater needs them)
    for placeholder in ["merged_invalid_words.txt", "merged_invalid_dict.json"]:
        path = target_dir / placeholder
        if not path.exists():
            path.write_text("# Placeholder - not used in this merge\n", encoding="utf-8")
            print(f"   ✅ Created tiny placeholder {placeholder}")
    
    return target_dir

def main():
    catchup_dir = Path("manual_catchup_2026-05")
    validated_file = catchup_dir / "oed_validated_words.json"
    
    if not validated_file.exists():
        print("❌ Validated JSON not found in manual_catchup_2026-05/")
        return
    
    # Step 1: Download only what we need
    download_minimal_from_hf()
    
    print("\n🔄 Loading your 201 validated OED words...")
    with open(validated_file, "r", encoding="utf-8") as f:
        validated_list = json.load(f)
    
    new_valid_words = []
    for item in validated_list:
        word = str(item.get("word") or item.get("word", "")).lower().strip()
        if word:
            metadata = item if isinstance(item, dict) else {"word": word}
            new_valid_words.append({"word": word, "metadata": metadata})
    
    print(f"Found {len(new_valid_words)} validated words ready to merge.")
    
    # Step 2: Merge
    updater = DataUpdater()
    output_dir = Path("output") / "2026-05-19"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stats = updater.run_update(new_valid_words, output_dir, update_source_files=True)
    
    print("\n✅ Merge successful!")
    print(f"   • Newly added to valid list : {stats.get('words_added_to_valid', 0)}")
    print(f"   • Promoted from invalid    : {stats.get('words_removed_from_invalid', 0)}")
    print(f"   • Total valid words now    : {stats.get('total_valid', 'N/A')}")
    
    print("\n🎉 Files are now updated in initial_deliverables/ and output/")
    print("   (These large files are ONLY in this Colab session — not on GitHub)")

if __name__ == "__main__":
    main()
