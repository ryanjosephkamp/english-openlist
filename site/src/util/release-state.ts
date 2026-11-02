/**
 * Whether the CEOL Universe is public.
 *
 * The English OpenList is a dated subset of each version of the CEOL Universe,
 * which is not released yet. Until it is, this site renders no link to it and
 * no page about it: `scripts/check-dist.mjs` fails the build if one appears.
 * At the CEOL's release, set this to true; the family link in the header and
 * the footer, and the page "The EOL in the CEOL Universe", then build. The
 * README gains the same family link by hand at the same time.
 */
export const CEOL_PUBLIC = false;

/** The CEOL Universe's site, and its page about the English OpenList. */
export const CEOL_SITE = 'https://common-english-openlist.pages.dev/';
export const CEOL_EOL_PAGE = `${CEOL_SITE}eol/`;
export const CEOL_COMPOSE_EOL = `${CEOL_SITE}compose/?d.eol=true`;
