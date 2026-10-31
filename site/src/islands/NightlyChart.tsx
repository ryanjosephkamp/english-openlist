import ChartFrame from '../charts/ChartFrame';
import Nightly from '../charts/Nightly';
import { full, plural } from '../charts/format';
import type { NightlyWindow } from '../util/runs';
import '../charts/charts.css';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const longDate = (iso: string) => `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${Number(iso.slice(8))}, ${iso.slice(0, 4)}`;
const sameYear = (a: string, b: string) => a.slice(0, 4) === b.slice(0, 4);
const span = (from: string, to: string) =>
  sameYear(from, to) ? `${longDate(from).replace(/, \d{4}$/, '')} to ${longDate(to)}` : `${longDate(from)} to ${longDate(to)}`;

interface Props {
  readonly window: NightlyWindow;
  /** the daily log's address, ending in a slash */
  readonly base: string;
  readonly title?: string;
}

/** What each nightly run added, with a table that links every run to its log. */
export default function NightlyChart({ window: w, base, title = 'What the nightly run added' }: Props) {
  const gaps = w.gaps.map((g) => span(g.from, g.to));
  return (
    <ChartFrame
      title={title}
      note={
        <>
          Every run from {longDate(w.from)}, the first to promote a word from the invalid list, to {longDate(w.to)}:{' '}
          {plural(w.runs.length, 'run')} added {plural(w.added, 'word')}.
          {gaps.length > 0 && <> No run was recorded from {gaps.join(', or from ')}.</>} Select a day for its log.
        </>
      }
      table={[]}
      tableView={
        <table className="chart-table">
          <thead>
            <tr>
              <th scope="col">Run</th>
              <th scope="col" className="num">
                Words added
              </th>
            </tr>
          </thead>
          <tbody>
            {w.runs.map((r) => (
              <tr key={r.date}>
                <th scope="row">
                  <a href={`${base}${r.date}/`}>{longDate(r.date)}</a>
                </th>
                <td className="num">{r.failed ? 'The run failed' : full(r.added)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <Nightly runs={w.runs} from={w.from} to={w.to} base={base} label="Words added by each nightly run" />
    </ChartFrame>
  );
}
