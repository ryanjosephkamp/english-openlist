#!/usr/bin/env python3
"""
Manual Catch-up MW Verifier
Validates OED new candidates using your existing Merriam-Webster API.
Brand-new script — no existing files modified.
"""

import sys
import json
from pathlib import Path

# Import your existing dictionary API (it must be in the same scripts/ folder or PYTHONPATH)
sys.path.append(".")
from dictionary_api import lookup_word

def main():
    input_file = "manual_catchup_2026-05/oed_new_candidates_for_mw.txt"
    output_dir = Path("manual_catchup_2026-05")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 Starting MW verification on OED new candidates...")

    with open(input_file, "r", encoding="utf-8") as f:
        candidates = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Found {len(candidates)} candidates to verify.\n")

    valid_words = []
    rejected_words = []

    for i, word in enumerate(candidates, 1):
        print(f"[{i:3d}/{len(candidates)}] Checking: {word}")
        result = lookup_word(word)

        if result and result.get("status") == "valid":
            valid_words.append(result)
            print(f"   ✅ VALID: {word}")
        else:
            reason = result.get("reason", "MW API rejected or no definition") if result else "No API response"
            rejected_words.append({"word": word, "reason": reason})
            print(f"   ❌ REJECTED: {word} → {reason}")

    # Save valid words with full metadata
    with open(output_dir / "oed_validated_words.json", "w", encoding="utf-8") as f:
        json.dump(valid_words, f, indent=2)

    # Save rejected words for manual review
    with open(output_dir / "oed_mw_rejected.txt", "w", encoding="utf-8") as f:
        f.write("# OED Words Rejected by MW (for manual review)\n")
        f.write(f"# Total rejected: {len(rejected_words)}\n\n")
        for item in rejected_words:
            f.write(f"{item['word']} → {item['reason']}\n")

    print("\n" + "="*60)
    print("✅ VERIFICATION COMPLETE")
    print(f"   Validated by MW : {len(valid_words)}")
    print(f"   Rejected by MW  : {len(rejected_words)}")
    print(f"   Files saved in  : {output_dir}/")
    print("   • oed_validated_words.json")
    print("   • oed_mw_rejected.txt")
    print("="*60)

if __name__ == "__main__":
    main()
