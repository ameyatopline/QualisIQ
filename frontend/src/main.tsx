import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  AnimatePresence,
  MotionConfig,
  animate,
  motion,
  useDragControls,
  useIsPresent,
  useMotionValue,
  useReducedMotion,
} from "motion/react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Beaker,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Database,
  FileCheck2,
  FileText,
  FlaskConical,
  Globe2,
  LayoutDashboard,
  LogOut,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  X,
  AlertTriangle,
  Layers,
  LockKeyhole,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { InvestigationAnalysis } from "./InvestigationAnalysis";
import "./style.css";

type Data = Record<string, any>;
type User = { role: string; email: string; tenant_id: number; id: number };
const fmt = (v: number | undefined) =>
  new Intl.NumberFormat("en-US").format(v ?? 0);
const pretty = (s: string) =>
  ["OOS", "OOT", "CAPA"].includes(s)
    ? s
    : s
        .replaceAll("_", " ")
        .toLowerCase()
        .replace(/\b\w/g, (c) => c.toUpperCase());
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
async function request(path: string, token: string, options: RequestInit = {}) {
  const response = await fetch("/api/v1" + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const e = await response
      .json()
      .catch(() => ({ detail: "Service unavailable" }));
    if (response.status === 401 && token)
      window.dispatchEvent(new Event("session-expired"));
    throw new Error(
      typeof e.detail === "string"
        ? e.detail
        : `Request rejected (${response.status}). Check your inputs.`,
    );
  }
  return response.json();
}
function useData(path: string, token: string, revision = 0) {
  const [state, set] = useState<{ data: any; error: string; loading: boolean }>(
    { data: null, error: "", loading: true },
  );
  useEffect(() => {
    let active = true;
    set((s) => ({ ...s, loading: true, error: "" }));
    request(path, token)
      .then((data) => {
        if (active) set({ data, error: "", loading: false });
      })
      .catch((e) => {
        if (active) set({ data: null, error: e.message, loading: false });
      });
    return () => {
      active = false;
    };
  }, [path, token, revision]);
  return state;
}
function Badge({ value }: { value: string }) {
  return (
    <span
      className={`badge ${["OOS", "FAILED"].includes(value) ? "red" : ["OOT", "DETECTED", "OPEN"].includes(value) ? "amber" : ["CLOSED", "APPROVED", "VERIFIED"].includes(value) ? "green" : "neutral"}`}
    >
      <i />
      {pretty(value)}
    </span>
  );
}
function ErrorBox({ error }: { error: string }) {
  return error ? (
    <div className="error" role="alert">
      <AlertTriangle size={16} />
      {error}
    </div>
  ) : null;
}
function Empty({
  text = "No records match these filters.",
}: {
  text?: string;
}) {
  return (
    <div className="empty">
      <Database size={26} />
      <p>{text}</p>
    </div>
  );
}
function App() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [sessionMessage, setSessionMessage] = useState("");
  useEffect(() => {
    const expire = () => {
      setToken("");
      setUser(null);
      setSessionMessage("Your session expired. Please sign in again.");
    };
    window.addEventListener("session-expired", expire);
    return () => window.removeEventListener("session-expired", expire);
  }, []);
  return token && user ? (
    <Workbench
      token={token}
      user={user}
      logout={() => {
        setToken("");
        setUser(null);
      }}
    />
  ) : (
    <Login
      message={sessionMessage}
      onLogin={(t, u) => {
        setToken(t);
        setUser(u);
        setSessionMessage("");
      }}
    />
  );
}
function Login({
  onLogin,
  message,
}: {
  onLogin: (t: string, u: User) => void;
  message: string;
}) {
  const [email, setEmail] = useState("qc_analyst@don-demo.test");
  const [password, setPassword] = useState("");
  const [tenant, setTenant] = useState("DON-DEMO");
  const [error, setError] = useState(message);
  const [busy, setBusy] = useState(false);
  async function login(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await request("/auth/login", "", {
        method: "POST",
        body: JSON.stringify({ email, password, tenant_code: tenant }),
      });
      const me = await request("/auth/me", data.access_token);
      onLogin(data.access_token, me);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const reduced = useReducedMotion();
  return (
    <div className="login">
      <section className="login-story" aria-label="QualisIQ workspace">
        <div className="brand">
          <span className="brandmark">
            <Layers size={23} />
          </span>
          QualisIQ
        </div>
        <div className="login-copy">
          <span className="login-category">QUALITY MANAGEMENT</span>
          <h1>
            Quality.
            <br />
            <span>Connected.</span>
          </h1>
          <div className="login-system" aria-label="Connected quality modules">
            <div className="system-core">
              <Layers size={32} />
              <strong>QualisIQ</strong>
            </div>
            <div className="system-grid">
              {[
                [Beaker, "Laboratory"],
                [FlaskConical, "Investigations"],
                [ClipboardCheck, "CAPA"],
                [ShieldCheck, "Evidence"],
              ].map(([Icon, label]) => {
                const ModuleIcon = Icon as LucideIcon;
                return (
                  <div className="system-module" key={String(label)}>
                    <ModuleIcon size={20} />
                    <span>{String(label)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        <div className="story-footer">
          <span className="live-dot" />
          DON QUALITYOS<span>QC / QA</span>
        </div>
      </section>
      <section className="login-form">
        <motion.div
          className="login-form-inner"
          initial={{ opacity: 0, y: reduced ? 0 : 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", bounce: 0, visualDuration: 0.3 }}
        >
          <span className="login-lock">
            <LockKeyhole size={22} />
          </span>
          <h2>Welcome to QualisIQ</h2>
          <ErrorBox error={error} />
          <form onSubmit={login}>
            <label>
              Work email
              <input
                autoComplete="username"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                autoComplete="current-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <label>
              Organization code
              <input
                autoComplete="organization"
                value={tenant}
                onChange={(e) => setTenant(e.target.value)}
                required
              />
            </label>
            <button className="primary login-submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in to workspace"}
              <ArrowRight size={17} />
            </button>
          </form>
          <div className="demo-note">
            <Beaker size={16} />
            <span>Synthetic demo · Not validated for GMP decisions</span>
          </div>
        </motion.div>
      </section>
    </div>
  );
}

const nav = [
  { id: "tower", name: "Control tower", icon: LayoutDashboard },
  { id: "events", name: "Investigations", icon: FlaskConical },
  { id: "sites", name: "Site network", icon: Globe2 },
  { id: "intake", name: "Result intake", icon: Beaker },
  { id: "capas", name: "CAPA worklist", icon: ClipboardCheck },
  { id: "documents", name: "Controlled documents", icon: FileCheck2 },
  { id: "model", name: "QualisIQ intelligence", icon: Sparkles },
  { id: "sources", name: "Source library", icon: Network },
];
function Workbench({
  token,
  user,
  logout,
}: {
  token: string;
  user: User;
  logout: () => void;
}) {
  const [page, setPage] = useState("tower");
  const [site, setSite] = useState("");
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [state, setState] = useState("");
  const [offset, setOffset] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const storage = useData("/workbench/storage", token, revision);
  const sites = useData("/workbench/sites", token, revision);
  const summary = useData(
    "/workbench/summary" + (site ? "?site_id=" + site : ""),
    token,
    revision,
  );
  const trends = useData(
    "/workbench/trends" + (site ? "?site_id=" + site : ""),
    token,
    revision,
  );
  const params = new URLSearchParams({
    q: search,
    limit: "10",
    offset: String(offset),
    ...(kind ? { kind } : {}),
    ...(state ? { state } : {}),
    ...(site ? { site_id: site } : {}),
  });
  const events = useData("/workbench/events?" + params, token, revision);
  useEffect(() => setOffset(0), [search, kind, state, site]);
  const refresh = () => setRevision((v) => v + 1);
  async function exportReport() {
    setExporting(true);
    setExportError("");
    try {
      const report = await request(
        "/workbench/summary" + (site ? "?site_id=" + site : ""),
        token,
      );
      const blob = new Blob(
        [
          JSON.stringify(
            { classification: "SYNTHETIC / NON-GMP", ...report },
            null,
            2,
          ),
        ],
        { type: "application/json" },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "qualisiq-quality-summary.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e) {
      setExportError((e as Error).message);
    } finally {
      setExporting(false);
    }
  }
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brandmark">
            <Layers size={21} />
          </span>
          QualisIQ
        </div>
        <div className="workspace">
          <span className="workspace-icon">DQ</span>
          <div>
            <strong>DON QualityOS</strong>
          </div>
          <span className="workspace-mode">QC</span>
        </div>
        <div className="nav-label">QUALITY MANAGEMENT</div>
        <nav>
          {nav.map(({ id, name, icon: Icon }) => (
            <button
              key={id}
              aria-label={name}
              title={name}
              aria-current={page === id ? "page" : undefined}
              className={page === id ? "nav-item active" : "nav-item"}
              onClick={() => setPage(id)}
            >
              {page === id && (
                <motion.span
                  className="nav-selection"
                  layoutId="nav-selection"
                  transition={{
                    type: "spring",
                    stiffness: 450,
                    damping: 40,
                    mass: 0.8,
                  }}
                />
              )}
              <Icon size={18} />
              <span>{id === "model" ? "Intelligence" : name}</span>
              {id === "events" && summary.data && (
                <small>{fmt(summary.data.open_events)}</small>
              )}
              {id === "model" && <span className="tiny-tag">LAB</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button className="user-block" onClick={logout} aria-label="Sign out">
            <span className="avatar">
              {user.role.slice(0, 2).toUpperCase()}
            </span>
            <span>
              <strong>{pretty(user.role)}</strong>
            </span>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <strong>{nav.find((n) => n.id === page)?.name}</strong>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-btn mobile-logout"
              onClick={logout}
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
            <span className="synthetic-top">
              <i /> Synthetic data
            </span>
            <button
              className="icon-btn"
              onClick={refresh}
              aria-label="Refresh data"
            >
              <RefreshCw size={17} />
            </button>
            <span className="avatar small">
              {user.role.slice(0, 2).toUpperCase()}
            </span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <h1>
                {nav.find((n) => n.id === page)?.name}
                {page === "tower" && (
                  <span className="pill live">
                    <span className="live-dot" /> Live workspace
                  </span>
                )}
              </h1>
            </div>
            <div className="heading-actions">
              {["tower", "events", "capas"].includes(page) && (
                <label className="select-wrap">
                  <Globe2 size={15} />
                  <span className="sr-only">Filter by site</span>
                  <select
                    aria-label="Filter by site"
                    value={site}
                    onChange={(e) => setSite(e.target.value)}
                  >
                    <option value="">All authorized sites</option>
                    {sites.data?.map((s: Data) => (
                      <option key={s.id} value={s.id}>
                        {s.code} · {s.region}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <button
                className="button"
                disabled={exporting}
                onClick={exportReport}
              >
                <ArrowDownToLine size={16} />
                {exporting ? "Exporting…" : "Export summary"}
              </button>
            </div>
          </div>
          <ErrorBox error={summary.error || sites.error || exportError} />
          <div className="database-storage" aria-label="Database storage">
            <Database size={15} aria-hidden="true" />
            <strong>Database</strong>
            {storage.loading ? (
              <span>Loading…</span>
            ) : storage.error ? (
              <span role="status">Location unavailable</span>
            ) : (
              <>
                <span>
                  {storage.data?.backend === "sqlite"
                    ? "SQLite"
                    : storage.data?.backend === "postgresql"
                      ? "PostgreSQL"
                      : storage.data?.backend}
                </span>
                <code>{storage.data?.location}</code>
              </>
            )}
          </div>
          <div className="disclosure">
            <Beaker size={15} />
            <strong>Synthetic demonstration</strong>
            <span>
              Synthetic records · Not validated for GMP or batch release.
            </span>
          </div>
          <motion.div
            className="view-content"
            key={page}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.16 }}
          >
            {page === "tower" && (
              <>
                <div className="kpi-grid">
                  <Kpi
                    title="Laboratory results"
                    value={summary.data?.total_results}
                    icon={Beaker}
                  />
                  <Kpi
                    title="Open investigations"
                    value={summary.data?.open_events}
                    icon={FlaskConical}
                    tone="amber"
                  />
                  <Kpi
                    title="Out-of-specification"
                    value={summary.data?.outcomes.OOS}
                    icon={AlertTriangle}
                    tone="red"
                  />
                  <Kpi
                    title="CAPA records"
                    value={
                      summary.data
                        ? (Object.values(summary.data.capas).reduce(
                            (a: any, b: any) => a + b,
                            0,
                          ) as number)
                        : undefined
                    }
                    icon={ClipboardCheck}
                  />
                </div>
                <div className="chart-grid">
                  <section className="panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Quality signals over time</h2>
                      </div>
                      <span className="muted small-text">Up to 90 days</span>
                    </div>
                    <div className="chart-legend">
                      <span>
                        <i className="legend-oos" />
                        Out of specification
                      </span>
                      <span>
                        <i className="legend-oot" />
                        Out of trend
                      </span>
                    </div>
                    {trends.loading ? (
                      <div className="loading">Loading quality signals…</div>
                    ) : trends.error ? (
                      <ErrorBox error={trends.error} />
                    ) : (
                      <TrendChart data={trends.data || []} />
                    )}
                  </section>
                  <section className="panel outcome-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Result disposition</h2>
                      </div>
                      <Activity size={18} />
                    </div>
                    <Disposition outcomes={summary.data?.outcomes || {}} />
                  </section>
                </div>
              </>
            )}
            {["tower", "events"].includes(page) && (
              <section className="panel event-panel">
                <div className="panel-heading">
                  <div>
                    <h2>
                      {page === "tower"
                        ? "Investigation worklist"
                        : "Quality investigations"}
                      <span className="count">{fmt(events.data?.total)}</span>
                    </h2>
                  </div>
                  {page === "tower" && (
                    <button
                      className="text-btn"
                      onClick={() => setPage("events")}
                    >
                      View all investigations
                      <ArrowRight size={15} />
                    </button>
                  )}
                </div>
                <div className="table-toolbar">
                  <label className="search">
                    <Search size={17} />
                    <input
                      aria-label="Search investigations"
                      placeholder="Search case, test, or source record…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                  <select
                    aria-label="Filter exception type"
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    <option value="">All exception types</option>
                    <option>OOS</option>
                    <option>OOT</option>
                  </select>
                  <select
                    aria-label="Filter investigation status"
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                  >
                    <option value="">All statuses</option>
                    {[
                      "DETECTED",
                      "TRIAGED",
                      "PHASE_I_OPEN",
                      "PHASE_I_REVIEW",
                      "PHASE_II_OPEN",
                      "PHASE_II_REVIEW",
                      "OOT_REVIEW",
                      "OOT_ESCALATED",
                      "QA_EVALUATION",
                      "REPORT_DRAFT",
                      "QA_REVIEW_PENDING",
                      "APPROVED",
                      "CLOSED",
                    ].map((s) => (
                      <option key={s} value={s}>
                        {pretty(s)}
                      </option>
                    ))}
                  </select>
                </div>
                <ErrorBox error={events.error} />
                {events.loading ? (
                  <div className="loading">Loading investigations…</div>
                ) : (
                  <>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Investigation</th>
                            <th>Type</th>
                            <th>Test characteristic</th>
                            <th>Site</th>
                            <th>Result</th>
                            <th>Status</th>
                            <th>
                              <span className="sr-only">Open</span>
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {events.data?.items.map((e: Data) => (
                            <tr key={e.id}>
                              <td>
                                <button
                                  className="case-link"
                                  onClick={() => setSelected(e.id)}
                                >
                                  {e.event_number}
                                </button>
                                <small>Spec {e.specification_version}</small>
                              </td>
                              <td>
                                <Badge value={e.kind} />
                              </td>
                              <td>{e.test_name}</td>
                              <td>
                                {sites.data?.find(
                                  (s: Data) => s.id === e.site_id,
                                )?.code || e.site_id}
                              </td>
                              <td className="numeric">
                                {Number(e.result_value).toFixed(2)}{" "}
                                <span className="muted">{e.unit}</span>
                              </td>
                              <td>
                                <Badge value={e.status} />
                              </td>
                              <td>
                                <button
                                  className="icon-btn"
                                  aria-label={"Open " + e.event_number}
                                  onClick={() => setSelected(e.id)}
                                >
                                  <ArrowUpRight size={16} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {!events.data?.items.length && <Empty />}
                    <div className="pagination">
                      <span>
                        {events.data?.total
                          ? `${offset + 1}–${Math.min(offset + 10, events.data.total)} of ${fmt(events.data.total)} investigations`
                          : "0 investigations"}
                      </span>
                      <div>
                        <button
                          className="icon-btn"
                          aria-label="Previous page"
                          disabled={offset === 0}
                          onClick={() => setOffset((o) => Math.max(0, o - 10))}
                        >
                          <ChevronLeft size={17} />
                        </button>
                        <button
                          className="icon-btn"
                          aria-label="Next page"
                          disabled={offset + 10 >= (events.data?.total || 0)}
                          onClick={() => setOffset((o) => o + 10)}
                        >
                          <ChevronRight size={17} />
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </section>
            )}
            {page === "sites" && (
              <section className="site-grid">
                {sites.data?.map((s: Data) => (
                  <article className="panel site-card" key={s.id}>
                    <div className="site-card-top">
                      <span className="site-icon">
                        <Globe2 size={23} />
                      </span>
                      <span className="muted small-text">{s.code}</span>
                    </div>
                    <h2>{s.name}</h2>
                    <p>{s.region}</p>
                    <div className="site-numbers">
                      <div>
                        <strong>{fmt(s.results)}</strong>
                        <small>Results</small>
                      </div>
                      <div>
                        <strong>{fmt(s.open_events)}</strong>
                        <small>Open cases</small>
                      </div>
                      <div>
                        <strong>{fmt(s.oos + s.oot)}</strong>
                        <small>Exceptions</small>
                      </div>
                    </div>
                    <button
                      className="text-btn"
                      onClick={() => {
                        setSite(String(s.id));
                        setPage("events");
                      }}
                    >
                      Open site worklist
                      <ArrowRight size={15} />
                    </button>
                  </article>
                ))}
              </section>
            )}
            {page === "intake" && (
              <ResultIntake
                token={token}
                open={setSelected}
                onChange={refresh}
              />
            )}
            {page === "capas" && (
              <CapaTable
                token={token}
                site={site}
                revision={revision}
                open={setSelected}
              />
            )}
            {page === "documents" && <Documents token={token} />}
            {page === "sources" && <Sources token={token} />}
            {page === "model" && <ModelPage token={token} />}
          </motion.div>
          <footer className="main-footer">
            <span>
              QualisIQ <span className="footer-sep">/</span> QC WORKSPACE
            </span>
            <span>DEMO WORKSPACE · HUMAN REVIEW REQUIRED</span>
          </footer>
        </main>
      </div>
      <AnimatePresence initial={false}>
        {selected !== null && (
          <Investigation
            key={selected}
            token={token}
            id={selected}
            user={user}
            close={() => setSelected(null)}
            onChange={refresh}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
function Kpi({
  title,
  value,
  icon: Icon,
  tone = "green",
}: {
  title: string;
  value?: number;
  icon: LucideIcon;
  tone?: string;
}) {
  return (
    <article className="panel kpi">
      <div className="kpi-top">
        <span>{title}</span>
        <span className={`kpi-icon ${tone}`}>
          <Icon size={18} />
        </span>
      </div>
      <strong>{value === undefined ? "—" : fmt(value)}</strong>
    </article>
  );
}
function TrendChart({ data }: { data: Data[] }) {
  if (!data.length) return <Empty text="No measurement history available." />;
  const w = 760,
    h = 195,
    p = 35,
    max = Math.max(2, ...data.map((d) => Math.max(d.OOS, d.OOT)));
  const coords = (key: string) =>
    data
      .map(
        (d, i) =>
          `${p + (i * (w - 2 * p)) / Math.max(1, data.length - 1)},${h - p - (d[key] * (h - 2 * p)) / max}`,
      )
      .join(" ");
  return (
    <div className="trend-chart">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label="Out-of-specification and out-of-trend exception counts by date"
      >
        {[0, 0.5, 1].map((n) => (
          <g key={n}>
            <line
              x1={p}
              y1={h - p - n * (h - 2 * p)}
              x2={w - p}
              y2={h - p - n * (h - 2 * p)}
              stroke="#e9eeeb"
              strokeDasharray="4 5"
            />
            <text
              x={p - 10}
              y={h - p - n * (h - 2 * p) + 4}
              textAnchor="end"
              fontSize="10"
              fill="#84908c"
            >
              {Math.round(max * n)}
            </text>
          </g>
        ))}
        <polygon
          points={`${p},${h - p} ${coords("OOS")} ${w - p},${h - p}`}
          fill="#d4e4fb"
          opacity=".45"
        />
        <polyline
          points={coords("OOS")}
          fill="none"
          stroke="#2476e5"
          strokeWidth="2.4"
        />
        <polyline
          points={coords("OOT")}
          fill="none"
          stroke="#d1a051"
          strokeWidth="2"
        />
        {[0, Math.floor((data.length - 1) / 2), data.length - 1].map((i, j) => (
          <text
            key={j}
            x={p + (i * (w - 2 * p)) / Math.max(1, data.length - 1)}
            y={h - 8}
            textAnchor="middle"
            fontSize="10"
            fill="#84908c"
          >
            {data[i].date}
          </text>
        ))}
      </svg>
      <details>
        <summary>View chart data</summary>
        <div className="chart-data">
          {data.map((d) => (
            <span key={d.date}>
              {d.date}: {d.OOS} OOS · {d.OOT} OOT · {d.total} total
            </span>
          ))}
        </div>
      </details>
    </div>
  );
}
function Disposition({ outcomes }: { outcomes: Data }) {
  const total = Object.values(outcomes).reduce((a: number, b: any) => a + b, 0);
  const normal = outcomes.IN_SPEC || 0;
  const rate = total ? (normal / total) * 100 : 0;
  const other = outcomes.OOT_NOT_ASSESSED || 0;
  const ootEnd = total ? ((normal + (outcomes.OOT || 0)) / total) * 100 : 0;
  const oosEnd = total
    ? ((normal + (outcomes.OOT || 0) + (outcomes.OOS || 0)) / total) * 100
    : 0;
  return (
    <div className="disposition">
      <div
        className="donut"
        style={{
          background: `conic-gradient(#2e79df 0 ${rate}%, #d9a34e ${rate}% ${ootEnd}%, #ce7263 ${ootEnd}% ${oosEnd}%, #a6b0a1 0 100%)`,
        }}
      >
        <div>
          <strong>
            {rate.toFixed(1)}
            <span>%</span>
          </strong>
          <small>No rule exception</small>
        </div>
      </div>
      <div className="disposition-legend">
        {[
          ["IN_SPEC", "No rule exception", "green"],
          ["OOS", "Out of specification", "red"],
          ["OOT", "Out of trend", "amber"],
          ...(other
            ? [["OOT_NOT_ASSESSED", "OOT not assessed", "neutral"]]
            : []),
        ].map(([key, label, color]) => (
          <div key={key}>
            <span>
              <i className={"mini-dot " + color} />
              {label}
            </span>
            <strong>{fmt(outcomes[key])}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
function CapaTable({
  token,
  site,
  revision,
  open,
}: {
  token: string;
  site: string;
  revision: number;
  open: (n: number) => void;
}) {
  const [offset, setOffset] = useState(0);
  useEffect(() => setOffset(0), [site]);
  const { data, error, loading } = useData(
    `/workbench/capas?offset=${offset}&limit=50${site ? "&site_id=" + site : ""}`,
    token,
    revision,
  );
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>
            Corrective & preventive actions{" "}
            <span className="count">{fmt(data?.total)}</span>
          </h2>
        </div>
      </div>
      <ErrorBox error={error} />
      {loading ? (
        <div className="loading">Loading CAPA worklist…</div>
      ) : (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Investigation</th>
                  <th>Due date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((c: Data) => (
                  <tr key={c.id}>
                    <td>
                      <strong>CAPA-{c.id}</strong>
                      <small>{c.title}</small>
                    </td>
                    <td>
                      <button
                        className="case-link"
                        onClick={() => open(c.event_id)}
                      >
                        {c.event_number}
                      </button>
                    </td>
                    <td>{c.due_at.slice(0, 10)}</td>
                    <td>
                      <Badge value={c.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data?.items.length && <Empty />}
          <div className="pagination">
            <span>{fmt(data?.total)} actions</span>
            <div>
              <button
                className="icon-btn"
                aria-label="Previous CAPA page"
                disabled={!offset}
                onClick={() => setOffset((x) => Math.max(0, x - 50))}
              >
                <ChevronLeft size={17} />
              </button>
              <button
                className="icon-btn"
                aria-label="Next CAPA page"
                disabled={offset + 50 >= (data?.total || 0)}
                onClick={() => setOffset((x) => x + 50)}
              >
                <ChevronRight size={17} />
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
function Documents({ token }: { token: string }) {
  const { data, error, loading } = useData("/workbench/documents", token);
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Controlled document register</h2>
        </div>
        <FileCheck2 size={22} />
      </div>
      <ErrorBox error={error} />
      {loading ? (
        <div className="loading">Loading documents…</div>
      ) : (
        data?.map((d: Data) => (
          <article className="document-row" key={d.code}>
            <FileText size={24} />
            <div>
              <strong>{d.title}</strong>
              <p>
                {d.code} · {d.version} · {d.status}
              </p>
              <code>SHA-256 {d.sha256}</code>
            </div>
            <span className="pill">Synthetic metadata</span>
          </article>
        ))
      )}
      {data?.length === 0 && <Empty />}
    </section>
  );
}
function Sources({ token }: { token: string }) {
  const { data, error, loading } = useData("/knowledge/sources", token);
  return (
    <>
      <section className="insight-strip">
        <Database size={28} />
        <div>
          <h3>Reference metadata</h3>
          <p>
            Operational records are synthetic. Public links inform the design;
            they are not private manufacturer data or model-training evidence.
          </p>
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Public source register</h2>
          </div>
        </div>
        <ErrorBox error={error} />
        {loading ? (
          <div className="loading">Loading source register…</div>
        ) : (
          data?.map((s: Data) => (
            <article className="source-row" key={s.reference_code}>
              <span className="source-icon">
                <Network size={21} />
              </span>
              <div>
                <span className="eyebrow dark">{s.publisher}</span>
                <h3>{s.title}</h3>
                <p>{s.scope}</p>
                <span className="muted small-text">
                  {s.imported_content
                    ? "Content imported"
                    : "Reference metadata only"}
                </span>
              </div>
              {/^https:\/\//.test(s.url) && (
                <a
                  className="button"
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View source
                  <ArrowUpRight size={15} />
                </a>
              )}
            </article>
          ))
        )}
      </section>
    </>
  );
}
function ModelPage({ token }: { token: string }) {
  const { data: d, error, loading } = useData("/ml/report", token);
  if (loading)
    return <div className="loading panel">Loading model evaluation…</div>;
  if (error) return <ErrorBox error={error} />;
  if (!d) return null;
  return (
    <>
      <section className="model-hero">
        <div>
          <span className="pill">RESEARCH MODEL · SYNTHETIC EVALUATION</span>
          <h2>Model evaluation</h2>
          <span className="small-text">
            {d.version} · {d.algorithm}
          </span>
        </div>
        <div className="model-orbit">
          <Sparkles size={50} />
        </div>
      </section>
      <div className="kpi-grid">
        <Kpi title="Held-out results" value={d.metrics.rows} icon={Database} />
        <Metric title="Sensitivity / recall" value={pct(d.metrics.recall)} />
        <Metric
          title="False-positive rate"
          value={pct(d.metrics.false_positive_rate)}
        />
        <Metric
          title="Average precision"
          value={d.metrics.average_precision?.toFixed(3) || "—"}
        />
      </div>
      <div className="chart-grid model-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Model vs. statistical baseline</h2>
            </div>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Isolation Forest</th>
                  <th>Robust |Z| baseline</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Recall", "recall"],
                  ["Precision", "precision"],
                  ["False-positive rate", "false_positive_rate"],
                  ["ROC AUC", "roc_auc"],
                  ["Average precision", "average_precision"],
                ].map(([name, k]) => (
                  <tr key={k}>
                    <td>{name}</td>
                    <td>
                      {d.metrics[k] === null
                        ? "Not assessed"
                        : Number(d.metrics[k]).toFixed(4)}
                    </td>
                    <td>
                      {d.baseline[k] === null
                        ? "Not assessed"
                        : Number(d.baseline[k]).toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="callout">
            <AlertTriangle size={18} />
            <p>
              The model has not demonstrated an advantage over the baseline.
              This benchmark does not establish real-world suitability.
            </p>
          </div>
        </section>
        <section className="panel validation">
          <h2>Validation boundaries</h2>
          <dl className="model-parameters">
            <div>
              <dt>Proxy positives</dt>
              <dd>{fmt(d.metrics.positives)}</dd>
            </div>
            <div>
              <dt>Alert budget</dt>
              <dd>1%</dd>
            </div>
            <div>
              <dt>Evaluation data</dt>
              <dd>Synthetic</dd>
            </div>
          </dl>
          <div className="validation-row">
            <CheckCircle2 size={17} />
            <span>Batch-disjoint train / calibration / test</span>
          </div>
          <div className="split-bars">
            {Object.entries(d.split_rows).map(([k, v]) => (
              <div key={k}>
                <span>{pretty(k)}</span>
                <strong>{fmt(v as number)}</strong>
              </div>
            ))}
          </div>
          <p>{d.normalization}</p>
          <p>{d.evaluation_label}</p>
          <span className="pill">NOT APPROVED FOR PRODUCTION</span>
        </section>
      </div>
      <section className="panel limitations">
        <h2>What the evidence does—and does not—support</h2>
        <ul>
          {d.limitations.map((s: string) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <h3>Dataset fingerprint</h3>
        <code>{d.dataset_sha256}</code>
        <h3>Artifact fingerprint</h3>
        <code>{d.artifact_sha256}</code>
      </section>
    </>
  );
}
function Metric({ title, value }: { title: string; value: string }) {
  return (
    <article className="panel kpi">
      <div className="kpi-top">
        <span>{title}</span>
        <Activity size={18} />
      </div>
      <strong>{value}</strong>
    </article>
  );
}
function Investigation({
  id,
  token,
  user,
  close,
  onChange,
}: {
  id: number;
  token: string;
  user: User;
  close: () => void;
  onChange: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const reduced = useReducedMotion();
  const dragControls = useDragControls();
  const sheetX = useMotionValue(0);
  const isPresent = useIsPresent();
  const dismissX = isPresent ? 72 : Math.max(72, sheetX.get() + 72);
  const [revision, setRevision] = useState(0);
  const [historyLimit, setHistoryLimit] = useState(40);
  const analysis = useData(
    `/workbench/events/${id}/analysis?limit=${historyLimit}`,
    token,
    revision,
  );
  const event = useData(`/quality/events/${id}`, token, revision);
  const lineage = useData(`/workbench/events/${id}/lineage`, token, revision);
  const brief = useData(`/quality/events/${id}/ai-brief`, token, revision);
  const score = useData(`/ml/events/${id}/score`, token, revision);
  const [tab, setTab] = useState("overview");
  const [form, setForm] = useState<Data>({});
  const [reason, setReason] = useState("");
  const [target, setTarget] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState("");
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  useEffect(() => {
    if (event.data) setForm(event.data.investigation || {});
  }, [event.data]);
  async function mutate(type: string) {
    setSaving(true);
    setError("");
    setSaved("");
    try {
      await request(`/quality/events/${id}/${type}`, token, {
        method: type === "investigation" ? "PATCH" : "POST",
        body: JSON.stringify(
          type === "investigation"
            ? {
                summary: form.summary || "",
                impact_assessment: form.impact_assessment || "",
                root_cause_hypothesis: form.root_cause_hypothesis || "",
                capa_rationale: form.capa_rationale || "",
                expected_version: event.data.version,
              }
            : {
                target_status: target,
                reason,
                expected_version: event.data.version,
              },
        ),
      });
      setRevision((r) => r + 1);
      onChange();
      setSaved(
        type === "investigation"
          ? "Investigation draft saved."
          : "Workflow transition recorded.",
      );
      setTarget("");
      setReason("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  const e = event.data;
  const canEdit =
    ["qc_analyst", "qc_manager", "admin"].includes(user.role) &&
    !["APPROVED", "CLOSED"].includes(e?.status);
  return (
    <motion.dialog
      ref={dialog}
      aria-label="Quality investigation"
      style={{ x: sheetX }}
      initial={{ x: reduced ? 0 : 72, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: reduced ? 0 : dismissX, opacity: 0 }}
      transition={{
        type: "spring",
        stiffness: 450,
        damping: 40,
        mass: 0.8,
        opacity: { duration: 0.16 },
      }}
      drag={reduced ? false : "x"}
      dragListener={false}
      dragControls={dragControls}
      dragConstraints={{
        left: 0,
        right: typeof window !== "undefined" ? window.innerWidth : 700,
      }}
      dragElastic={0}
      dragMomentum={false}
      onDragEnd={(_, info) => {
        const projected =
          sheetX.get() + ((info.velocity.x / 1000) * 0.995) / (1 - 0.995);
        if (
          projected > Math.min(220, window.innerWidth * 0.35) &&
          info.velocity.x > -200
        )
          close();
        else
          animate(sheetX, 0, {
            type: "spring",
            stiffness: 450,
            damping: 40,
            mass: 0.8,
            velocity: info.velocity.x,
          });
      }}
      className="investigation-dialog"
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(ev) => {
        if (ev.target === dialog.current) close();
      }}
    >
      <div
        className="sheet-grab"
        aria-hidden="true"
        onPointerDown={(event) => dragControls.start(event)}
      >
        <span />
      </div>
      <div className="drawer-head">
        <span className="eyebrow dark">INVESTIGATION OBJECT PAGE</span>
        <button
          className="icon-btn"
          aria-label="Close investigation"
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      <ErrorBox error={event.error} />
      {event.loading ? (
        <div className="loading">Loading investigation…</div>
      ) : (
        e && (
          <>
            <div className="drawer-title">
              <h2>{e.event_number}</h2>
              <div>
                <Badge value={e.kind} />
                <Badge value={e.status} />
                <span className="muted small-text">
                  Version {e.version} · Synthetic
                </span>
              </div>
              <p>
                {e.test_name} · {Number(e.result_value).toFixed(3)} {e.unit}
              </p>
            </div>
            <div className="drawer-tabs">
              {[
                "overview",
                "analysis",
                "investigation",
                "lineage",
                "intelligence",
              ].map((t) => (
                <button
                  key={t}
                  aria-pressed={tab === t}
                  className={tab === t ? "selected" : ""}
                  onClick={() => setTab(t)}
                >
                  {tab === t && (
                    <motion.span
                      className="tab-selection"
                      layoutId={`investigation-tab-${id}`}
                      transition={{
                        type: "spring",
                        stiffness: 450,
                        damping: 40,
                        mass: 0.8,
                      }}
                    />
                  )}
                  <span>{pretty(t)}</span>
                </button>
              ))}
            </div>
            <div className="drawer-content">
              <ErrorBox error={error} />
              {saved && (
                <div className="success" role="status">
                  <Check size={17} />
                  {saved}
                </div>
              )}
              {tab === "analysis" && (
                <InvestigationAnalysis
                  data={analysis.data}
                  error={analysis.error}
                  loading={analysis.loading}
                  limit={historyLimit}
                  onLimitChange={setHistoryLimit}
                />
              )}
              {tab === "overview" && (
                <>
                  <button
                    className="button analysis-shortcut"
                    onClick={() => setTab("analysis")}
                  >
                    <Activity size={16} />
                    View OOS / OOT graphs
                    <ArrowUpRight size={15} />
                  </button>
                  <div className="case-context">
                    <div>
                      <span>Observed result</span>
                      <strong>
                        {Number(e.result_value).toFixed(3)} {e.unit}
                      </strong>
                    </div>
                    <div>
                      <span>Approved demo limits</span>
                      <strong>
                        {e.approved_limits.min ?? "—"} –{" "}
                        {e.approved_limits.max ?? "—"}
                      </strong>
                    </div>
                  </div>
                  <h3>Why this case was raised</h3>
                  <p>{e.alert_reason}</p>
                  <h3>Investigation summary</h3>
                  <p>
                    {e.investigation?.summary ||
                      "No investigation summary recorded yet."}
                  </p>
                  <div className="case-context">
                    <div>
                      <span>Evidence metadata records</span>
                      <strong>{e.evidence_count}</strong>
                    </div>
                    <div>
                      <span>Linked CAPA actions</span>
                      <strong>{e.capa_count}</strong>
                    </div>
                  </div>
                  <div className="callout">
                    <ShieldCheck size={20} />
                    <p>
                      Workflow approval is a simulated quality state. It is not
                      an electronic signature or batch-release authorization.
                    </p>
                  </div>
                </>
              )}
              {tab === "investigation" && (
                <>
                  <h3>Investigation draft</h3>
                  <form
                    onSubmit={(ev) => {
                      ev.preventDefault();
                      mutate("investigation");
                    }}
                  >
                    {[
                      ["summary", "Summary", 12],
                      [
                        "root_cause_hypothesis",
                        "Root-cause hypothesis (unverified)",
                        0,
                      ],
                      ["impact_assessment", "Impact assessment", 12],
                      ["capa_rationale", "CAPA rationale", 12],
                    ].map(([key, label, min]) => (
                      <label key={String(key)}>
                        {label}
                        <textarea
                          rows={3}
                          value={form[String(key)] || ""}
                          disabled={!canEdit || saving}
                          minLength={Number(min)}
                          maxLength={key === "capa_rationale" ? 5000 : 10000}
                          required={Number(min) > 0}
                          onChange={(ev) =>
                            setForm({ ...form, [key]: ev.target.value })
                          }
                        />
                      </label>
                    ))}
                    {canEdit ? (
                      <button className="primary" disabled={saving}>
                        {saving ? "Saving…" : "Save investigation draft"}
                      </button>
                    ) : (
                      <p className="muted">
                        Your role or this case’s terminal status permits
                        read-only access.
                      </p>
                    )}
                  </form>
                  <Workflow
                    token={token}
                    id={id}
                    revision={revision}
                    target={target}
                    setTarget={setTarget}
                    reason={reason}
                    setReason={setReason}
                    saving={saving}
                    submit={() => mutate("transition")}
                  />
                </>
              )}
              {tab === "lineage" && (
                <>
                  <ErrorBox error={lineage.error} />
                  {lineage.data && (
                    <>
                      <div className="lineage-list">
                        {[
                          ["Source system", lineage.data.source.system],
                          ["Source record", lineage.data.source.record_id],
                          ["Material", lineage.data.material.description],
                          ["Batch", lineage.data.batch],
                          ["Inspection lot", lineage.data.inspection_lot],
                          ["Sample", lineage.data.sample],
                          ["Specification", lineage.data.specification.version],
                        ].map(([k, v]) => (
                          <div key={k}>
                            <span className="lineage-node">
                              <Database size={16} />
                            </span>
                            <div>
                              <small>{k}</small>
                              <strong>{v}</strong>
                            </div>
                          </div>
                        ))}
                      </div>
                      <h3>Source fingerprint</h3>
                      <code>{lineage.data.source.sha256}</code>
                      <h3>Evidence metadata</h3>
                      {lineage.data.evidence.length ? (
                        lineage.data.evidence.map((v: Data) => (
                          <div className="evidence" key={v.id}>
                            <strong>{v.label}</strong>
                            <p>
                              {v.kind} · {v.reference_uri}
                            </p>
                            <code>{v.sha256}</code>
                          </div>
                        ))
                      ) : (
                        <Empty text="No evidence metadata has been attached." />
                      )}
                    </>
                  )}
                </>
              )}
              {tab === "intelligence" && (
                <>
                  <span className="pill">ADVISORY · HUMAN REVIEW REQUIRED</span>
                  <h3>Source-linked investigation checklist</h3>
                  <ErrorBox error={brief.error} />
                  {brief.data && (
                    <>
                      <p>{brief.data.summary}</p>
                      <ul className="checklist">
                        {brief.data.hypotheses_not_conclusions.map(
                          (c: string) => (
                            <li key={c}>
                              <ClipboardCheck size={17} />
                              {c}
                            </li>
                          ),
                        )}
                      </ul>
                      <div className="reference-chips">
                        {brief.data.source_references.map((r: string) => (
                          <span key={r}>{r}</span>
                        ))}
                      </div>
                      <div className="callout">
                        <AlertTriangle size={18} />
                        <p>{brief.data.disclaimer}</p>
                      </div>
                    </>
                  )}
                  <h3>Experimental anomaly score</h3>
                  <ErrorBox error={score.error} />
                  {score.data &&
                    (score.data.status === "NOT_ASSESSED" ? (
                      <p>{score.data.reason}</p>
                    ) : (
                      <>
                        <div className="case-context">
                          <div>
                            <span>Score (not a probability)</span>
                            <strong>
                              {score.data.anomaly_score.toFixed(4)}
                            </strong>
                          </div>
                          <div>
                            <span>Calibration threshold</span>
                            <strong>{score.data.threshold.toFixed(4)}</strong>
                          </div>
                        </div>
                        <p>
                          {score.data.flagged_for_review
                            ? "Above the experimental review threshold."
                            : "Below the experimental review threshold. Approved specification exceptions still require investigation."}
                        </p>
                        <p className="muted">{score.data.warning}</p>
                      </>
                    ))}
                </>
              )}
            </div>
          </>
        )
      )}
    </motion.dialog>
  );
}
function Workflow({
  token,
  id,
  revision,
  target,
  setTarget,
  reason,
  setReason,
  saving,
  submit,
}: {
  token: string;
  id: number;
  revision: number;
  target: string;
  setTarget: (v: string) => void;
  reason: string;
  setReason: (v: string) => void;
  saving: boolean;
  submit: () => void;
}) {
  const { data, error } = useData(
    `/workbench/events/${id}/transitions`,
    token,
    revision,
  );
  return (
    <div className="workflow">
      <h3>Controlled workflow</h3>
      <ErrorBox error={error} />
      {data?.allowed.length ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <label>
            Next workflow state
            <select
              required
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="">Select a permitted transition</option>
              {data.allowed.map((t: string) => (
                <option key={t} value={t}>
                  {pretty(t)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Reason
            <textarea
              required
              minLength={12}
              maxLength={2000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
            />
          </label>
          <button className="primary" disabled={saving}>
            {saving ? "Recording…" : "Record workflow transition"}
            <ArrowRight size={16} />
          </button>
        </form>
      ) : (
        <p>
          No transitions are available for your role at this workflow state.
          Independent QA and evidence gates apply.
        </p>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user">
      <App />
    </MotionConfig>
  </React.StrictMode>,
);

function ResultIntake({
  token,
  open,
  onChange,
}: {
  token: string;
  open: (v: number) => void;
  onChange: () => void;
}) {
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState("");
  const [lot, setLot] = useState<Data | null>(null);
  const [test, setTest] = useState("Assay");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("%");
  const [source, setSource] = useState("SYNTHETIC_LIMS");
  const [record, setRecord] = useState("");
  const [key, setKey] = useState<string>(() => crypto.randomUUID());
  const [time, setTime] = useState(() => new Date().toISOString().slice(0, 16));
  const [result, setResult] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const lots = useData(
    "/workbench/inspection-lots?q=" + encodeURIComponent(q),
    token,
  );
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!lot) return;
    setError("");
    setResult(null);
    setBusy(true);
    try {
      const response = await request("/lab/results", token, {
        method: "POST",
        body: JSON.stringify({
          site_code: lot.site_code,
          material_code: lot.material_code,
          batch_number: lot.batch_number,
          inspection_lot: lot.inspection_lot,
          sample_number: lot.sample_number,
          test_name: test,
          value,
          unit,
          measured_at: time + ":00Z",
          source_system: source,
          source_record_id: record,
          idempotency_key: key,
        }),
      });
      setResult(response);
      onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel intake">
      <div className="panel-heading">
        <div>
          <h2>Record a laboratory result</h2>
        </div>
        <Beaker size={21} />
      </div>
      <div className="intake-inner">
        <ErrorBox error={lots.error || error} />
        <form onSubmit={submit}>
          <label>
            Find an inspection lot or batch
            <input
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setSelected("");
                setLot(null);
              }}
              placeholder="Search by lot or batch number"
            />
          </label>
          <label>
            Authorized inspection lot
            <select
              required
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setLot(
                  lots.data?.find(
                    (l: Data) => String(l.id) === e.target.value,
                  ) || null,
                );
                setResult(null);
              }}
            >
              <option value="">
                Select a lot ({lots.data?.length || 0} matching, up to 30)
              </option>
              {lots.data?.map((l: Data) => (
                <option key={l.id} value={l.id}>
                  {l.inspection_lot} · {l.site_code} · {l.material}
                </option>
              ))}
            </select>
          </label>
          {lot && (
            <div className="callout">
              <Database size={18} />
              <p>
                {lot.material}
                <br />
                {lot.batch_number} → {lot.inspection_lot} → {lot.sample_number}
              </p>
            </div>
          )}
          <div className="intake-grid">
            <label>
              Test characteristic
              <select value={test} onChange={(e) => setTest(e.target.value)}>
                <option>Assay</option>
                <option>Related Impurity A</option>
                <option>Dissolution</option>
              </select>
            </label>
            <label>
              Measured value
              <input
                type="number"
                step="any"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                required
              />
            </label>
            <label>
              Unit
              <input
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                required
              />
            </label>
            <label>
              Measured at (UTC)
              <input
                type="datetime-local"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                required
              />
            </label>
            <label>
              Source system
              <input
                minLength={2}
                maxLength={60}
                value={source}
                onChange={(e) => setSource(e.target.value)}
                required
              />
            </label>
            <label>
              Source record ID
              <input
                minLength={2}
                maxLength={140}
                value={record}
                onChange={(e) => setRecord(e.target.value)}
                required
                placeholder="Unique laboratory record ID"
              />
            </label>
          </div>
          <label>
            Idempotency key
            <input
              minLength={4}
              maxLength={160}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              required
            />
          </label>
          <p className="intake-note">
            A repeated key and identical payload replay the original result.
            Changed payloads or source identities are rejected. New records
            require a new key.
          </p>
          <button className="primary" disabled={!lot || busy}>
            {busy ? "Validating & recording…" : "Validate and record result"}
            <ArrowRight size={16} />
          </button>
        </form>
        {result && (
          <div className="ingest-result" role="status">
            <CheckCircle2 size={22} />
            <div>
              <h3>
                {result.replayed
                  ? "Original result replayed"
                  : "Laboratory result recorded"}
              </h3>
              <p>
                Result #{result.result_id} · Outcome: {result.outcome}
              </p>
              {result.event_id && (
                <button
                  className="text-btn"
                  onClick={() => open(result.event_id)}
                >
                  Open generated investigation
                  <ArrowRight size={15} />
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
