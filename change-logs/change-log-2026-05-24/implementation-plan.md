# Implementation Plan

## 1. Confirm existing repository conventions

- Treat committed `output/YYYY-MM-DD/` files as the existing release-output convention.
- Do not introduce committed repository folders named `latest/brrrdle/` or `data/brrrdle/`.

## 2. Generate Brrrdle artifacts

- Generate the Brrrdle-specific word-list artifacts as transient build outputs.
- Keep any temporary local staging outside committed source paths, or clean it before commit.

## 3. Upload to Hugging Face

- Upload Brrrdle “latest” artifacts to Hugging Face path `latest/brrrdle/`.
- Upload Brrrdle full dataset artifacts to Hugging Face path `data/brrrdle/`.
- Treat those paths as remote Hugging Face dataset destinations only.

## 4. Repository cleanliness

- Do not commit generated Brrrdle artifacts unless they belong under an already-established committed output convention.
- If needed, add ignore rules to prevent accidental commits of local `latest/` or `data/brrrdle/` staging folders.

## 5. Validation

- Run existing tests after implementation.
- Verify Hugging Face upload paths are correct without requiring committed local `latest/brrrdle/` or `data/brrrdle/` folders.

## Clarification questions

None.

## Additional recommendations

Add `.gitignore` protection for local `latest/` and `data/brrrdle/` staging paths if implementation creates them temporarily.
