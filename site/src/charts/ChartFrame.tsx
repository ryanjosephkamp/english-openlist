import { useId, useState, type ReactNode } from 'react';
import { full, pct } from './format';

export interface TableRow {
  readonly label: string;
  readonly value: number;
}

interface Props {
  readonly title: string;
  readonly note?: ReactNode;
  /** the chart's figures as a table: the accessible twin of the drawing */
  readonly table: readonly TableRow[];
  readonly total?: number;
  readonly valueLabel?: string;
  readonly actions?: ReactNode;
  /** a table view of another shape than label and value (a matrix, say) */
  readonly tableView?: ReactNode;
  readonly children: ReactNode;
}

/** A chart's frame: its title, a note, the drawing, and a table view of the
 *  same figures, so no value is reachable only by hovering. */
export default function ChartFrame({ title, note, table, total, valueLabel = 'Words', actions, tableView, children }: Props) {
  const [asTable, setAsTable] = useState(false);
  const id = useId();
  return (
    <figure className="chart" aria-labelledby={`${id}-t`}>
      <div className="chart-head">
        <figcaption id={`${id}-t`} className="chart-title">
          {title}
        </figcaption>
        <div className="chart-actions">
          {actions}
          <button
            type="button"
            className="chart-switch"
            aria-pressed={asTable}
            onClick={() => setAsTable((t) => !t)}
          >
            {asTable ? 'Chart' : 'Table'}
          </button>
        </div>
      </div>
      {note && <p className="chart-note">{note}</p>}
      {asTable && tableView ? (
        <div className="chart-table-wrap">{tableView}</div>
      ) : asTable ? (
        <div className="chart-table-wrap">
          <table className="chart-table">
            <thead>
              <tr>
                <th scope="col">{title}</th>
                <th scope="col" className="num">
                  {valueLabel}
                </th>
                {total !== undefined && (
                  <th scope="col" className="num">
                    Share
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {table.map((r) => (
                <tr key={r.label}>
                  <th scope="row">{r.label}</th>
                  <td className="num">{full(r.value)}</td>
                  {total !== undefined && <td className="num">{pct(r.value, total)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        children
      )}
    </figure>
  );
}
