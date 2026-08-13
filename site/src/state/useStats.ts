import { useEffect, useState } from 'react';

export type Stats = {
  readonly lengths: readonly { length: number; count: number }[];
  readonly letters: readonly { letter: string; count: number }[];
  readonly letterPosition: {
    readonly positions: number;
    readonly counts: readonly (readonly number[])[];
    readonly columnTotals: readonly number[];
  };
  readonly intakeByLength: readonly {
    length: number;
    total: number;
    counts: readonly number[];
  }[];
  readonly growth: {
    readonly recordedFrom: string;
    readonly recordedTo: string;
    readonly daysRecorded: number;
    readonly daysUnrecorded: number;
    readonly first: number;
    readonly last: number;
    readonly events: readonly { date: string; delta: number; total: number }[];
  };
};

/**
 * The precomputed aggregates, fetched on demand.
 *
 * Only the Shape page needs them, so they are not part of the first load — the
 * explorer stays at 666 KB whether or not anyone visits this page.
 */
export function useStats(): { stats: Stats | null; error: string | null } {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    const url = `${import.meta.env.BASE_URL}data/stats.json`.replace(/\/{2,}/g, '/');

    fetch(url)
      .then((response) => {
        if (!response.ok) throw new Error(`stats.json: HTTP ${response.status}`);
        return response.json() as Promise<Stats>;
      })
      .then((value) => live && setStats(value))
      .catch((cause: unknown) => {
        if (live) setError(cause instanceof Error ? cause.message : String(cause));
      });

    return () => {
      live = false;
    };
  }, []);

  return { stats, error };
}
