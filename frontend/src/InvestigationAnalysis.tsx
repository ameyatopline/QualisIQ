import { useEffect, useId, useRef } from "react";
import { Activity, AlertTriangle, SlidersHorizontal } from "lucide-react";

type HistoryPoint = {
  result_id: number;
  value: string;
  signed_z: string | null;
  measured_at: string;
  outcome: string;
  source_system: string;
  source_record_id: string;
  is_current: boolean;
};
export type AnalysisData = {
  event_number: string;
  current_result_id: number;
  current_value: string;
  unit: string;
  cohort: { site: string; material: string; test: string };
  specification: {
    version: string;
    lower: string | null;
    upper: string | null;
    within_limits: boolean | null;
  };
  baseline: {
    version: string;
    mean: string;
    sigma: string;
    threshold: string;
    n: number;
    method: string;
  } | null;
  oot_status: string;
  oot_reason: string | null;
  history: HistoryPoint[];
  window: { shown: number; available: number; truncated: boolean };
  synthetic: boolean;
  notice: string;
};
const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumSignificantDigits: 7,
});
const number = (value: number | string) =>
  numberFormatter.format(Number(value));
const color = (outcome: string) =>
  outcome === "OOS" ? "#bf6964" : outcome === "OOT" ? "#bc8b3d" : "#6194d7";
type Reference = { value: number; label: string; color: string };

function bounds(values: number[]) {
  const min = Math.min(...values),
    max = Math.max(...values);
  const span = max - min || Math.abs(max) * 0.2 || 1;
  const low = min - span * 0.14,
    high = max + span * 0.14;
  const rough = (high - low) / 4,
    power = 10 ** Math.floor(Math.log10(rough));
  const factor = [1, 2, 2.5, 5, 10].find((n) => n >= rough / power) || 10;
  const step = factor * power,
    bottom = Math.floor(low / step) * step,
    top = Math.ceil(high / step) * step;
  const ticks = Array.from(
    { length: Math.min(12, Math.round((top - bottom) / step) + 1) },
    (_, i) => bottom + i * step,
  );
  return { bottom, top, ticks };
}

function ResultChart({
  points,
  field,
  references,
  band,
  unit,
  label,
}: {
  points: HistoryPoint[];
  field: "value" | "signed_z";
  references: Reference[];
  band: [number | null, number | null] | null;
  unit: string;
  label: string;
}) {
  const clip = useId().replaceAll(":", "");
  const scroll = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = scroll.current;
    if (!element) return;
    const revealCase = () => {
      element.scrollLeft = element.scrollWidth - element.clientWidth;
    };
    revealCase();
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(revealCase);
    observer?.observe(element);
    return () => observer?.disconnect();
  }, [points]);
  const values = points.map((p) =>
    p[field] === null ? null : Number(p[field]),
  );
  const finite = values.filter(
    (v): v is number => v !== null && Number.isFinite(v),
  );
  if (!finite.length)
    return (
      <div className="analysis-unavailable">
        No comparable values available.
      </div>
    );
  if (values.some((v) => v !== null && !Number.isFinite(v)))
    return (
      <div className="analysis-unavailable">
        A result exceeds the chart’s supported numeric range. Review the source
        results.
      </div>
    );
  const { bottom, top, ticks } = bounds([
    ...finite,
    ...references.map((r) => r.value),
  ]);
  const w = 640,
    h = 250,
    left = 60,
    right = 27,
    plotTop = 28,
    plotBottom = h - 52;
  const x = (i: number) =>
    points.length === 1
      ? (left + w - right) / 2
      : left + (i * (w - left - right)) / (points.length - 1);
  const y = (v: number) =>
    plotBottom - ((v - bottom) * (plotBottom - plotTop)) / (top - bottom);
  const segments: string[][] = [[]];
  values.forEach((v, i) => {
    if (v === null) segments.push([]);
    else segments.at(-1)!.push(`${x(i)},${y(v)}`);
  });
  const current = points.findIndex((p) => p.is_current);
  const dateTicks = [
    ...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1]),
  ];
  return (
    <div
      ref={scroll}
      className="case-chart-scroll"
      tabIndex={0}
      aria-label={label + " plot area"}
    >
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label}>
        <title>{label}</title>
        <desc>
          {points.length} observations ordered by measurement time and result
          ID. Dashed lines show stored reference limits. The outlined point is
          the current investigation result. Exact values and source records are
          in the source results table.
        </desc>
        <defs>
          <clipPath id={clip}>
            <rect
              x={left - 8}
              y={plotTop - 8}
              width={w - left - right + 16}
              height={plotBottom - plotTop + 16}
            />
          </clipPath>
        </defs>
        <text x={left - 12} y={13} textAnchor="end" className="case-axis-unit">
          {unit}
        </text>
        {band && (
          <rect
            x={left}
            y={y(band[1] ?? top)}
            width={w - left - right}
            height={Math.max(0, y(band[0] ?? bottom) - y(band[1] ?? top))}
            fill="#edf4ff"
          />
        )}
        {ticks.map((tick, i) => (
          <g key={i}>
            <line
              x1={left}
              y1={y(tick)}
              x2={w - right}
              y2={y(tick)}
              stroke="#e3eaf4"
              strokeDasharray="3 5"
            />
            <text
              x={left - 10}
              y={y(tick) + 4}
              textAnchor="end"
              className="case-axis-label"
            >
              {number(tick)}
            </text>
          </g>
        ))}
        {references.map((r) => (
          <g key={r.label}>
            <line
              x1={left}
              y1={y(r.value)}
              x2={w - right}
              y2={y(r.value)}
              stroke={r.color}
              strokeDasharray={
                r.value === 0 && field === "signed_z" ? "2 3" : "6 4"
              }
              strokeWidth="1.2"
            />
            <text
              x={w - right - 15}
              y={y(r.value) - 5}
              textAnchor="end"
              className="case-reference-label"
              fill={r.color}
            >
              {r.label}
            </text>
          </g>
        ))}
        <g clipPath={`url(#${clip})`}>
          {current >= 0 && (
            <line
              x1={x(current)}
              y1={plotTop}
              x2={x(current)}
              y2={plotBottom}
              stroke="#6e9cdc"
              strokeDasharray="2 4"
              opacity=".6"
            />
          )}
          {segments
            .filter((segment) => segment.length > 1)
            .map((segment, i) => (
              <polyline
                key={i}
                points={segment.join(" ")}
                fill="none"
                stroke="#83a4ce"
                strokeWidth="1.6"
              />
            ))}
          {points.map((p, i) =>
            values[i] === null ? null : (
              <g
                key={p.result_id}
                data-current={p.is_current ? "true" : undefined}
              >
                {p.is_current && (
                  <circle
                    cx={x(i)}
                    cy={y(values[i]!)}
                    r="8"
                    fill="white"
                    stroke="#2d70c8"
                    strokeWidth="2"
                  />
                )}
                <circle
                  cx={x(i)}
                  cy={y(values[i]!)}
                  r={p.is_current ? 4.5 : 3}
                  fill={color(p.outcome)}
                  stroke="white"
                  strokeWidth="1"
                >
                  <title>
                    {p.is_current ? "Current case · " : ""}
                    {p.source_record_id} · {p.measured_at} ·{" "}
                    {field === "signed_z" ? "Z " : ""}
                    {number(values[i]!)} {unit} · {p.outcome}
                  </title>
                </circle>
              </g>
            ),
          )}
        </g>
        {dateTicks.map((i) => (
          <g key={i}>
            <line
              x1={x(i)}
              y1={plotBottom + 3}
              x2={x(i)}
              y2={plotBottom + 7}
              stroke="#b8c8dd"
            />
            <text
              x={x(i)}
              y={plotBottom + 22}
              textAnchor="middle"
              className="case-axis-label"
            >
              {points[i].measured_at.slice(0, 10)}
            </text>
          </g>
        ))}
        <text x={left} y={h - 4} className="case-axis-unit">
          Chronological result sequence · UTC dates
        </text>
      </svg>
    </div>
  );
}

export function InvestigationAnalysis({
  data,
  error,
  loading,
  limit,
  onLimitChange,
}: {
  data: AnalysisData | null;
  error: string;
  loading: boolean;
  limit: number;
  onLimitChange: (limit: number) => void;
}) {
  if (loading)
    return <div className="loading">Loading investigation graphs…</div>;
  if (error)
    return (
      <div className="error" role="alert">
        <AlertTriangle size={16} />
        {error}
      </div>
    );
  if (!data) return null;
  const spec = data.specification,
    baseline = data.baseline;
  const current = data.history.find((p) => p.is_current);
  const specReferences: Reference[] = [];
  if (spec.lower !== null)
    specReferences.push({
      value: Number(spec.lower),
      label: `LSL ${number(spec.lower)}`,
      color: "#ba776d",
    });
  if (spec.upper !== null)
    specReferences.push({
      value: Number(spec.upper),
      label: `USL ${number(spec.upper)}`,
      color: "#ba776d",
    });
  return (
    <section
      className="investigation-analysis"
      aria-label="Investigation result analysis"
    >
      <div className="analysis-toolbar">
        <div className="analysis-cohort">
          <span>{data.cohort.site}</span>
          <span>{data.cohort.material}</span>
          <strong>{data.cohort.test}</strong>
        </div>
        <label>
          <SlidersHorizontal size={14} />
          <span className="sr-only">History window</span>
          <select
            aria-label="History window"
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
          >
            {[20, 40, 80].map((n) => (
              <option key={n} value={n}>
                {n} results
              </option>
            ))}
          </select>
        </label>
      </div>
      <dl className="analysis-readout">
        <div>
          <dt>Case result</dt>
          <dd>
            {number(data.current_value)} <span>{data.unit}</span>
          </dd>
        </div>
        <div>
          <dt>Specification</dt>
          <dd>
            {spec.lower === null ? "—" : number(spec.lower)} –{" "}
            {spec.upper === null ? "—" : number(spec.upper)}{" "}
            <span>{data.unit}</span>
          </dd>
        </div>
        <div>
          <dt>Case Z-score</dt>
          <dd>
            {current?.signed_z === null || current?.signed_z === undefined
              ? "Not assessed"
              : number(current.signed_z)}
          </dd>
        </div>
      </dl>
      <section className="case-chart-card">
        <header>
          <h3>
            <AlertTriangle size={15} />
            OOS · Specification
          </h3>
          <span
            className={`analysis-status ${spec.within_limits === false ? "outside" : ""}`}
          >
            {spec.within_limits === null
              ? "No limits"
              : spec.within_limits
                ? "Within limits"
                : "Outside limits"}
          </span>
        </header>
        <ResultChart
          points={data.history}
          field="value"
          references={specReferences}
          band={
            spec.lower === null && spec.upper === null
              ? null
              : [
                  spec.lower === null ? null : Number(spec.lower),
                  spec.upper === null ? null : Number(spec.upper),
                ]
          }
          unit={data.unit}
          label="OOS specification chart"
        />
        <div className="analysis-chart-key">
          <span className="case-key-current" />
          Current case
          <span className="case-key-rule" />
          Specification limits
          <span className="case-key-outcome oos" />
          OOS
          <span className="case-key-outcome oot" />
          OOT
          <span className="analysis-version">{spec.version}</span>
        </div>
      </section>
      <section className="case-chart-card">
        <header>
          <h3>
            <Activity size={16} />
            OOT · Baseline trend
          </h3>
          <span className="analysis-status">
            {baseline ? "Stored demo baseline" : "Not assessed"}
          </span>
        </header>
        {baseline ? (
          <>
            <div className="analysis-baseline">
              <span>
                Mean{" "}
                <strong>
                  {number(baseline.mean)} {data.unit}
                </strong>
              </span>
              <span>
                σ <strong>{number(baseline.sigma)}</strong>
              </span>
              <span>
                Baseline N <strong>{baseline.n}</strong>
              </span>
              <span>
                Threshold <strong>±{number(baseline.threshold)} Z</strong>
              </span>
            </div>
            <ResultChart
              points={data.history}
              field="signed_z"
              references={[
                { value: 0, label: "Baseline mean (Z = 0)", color: "#6e90bc" },
                {
                  value: Number(baseline.threshold),
                  label: `+${number(baseline.threshold)} Z`,
                  color: "#bb954e",
                },
                {
                  value: -Number(baseline.threshold),
                  label: `−${number(baseline.threshold)} Z`,
                  color: "#bb954e",
                },
              ]}
              band={[-Number(baseline.threshold), Number(baseline.threshold)]}
              unit="Z"
              label="OOT baseline chart"
            />
            <div className="analysis-chart-key">
              <span className="case-key-current" />
              Current case
              <span className="case-key-rule amber" />
              Demo trend thresholds
              <span className="case-key-outcome oos" />
              OOS
              <span className="case-key-outcome oot" />
              OOT
              <span className="analysis-version">{baseline.version}</span>
            </div>
            {data.oot_status === "CONTEXT_ONLY_OOS" && (
              <div className="analysis-context">
                OOS takes precedence. Z-scores are shown as context only.
              </div>
            )}
          </>
        ) : (
          <div className="analysis-unavailable">
            <Activity size={24} />
            <strong>OOT not assessed</strong>
            <span>{data.oot_reason}</span>
          </div>
        )}
      </section>
      <div className="analysis-window">
        {data.window.shown} of {data.window.available} comparable results · Same
        site, material, test, unit and specification · Ending at the case result
      </div>
      <details className="analysis-data">
        <summary>Source results ({data.history.length})</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Measured at (UTC)</th>
                <th>Result ({data.unit})</th>
                <th>Outcome</th>
                <th>Signed Z</th>
                <th>Source record</th>
              </tr>
            </thead>
            <tbody>
              {data.history.map((p) => (
                <tr
                  key={p.result_id}
                  data-current={p.is_current ? "true" : undefined}
                >
                  <td>
                    {p.is_current && (
                      <span className="analysis-current-tag">Case</span>
                    )}
                    {p.measured_at.replace("T", " ").replace("Z", "")}
                  </td>
                  <td>{p.value}</td>
                  <td>{p.outcome}</td>
                  <td>{p.signed_z === null ? "Not assessed" : p.signed_z}</td>
                  <td>
                    {p.source_system} / {p.source_record_id}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <div className="analysis-notice">
        <AlertTriangle size={14} />
        {data.notice}
      </div>
    </section>
  );
}
