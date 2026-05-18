#!/usr/bin/env python3
"""
OED Unigram Extractor (brand-new helper script)
Handles BOTH hyperlinked and non-hyperlinked OED update pages.
Saves raw candidates to manual_catchup_2026-05/oed_raw/ for backup.
"""

import re
import sys
from pathlib import Path
import requests

def extract_unigrams(url: str, list_type: str) -> list[str]:
    """Extract unigrams from an OED update page using your exact rules."""
    print(f"📥 Fetching {url} ({list_type})...")
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    html = response.text

    if list_type == "hyperlinked":
        # Extract text inside [brackets] before first comma
        pattern = r'\[([^,\]]+?)(?:,|\])'
        matches = re.findall(pattern, html)
    elif list_type == "non-hyperlinked":
        # Extract text before first comma or colon in bullet lines
        pattern = r'[-•]\s*([^\s,:\n]+(?:\s+[^\s,:\n]+)*?)(?:,|:|\n)'
        matches = re.findall(pattern, html)
    else:
        raise ValueError("list_type must be 'hyperlinked' or 'non-hyperlinked'")

    # Clean each match: remove everything before and including '/' for X/x cases
    candidates = []
    for m in matches:
        m = m.strip()
        if '/' in m:
            m = m.split('/', 1)[-1]          # keep only after the last /
        if m:
            candidates.append(m)

    # Remove duplicates within this page
    candidates = sorted(set(candidates))
    print(f"   → Found {len(candidates)} raw candidates")
    return candidates

def save_raw_candidates(url: str, candidates: list[str], list_type: str):
    """Save raw candidates to oed_raw/ for backup."""
    slug = url.rstrip('/').split('/')[-2] if 'previous-updates' in url else url.rstrip('/').split('/')[-1]
    filename = f"oed_raw/{slug}_{list_type}.txt"
    Path("manual_catchup_2026-05/oed_raw").mkdir(parents=True, exist_ok=True)

    with open(f"manual_catchup_2026-05/{filename}", "w", encoding="utf-8") as f:
        f.write(f"# Raw candidates from {url} ({list_type})\n")
        f.write(f"# Extracted: {len(candidates)} unigrams\n\n")
        for word in candidates:
            f.write(word + "\n")
    print(f"   📁 Saved raw → manual_catchup_2026-05/{filename}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/extract_oed_unigrams.py <URL> <hyperlinked|non-hyperlinked>")
        sys.exit(1)

    url = sys.argv[1]
    list_type = sys.argv[2]
    candidates = extract_unigrams(url, list_type)
    save_raw_candidates(url, candidates, list_type)
    print("\n✅ Raw candidates ready for rule checking!")
    for w in candidates[:15]:
        print("   ", w)
    if len(candidates) > 15:
        print(f"   ... and {len(candidates)-15} more")
