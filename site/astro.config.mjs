// The English OpenList's site: static pages for Cloudflare Pages, with React
// islands for the search and the charts.
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

export default defineConfig({
  site: 'https://english-openlist.pages.dev',
  integrations: [react()],
  build: { format: 'directory' },
  // keep the whitespace as written: compression drops the space before an
  // inline element that starts a source line
  compressHTML: false,
  devToolbar: { enabled: false },
  vite: { worker: { format: 'es' } },
});
