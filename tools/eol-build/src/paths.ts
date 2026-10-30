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
 * builds skip the download entirely. `EOL_SOURCE_DIR` points the build at
 * another folder of the same 3 files, read-only, such as a pinned revision's.
 */
export const CACHE_DIR = process.env['EOL_SOURCE_DIR'] ? resolve(process.env['EOL_SOURCE_DIR']) : resolve(ROOT, '.cache/hf');
export const VALID_WORDS = resolve(CACHE_DIR, 'merged_valid_words.txt');
export const VALID_DICT = resolve(CACHE_DIR, 'merged_valid_dict.json');
export const INVALID_WORDS = resolve(CACHE_DIR, 'merged_invalid_words.txt');

/** Repo-local inputs, committed by the daily pipeline. */
export const UPDATES_LOG = resolve(ROOT, 'updates/updates_log.csv');
export const DAILY_METRICS_DIR = resolve(ROOT, 'archive/daily-metrics');
export const CORRECTIONS_DIR = resolve(ROOT, 'corrections');

/** Build outputs. Never committed; regenerated on every deploy. */
export const DATA_DIR = resolve(ROOT, 'site/public/data');
export const DOWNLOADS_DIR = resolve(ROOT, 'site/public/downloads');

export const HF_REPO = 'ryanjosephkamp/english-openlist';
/** The dataset revision to read: `EOL_REVISION`, or the current `main`. */
export const HF_REVISION = process.env['EOL_REVISION'] || 'main';
export const HF_BASE = `https://huggingface.co/datasets/${HF_REPO}/resolve/${HF_REVISION}`;
