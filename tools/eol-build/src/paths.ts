import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

/** Repository root — three levels up from `tools/eol-build/src`. */
export const ROOT = resolve(here, '../../..');

/**
 * Downloaded Hugging Face sources.
 *
 * Gitignored, and cached across CI runs keyed on the dataset revision: the
 * 291 MB metadata dictionary only changes on days a word is promoted, so most
 * builds skip the download entirely.
 */
export const CACHE_DIR = resolve(ROOT, '.cache/hf');
export const VALID_WORDS = resolve(CACHE_DIR, 'merged_valid_words.txt');
export const VALID_DICT = resolve(CACHE_DIR, 'merged_valid_dict.json');
export const INVALID_WORDS = resolve(CACHE_DIR, 'merged_invalid_words.txt');

/** Repo-local inputs, committed by the daily pipeline. */
export const UPDATES_LOG = resolve(ROOT, 'updates/updates_log.csv');
export const OVERALL_STATS = resolve(ROOT, 'overall_stats.json');
export const POSTS_DIR = resolve(ROOT, '_posts');

/** Build outputs. Never committed; regenerated on every deploy. */
export const DATA_DIR = resolve(ROOT, 'site/public/data');
export const DOWNLOADS_DIR = resolve(ROOT, 'site/public/downloads');

export const HF_REPO = 'ryanjosephkamp/english-openlist';
export const HF_BASE = `https://huggingface.co/datasets/${HF_REPO}/resolve/main`;
