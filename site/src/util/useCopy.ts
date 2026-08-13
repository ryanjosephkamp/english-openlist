import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Copy-to-clipboard with a short confirmation.
 *
 * Keyed rather than boolean, so a page with a dozen snippets confirms only the
 * one that was actually copied.
 */
export function useCopy(holdMs = 1400): {
  copied: string | null;
  copy: (key: string, text: string) => void;
} {
  const [copied, setCopied] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => void (timer.current && clearTimeout(timer.current)), []);

  const copy = useCallback(
    (key: string, text: string) => {
      void navigator.clipboard.writeText(text).then(
        () => {
          setCopied(key);
          if (timer.current) clearTimeout(timer.current);
          timer.current = setTimeout(() => setCopied(null), holdMs);
        },
        () => setCopied(null),
      );
    },
    [holdMs],
  );

  return { copied, copy };
}
