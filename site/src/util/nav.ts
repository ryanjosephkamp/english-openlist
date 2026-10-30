import { CEOL_PUBLIC } from './release-state';

/** The site's sections, in header order. */
export interface Section {
  readonly label: string;
  readonly href: string;
}

export const SECTIONS: readonly Section[] = [
  { label: 'Search', href: '/' },
  { label: 'Charts', href: '/charts/' },
  { label: 'Rule and record', href: '/rule/' },
  { label: 'Downloads', href: '/downloads/' },
  ...(CEOL_PUBLIC ? [{ label: 'In the CEOL Universe', href: '/universe/' }] : []),
];
