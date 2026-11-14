import { readdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { CORRECTIONS_DIR } from './paths.ts';

/**
 * The list's record of corrections, counted from the ledgers in `corrections/`.
 *
 * Every word moved by hand is a row of a ledger first, with its reason, its
 * method, and its date. The rule page states these counts; they come from the
 * committed ledgers on every build, never from prose.
 */

export type LedgerCount = {
  readonly ledger: string;
  readonly action: string;
  readonly date: string;
  readonly count: number;
};

/** A minimal CSV reader: quoted fields, doubled quotes, commas inside quotes. */
export function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i]!;
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else field += c;
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows.filter((r) => r.length > 1 || r[0] !== '');
}

export async function buildRecord(): Promise<LedgerCount[]> {
  const names = (await readdir(CORRECTIONS_DIR)).filter((n) => /^ledger_.*\.csv$/.test(n)).sort();
  const counts = new Map<string, LedgerCount>();
  for (const name of names) {
    const [header, ...rows] = parseCsv(await readFile(resolve(CORRECTIONS_DIR, name), 'utf8'));
    const actionAt = header!.indexOf('action');
    const dateAt = header!.indexOf('decided_date');
    if (actionAt < 0 || dateAt < 0) throw new Error(`${name}: no action or decided_date column`);
    for (const row of rows) {
      const action = row[actionAt] ?? '';
      const date = (row[dateAt] ?? '').slice(0, 10);
      const key = `${name}|${action}|${date}`;
      const found = counts.get(key);
      counts.set(key, { ledger: name, action, date, count: (found?.count ?? 0) + 1 });
    }
  }
  return [...counts.values()].sort((a, b) => a.date.localeCompare(b.date) || a.ledger.localeCompare(b.ledger));
}
