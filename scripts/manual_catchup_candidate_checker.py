#!/usr/bin/env python3
"""
Manual Catch-up Candidate Rule Checker
Strictly enforces English OpenList rules + unigram-only constraint.
Brand-new script — no existing files were modified.
"""

CANDIDATES = [
    "affable",
    "badassery",
    "burrata",
    "capicola",
    "freestyle",
    "fyp",
    "idgaf",
    "maga",
    "snog",
    # ← Add any additional candidates here later
]

def passes_rules(word: str) -> tuple[bool, str]:
    """Return (passes, reason)"""
    original = word

    # Must be a unigram (no spaces, no hyphens) — non-negotiable
    if " " in original or "-" in original:
        return False, "contains space or hyphen (unigrams only)"

    # Lowercase and check only a-z
    lower = original.lower()
    if not lower.isalpha():
        return False, "contains non-letter characters"

    # Length check
    if len(lower) < 2 or len(lower) > 45:
        return False, f"length {len(lower)} (must be 2-45 characters)"

    return True, "passes all rules"

def main():
    print("🔍 English OpenList – Manual Catch-up Candidate Rule Checker")
    print("=" * 70)
    print(f"Candidates checked: {len(CANDIDATES)}\n")

    passed = []
    rejected = []

    for word in CANDIDATES:
        passes, reason = passes_rules(word)
        if passes:
            passed.append(word.lower())
            print(f"✅ PASSED: {word}")
        else:
            rejected.append((word, reason))
            print(f"❌ REJECTED: {word} → {reason}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print(f"✅ Candidates that pass all rules : {len(passed)}")
    print(f"❌ Candidates that fail rules     : {len(rejected)}")
    print("=" * 70)

    print("\nPASSED (ready for next step):")
    for w in sorted(passed):
        print("   ", w)

    print("\nREJECTED:")
    for w, reason in sorted(rejected):
        print(f"   {w} → {reason}")

    # Create the new output folder and save results
    import os
    output_dir = "manual_catchup_2026-05"
    os.makedirs(output_dir, exist_ok=True)

    with open(f"{output_dir}/passed_rule_check.txt", "w", encoding="utf-8") as f:
        for w in sorted(passed):
            f.write(w + "\n")

    with open(f"{output_dir}/rejected_candidates.txt", "w", encoding="utf-8") as f:
        for w, reason in sorted(rejected):
            f.write(f"{w} → {reason}\n")

    print(f"\n📁 Results saved to new folder: {output_dir}/")
    print("   • passed_rule_check.txt")
    print("   • rejected_candidates.txt")

if __name__ == "__main__":
    main()