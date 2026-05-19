#!/usr/bin/env python3
"""
Deduplicate OED candidates + frequency distribution
Brand-new script for Phase 1 – goes in existing scripts/ folder.
"""

from collections import Counter
import sys

# Paste the exact content of your oed_candidates.txt here (or read from file)
content = """[PASTE THE FULL CONTENT OF YOUR oed_candidates.txt HERE]"""

lines = [line.strip() for line in content.splitlines() if line.strip()]
# Skip header lines
words = [w for w in lines if not w.startswith('#') and not w.startswith('OED Candidates') and not w.startswith('One unigram') and not w.startswith('These are unique')]

freq = Counter(words)
unique_sorted = sorted(set(words))

print(f"Total unique unigrams: {len(unique_sorted)}")

# Save unique list
with open("manual_catchup_2026-05/oed_unique_unigrams.txt", "w", encoding="utf-8") as f:
    f.write("# OED Unique Unigrams (deduplicated, sorted)\n")
    f.write("# Total: " + str(len(unique_sorted)) + "\n\n")
    f.write("\n".join(unique_sorted) + "\n")

# Save frequency CSV
with open("manual_catchup_2026-05/oed_frequency_distribution.csv", "w", encoding="utf-8") as f:
    f.write("word,count\n")
    for word in unique_sorted:
        f.write(f"{word},{freq[word]}\n")

print("✅ Files created in manual_catchup_2026-05/")