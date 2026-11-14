import type { AttesterKey } from './format.ts';

/**
 * The open sources a word can be listed by: each one's name as the site shows
 * it, and its home. `ATTESTERS` in `format.ts` holds their order.
 */
export const ATTESTER_INFO: Readonly<Record<AttesterKey, { readonly label: string; readonly url: string }>> = {
  wiktionary: { label: 'Wiktionary', url: 'https://en.wiktionary.org/' },
  wordnet: { label: 'WordNet', url: 'https://wordnet.princeton.edu/' },
  scowl: { label: 'SCOWL', url: 'http://wordlist.aspell.net/' },
  libreoffice: { label: 'LibreOffice dictionaries', url: 'https://github.com/LibreOffice/dictionaries/tree/master/en' },
  enable: { label: 'ENABLE', url: 'https://github.com/dolph/dictionary' },
  wordfreq: { label: 'wordfreq', url: 'https://github.com/rspeer/wordfreq' },
};

/** Where the attesting sources' notices and licenses are. */
export const NOTICES_URL = 'https://huggingface.co/datasets/ryanjosephkamp/english-openlist/blob/main/NOTICES.md';
