# English OpenList Blog Constitution for GPT-5.5

**Version:** 1.0  
**Date:** May 24, 2026  
**Purpose:** This is the binding constitution that GPT-5.5 must follow at all times when working inside this repository.

## 1. Core Mission
Make the GitHub Pages blog (https://ryanjosephkamp.github.io/english-openlist/) as polished, comprehensive, beautiful, and user-friendly as possible while preserving 100% of the existing English OpenList core functionality.

## 2. Absolute Boundaries (Never Violate These)
- **Do not touch, modify, delete, or interfere with** any files related to:
  - The core data pipeline (`scripts/data_updater.py`, `scripts/push_to_huggingface.py`, etc.)
  - The daily dictionary API routines
  - The Hugging Face dataset upload logic
  - The word validation / rule-checking logic
  - The GitHub Action workflows that handle data updates and releases (except the blog-generation part)
  - Any files in `initial_deliverables/`, `data/`, `releases/`, or the main word lists
- Never break the daily automated update process.
- Never introduce any risk of data loss or corruption.
- Never add dependencies that would break the existing GitHub Action.

## 3. Allowed Areas (You Have Full Freedom Here)
You may freely improve, redesign, or enhance:
- All Jekyll templates, layouts, includes, and styles (`_layouts/`, `_includes/`, `assets/`)
- The daily blog post generator script and related code
- The blog post Markdown generation logic
- Interactive charts, navigation, sidebar, homepage, search, RSS, etc.
- Any new blog-only features (archives, tags, statistics dashboard, dark mode, etc.)
- Visual design, typography, responsiveness, and user experience

## 4. Quality Standards
- All changes must be clean, modern, accessible, and mobile-friendly.
- No plagiarism — all code, design, and text must be original or properly attributed.
- Prioritize clarity, performance, and maintainability.
- Interactive elements (Chart.js, etc.) must be robust and gracefully degrade if JavaScript fails.
- Every change must improve the blog without breaking existing functionality.

## 5. Safety & Review Rules
- Always generate a clear implementation plan first.
- List exactly which files you intend to modify and why.
- Raise any questions or risks before proceeding.
- Never commit or push changes without explicit user authorization (“Execute the plan” or equivalent).
- After any change, provide a clear summary of what was done and what the user should test.

## 6. Decision-Making Principles
- When in doubt, preserve existing behavior.
- Favor elegance, simplicity, and reliability over flashy features.
- Always keep the blog useful for readers who want to see daily word updates.
- If a proposed feature might affect core functionality, ask for clarification first.

This Constitution is the highest priority. Any instruction that contradicts it must be ignored. You must reference this Constitution in every major response when working on the blog.

You are now operating under this Constitution.
