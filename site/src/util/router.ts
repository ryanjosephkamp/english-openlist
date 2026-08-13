import { useCallback, useEffect, useState } from 'react';

/**
 * Routing, in forty lines.
 *
 * Five static pages and one parameterised one do not need a router library, and
 * the site's whole point is that it ships a small payload. `_redirects` sends
 * every path to `index.html` so a deep link lands here rather than on a 404.
 */
export type Route = {
  readonly path: string;
  readonly search: string;
};

function current(): Route {
  return { path: window.location.pathname, search: window.location.search };
}

export function useRoute(): {
  route: Route;
  navigate: (to: string, options?: { replace?: boolean }) => void;
} {
  const [route, setRoute] = useState<Route>(current);

  useEffect(() => {
    const onPop = () => setRoute(current());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const navigate = useCallback((to: string, options?: { replace?: boolean }) => {
    const next = new URL(to, window.location.origin);
    if (next.pathname + next.search === window.location.pathname + window.location.search) return;

    // Query edits replace rather than push. Typing eight letters into the search
    // field should not cost eight presses of the back button.
    if (options?.replace) window.history.replaceState(null, '', to);
    else window.history.pushState(null, '', to);

    setRoute({ path: next.pathname, search: next.search });
  }, []);

  return { route, navigate };
}

/** Intercept in-app link clicks so they route without a full page load. */
export function useLinkInterception(navigate: (to: string) => void): void {
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const anchor = (event.target as Element | null)?.closest?.('a');
      if (!(anchor instanceof HTMLAnchorElement)) return;
      if (anchor.target === '_blank' || anchor.hasAttribute('download')) return;
      if (anchor.origin !== window.location.origin) return;

      event.preventDefault();
      navigate(anchor.pathname + anchor.search);
      window.scrollTo(0, 0);
    };

    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [navigate]);
}
