#!/usr/bin/env python3
"""
Manual Catch-up MW Verifier
Now prints full WordLookupResult for BOTH VALID and REJECTED words.
"""

import sys
import json
import time
from pathlib import Path

sys.path.append(".")

from dictionary_api import lookup_word_sync

def main():
    input_file = "manual_catchup_2026-05/oed_new_candidates_for_mw.txt"
    output_dir = Path("manual_catchup_2026-05")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 Starting MW verification on OED new candidates (detailed output)...")

    with open(input_file, "r", encoding="utf-8") as f:
        candidates = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Found {len(candidates)} candidates to verify.\n")

    valid_words = []
    rejected_words = []

    for i, word in enumerate(candidates, 1):
        print(f"[{i:3d}/{len(candidates)}] Checking: {word}")
        
        result = lookup_word_sync(word)

        status = getattr(result, 'status', None)
        status_value = status.value if hasattr(status, 'value') else str(status)

        if status_value == "valid":
            valid_words.append(result.__dict__ if hasattr(result, '__dict__') else {"word": word})
            print(f"   ✅ VALID: {word}")
            print(f"      {result}")          # ← Full result printed here
        else:
            reason = getattr(result, 'reason', str(result)) if result else "No API response"
            rejected_words.append({"word": word, "reason": reason})
            print(f"   ❌ REJECTED: {word} → {reason}")
            print(f"      {result}")          # Full result printed here too

        time.sleep(2)   # rate-limit protection

    # Save results
    with open(output_dir / "oed_validated_words.json", "w", encoding="utf-8") as f:
        json.dump(valid_words, f, indent=2, default=str)

    with open(output_dir / "oed_mw_rejected.txt", "w", encoding="utf-8") as f:
        f.write("# OED Words Rejected by MW (for manual review)\n")
        f.write(f"# Total rejected: {len(rejected_words)}\n\n")
        for item in rejected_words:
            f.write(f"{item['word']} → {item['reason']}\n")

    print("\n" + "="*70)
    print("✅ VERIFICATION COMPLETE")
    print(f"   Validated by MW : {len(valid_words)}")
    print(f"   Rejected by MW  : {len(rejected_words)}")
    print(f"   Files saved in  : {output_dir}/")
    print("   • oed_validated_words.json")
    print("   • oed_mw_rejected.txt")
    print("="*70)

if __name__ == "__main__":
    main()
