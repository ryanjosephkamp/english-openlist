/**
 * The channels a word came in by, as the CEOL Universe names them, with the
 * labels it withholds taken out.
 *
 * A record names a channel 2 ways: `source`, the intake its record was written
 * by, and `candidate_source`, the discovery log of where the string was first
 * seen (each entry suffixed `_valid` or `_unlikely`). The discovery log is a
 * record of intake, never evidence that a source lists the word.
 *
 * The CEOL Universe withholds 6 of these labels from every public file for
 * license reasons: the tournament word list, Collins, the COCA frequency list,
 * the Merriam-Webster API, and the Linux and NLTK word lists. This site and its
 * data files follow the same rule: a withheld label is dropped, and the count
 * of words whose every channel is withheld appears only in the build's log.
 */

export type ChannelKey =
  | 'google_ngrams'
  | 'wiktionary'
  | 'wikipedia'
  | 'opensource'
  | 'libreoffice'
  | 'enable'
  | 'wordnet'
  | 'synthetic_engine'
  | 'free_dictionary'
  | 'authoritative_extracts'
  | 'extended_domain_sources'
  | 'invalid_list_recovery';

/** The published channels, in the order the charts list them, with their names. */
export const CHANNELS: readonly { key: ChannelKey; label: string; kind: 'discovery' | 'record' }[] = [
  { key: 'google_ngrams', label: 'Google Books Ngram counts', kind: 'discovery' },
  { key: 'wiktionary', label: 'Wiktionary', kind: 'discovery' },
  { key: 'wikipedia', label: 'Wikipedia', kind: 'discovery' },
  { key: 'opensource', label: 'Open-source word lists', kind: 'discovery' },
  { key: 'libreoffice', label: 'LibreOffice dictionaries', kind: 'discovery' },
  { key: 'enable', label: 'ENABLE', kind: 'discovery' },
  { key: 'wordnet', label: 'WordNet', kind: 'discovery' },
  { key: 'synthetic_engine', label: 'The synthetic engine', kind: 'record' },
  { key: 'free_dictionary', label: 'The Free Dictionary API', kind: 'record' },
  { key: 'authoritative_extracts', label: 'Domain extracts', kind: 'record' },
  { key: 'extended_domain_sources', label: 'Extended domain sources', kind: 'record' },
  { key: 'invalid_list_recovery', label: 'The nightly run (promoted from the invalid list)', kind: 'record' },
];

/** `source` values and the channel each names; null is a withheld channel. */
const SOURCE_CHANNELS: Readonly<Record<string, ChannelKey | null>> = {
  twl_scrabble_dictionary: null,
  'merriam-webster': null,
  'merriam-webster-medical': null,
  synthetic_generation: 'synthetic_engine',
  'free-dictionary': 'free_dictionary',
  authoritative_extracts: 'authoritative_extracts',
  extended_domain_sources: 'extended_domain_sources',
  invalid_list_recovery: 'invalid_list_recovery',
};

/** Discovery-log names and the channel each names; null is a withheld channel. */
const DISCOVERY_CHANNELS: Readonly<Record<string, ChannelKey | null>> = {
  google_ngrams: 'google_ngrams',
  wiktionary: 'wiktionary',
  wikipedia: 'wikipedia',
  opensource: 'opensource',
  libreoffice: 'libreoffice',
  enable: 'enable',
  wordnet: 'wordnet',
  coca_frequency: null,
  linux: null,
  nltk: null,
  collins: null,
};

export type Channels =
  | { readonly kind: 'published'; readonly keys: readonly ChannelKey[] }
  | { readonly kind: 'withheld' }
  | { readonly kind: 'unrecorded' };

/**
 * A record's channels. Throws on a label outside the known vocabulary, so a new
 * channel cannot reach a public file before someone decides whether it may.
 */
export function channelsOf(record: { source?: unknown; candidate_source?: unknown }): Channels {
  const published = new Set<ChannelKey>();
  let withheld = 0;

  const note = (channel: ChannelKey | null | undefined, label: string) => {
    if (channel === undefined) throw new Error(`unknown channel label: ${label}`);
    if (channel === null) withheld++;
    else published.add(channel);
  };

  if (typeof record.source === 'string') note(SOURCE_CHANNELS[record.source], `source ${record.source}`);

  if (Array.isArray(record.candidate_source)) {
    for (const raw of record.candidate_source) {
      if (typeof raw !== 'string') continue;
      const name = raw.replace(/_(valid|unlikely)$/, '');
      note(DISCOVERY_CHANNELS[name], `candidate_source ${raw}`);
    }
  }

  if (published.size > 0) {
    const keys = CHANNELS.map((c) => c.key).filter((k) => published.has(k));
    return { kind: 'published', keys };
  }
  return withheld > 0 ? { kind: 'withheld' } : { kind: 'unrecorded' };
}
