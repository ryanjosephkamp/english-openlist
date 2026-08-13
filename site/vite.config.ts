import type { IncomingMessage, ServerResponse } from 'node:http';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

/**
 * Serve `*.br` with `Content-Encoding: br`, the way `_headers` does in
 * production.
 *
 * Vite knows nothing about `_headers`, so without this the loader's preference
 * for the pre-compressed artifact would be exercised for the first time on
 * Cloudflare. It would still work — the decoded-length check falls back — but
 * it would fall back on every local run, so the path that ships would be the
 * one nobody had ever seen succeed.
 */
function brotliHeaders(): Plugin {
  const middleware = (req: IncomingMessage, res: ServerResponse, next: () => void): void => {
    if (req.url?.split('?')[0]?.endsWith('.br')) {
      res.setHeader('Content-Encoding', 'br');
      res.setHeader('Content-Type', 'application/octet-stream');
    }
    next();
  };

  return {
    name: 'eol-brotli-headers',
    configureServer: (server) => void server.middlewares.use(middleware),
    configurePreviewServer: (server) => void server.middlewares.use(middleware),
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), brotliHeaders()],
  worker: { format: 'es' },
  build: {
    target: 'es2022',
    // The word and metadata artifacts are content-hashed and served
    // pre-compressed; never inline them.
    assetsInlineLimit: 0,
  },
  server: { port: 5174 },
});
