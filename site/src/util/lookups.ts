/** Where to read about a word: the list carries no definitions of its own. */
export function lookups(word: string): { label: string; href: string }[] {
  const w = encodeURIComponent(word);
  return [
    { label: 'Google', href: `https://www.google.com/search?q=define+${w}` },
    { label: 'Merriam-Webster', href: `https://www.merriam-webster.com/dictionary/${w}` },
    { label: 'Wiktionary', href: `https://en.wiktionary.org/wiki/${w}#English` },
  ];
}
