import React, { useState, useEffect, useCallback } from "react";
import {
  LayoutDashboard, ListChecks, TrendingUp, Copy, Database, Map as MapIcon,
  Bell, ArrowLeft, MapPin, FileSearch, ClipboardCheck, AlertTriangle, Clock,
  Building2, ShieldCheck, Upload, CheckCircle2, Info, Landmark, PlugZap, WifiOff,
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

/* ================= API ================= */
const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const api = {
  get: (p) => fetch(API + p).then((r) => r.json()),
  post: (p, body) => fetch(API + p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json()),
  upload: (p, file, fields) => { const fd = new FormData(); fd.append("file", file); Object.entries(fields || {}).forEach(([k, v]) => fd.append(k, v)); return fetch(API + p, { method: "POST", body: fd }).then((r) => r.json()); },
};

const NAVY = "#0b2b52", NAVY2 = "#0a2344", SAFFRON = "#ff8c1a", GREEN = "#138808";
const inr = (n) => "\u20B9" + Number(n).toLocaleString("en-IN");
const lakh = (n) => "\u20B9" + (Number(n) / 100000).toFixed(1) + "L";
const KIND = {
  cost: { c: "#e11d48", bg: "bg-rose-50", tx: "text-rose-700", rg: "ring-rose-200", Icon: AlertTriangle, name: "Cost anomaly" },
  duplicate: { c: "#d97706", bg: "bg-amber-50", tx: "text-amber-700", rg: "ring-amber-200", Icon: Copy, name: "Duplicate" },
  delivery_risk: { c: "#2563eb", bg: "bg-blue-50", tx: "text-blue-700", rg: "ring-blue-200", Icon: Clock, name: "Delivery risk" },
  concentration: { c: "#7c3aed", bg: "bg-violet-50", tx: "text-violet-700", rg: "ring-violet-200", Icon: Building2, name: "Concentration" },
};

function Logo({ size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-label="Drishti">
      <path d="M6 50 Q50 12 94 50" fill="none" stroke={SAFFRON} strokeWidth="9" strokeLinecap="round" />
      <path d="M6 50 Q50 88 94 50" fill="none" stroke={GREEN} strokeWidth="9" strokeLinecap="round" />
      <circle cx="50" cy="50" r="15" fill="#fff" stroke={NAVY} strokeWidth="3" /><circle cx="50" cy="50" r="6" fill={NAVY} />
    </svg>
  );
}
const NAV = [["dashboard", "Dashboard", LayoutDashboard], ["queue", "Review Queue", ListChecks],
  ["risk", "Delivery Risk", TrendingUp], ["dupes", "Duplicate Detection", Copy],
  ["geo", "Geographic View", MapIcon], ["data", "Data Sources", Database]];

export default function Drishti() {
  const [view, setView] = useState("dashboard");
  const [mode, setMode] = useState({ mode: "real", connected: false });
  const [sel, setSel] = useState(null);
  const [role, setRole] = useState("District Authority");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const refreshMode = useCallback(() => {
    setLoading(true); setErr(null);
    api.get("/mode").then((m) => { setMode(m); setLoading(false); })
      .catch(() => { setErr("Cannot reach the Drishti API at " + API); setLoading(false); });
  }, []);
  useEffect(refreshMode, [refreshMode]);

  const openCase = (c) => { setSel(c); setView("dossier"); };

  return (
    <div className="min-h-screen w-full flex bg-slate-100" style={{ fontFamily: "system-ui, sans-serif" }}>
      <aside className="w-60 shrink-0 flex flex-col text-slate-200" style={{ background: NAVY2 }}>
        <div className="px-4 py-4 flex items-center gap-2 border-b border-white/10">
          <Landmark className="h-6 w-6 text-slate-300" />
          <div className="leading-tight"><div className="text-[11px] font-semibold">GOVERNMENT OF INDIA</div><div className="text-[9px] text-slate-400">MoSPI &middot; MPLADS</div></div>
        </div>
        <nav className="flex-1 py-3">
          {NAV.map(([k, label, Icon]) => {
            const active = view === k || (k === "queue" && view === "dossier");
            return <button key={k} onClick={() => setView(k)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm ${active ? "text-white" : "text-slate-300 hover:bg-white/5"}`}
              style={active ? { background: "rgba(255,255,255,0.10)", borderLeft: `3px solid ${SAFFRON}` } : { borderLeft: "3px solid transparent" }}>
              <Icon style={{ width: 18, height: 18 }} /> {label}</button>;
          })}
        </nav>
        <div className="px-4 py-4 border-t border-white/10"><div className="flex items-center gap-2"><Logo size={26} /><span className="font-semibold text-white">Drishti</span></div><div className="text-[10px] text-slate-400 mt-1">Insight for Integrity</div></div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-4">
          <Logo /><div className="leading-tight"><div className="text-xl font-bold" style={{ color: NAVY }}>Drishti</div><div className="text-[11px] text-slate-500">AI-Powered MPLADS Oversight &amp; Early-Warning System</div></div>
          <div className="ml-auto flex items-center gap-3">
            <ModeBadge mode={mode} />
            <select value={role} onChange={(e) => setRole(e.target.value)} className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-slate-700">
              {["District Authority", "State Nodal Authority", "Ministry (MoSPI)", "MP / Constituency"].map((r) => <option key={r}>{r}</option>)}
            </select>
            <Bell className="h-5 w-5 text-slate-500" />
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">
          {loading ? <Loading /> : err ? <ErrorState msg={err} onRetry={refreshMode} /> :
            !mode.connected && view !== "data" ? <NotConnected onConnect={() => setView("data")} mode={mode} /> :
              view === "dashboard" ? <Dashboard role={role} setView={setView} /> :
                view === "queue" ? <Queue openCase={openCase} /> :
                  view === "risk" ? <RiskView openCase={openCase} /> :
                    view === "dupes" ? <DupesView /> :
                      view === "geo" ? <GeoView /> :
                        view === "data" ? <DataView mode={mode} onImported={refreshMode} /> :
                          view === "dossier" && sel ? <Dossier c={sel} role={role} back={() => setView("queue")} /> : null}
        </main>
        <footer className="bg-white border-t border-slate-200 px-6 py-3 text-center text-[11px] text-slate-400">
          &copy; 2026 Drishti &mdash; Ministry of Statistics &amp; Programme Implementation (MoSPI)
        </footer>
      </div>
    </div>
  );
}

function ModeBadge({ mode }) {
  if (mode.mode === "demo") return <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-800 ring-1 ring-amber-300 px-2.5 py-1 text-[11px] font-bold uppercase"><span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Demo data</span>;
  return mode.connected
    ? <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 px-2.5 py-1 text-[11px] font-semibold"><PlugZap className="h-3.5 w-3.5" /> Real data connected</span>
    : <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 text-slate-600 ring-1 ring-slate-300 px-2.5 py-1 text-[11px] font-semibold"><WifiOff className="h-3.5 w-3.5" /> No real data</span>;
}
const Loading = () => <div className="flex items-center justify-center h-64 text-slate-400 text-sm">Loading from Drishti API\u2026</div>;
const ErrorState = ({ msg, onRetry }) => (
  <div className="max-w-lg mx-auto mt-16 text-center"><WifiOff className="h-10 w-10 text-slate-300 mx-auto" />
    <h2 className="mt-3 font-semibold text-slate-800">API not reachable</h2><p className="text-sm text-slate-500 mt-1">{msg}</p>
    <button onClick={onRetry} className="mt-4 rounded-lg px-4 py-2 text-sm text-white" style={{ background: NAVY }}>Retry</button></div>
);
function NotConnected({ onConnect }) {
  return (
    <div className="max-w-xl mx-auto mt-16 text-center">
      <Database className="h-12 w-12 text-slate-300 mx-auto" />
      <h1 className="mt-4 text-2xl font-bold text-slate-900">No real MPLADS data connected</h1>
      <p className="text-slate-500 mt-2">Drishti shows no statistics until official data is imported. Nothing here is synthetic.</p>
      <button onClick={onConnect} className="mt-5 inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-white font-medium" style={{ background: NAVY }}>
        <Upload className="h-4 w-4" /> Connect e-SAKSHI / Import official data</button>
    </div>
  );
}
function useApi(path, deps = []) {
  const [d, setD] = useState(null), [l, setL] = useState(true);
  useEffect(() => { setL(true); api.get(path).then((x) => { setD(x); setL(false); }).catch(() => setL(false)); }, deps); // eslint-disable-line
  return [d, l];
}

/* ================= DASHBOARD ================= */
function Dashboard({ role, setView }) {
  const [p, l] = useApi("/portfolio/summary");
  if (l || !p) return <Loading />;
  const greet = { "District Authority": "Works flagged for review in your district.", "State Nodal Authority": "Districts and agencies needing attention.", "Ministry (MoSPI)": "Systemic national patterns.", "MP / Constituency": "Works in your constituency." }[role];
  const cards = [
    ["Total Works", p.total, "imported", "#2563eb", LayoutDashboard],
    ["Under Review", p.under_review, "prioritised", "#e11d48", ListChecks],
    ["Cost Anomalies", p.cost_anomaly, "z \u2265 2.5", "#f59e0b", AlertTriangle],
    ["Delivery Risk", p.delivery_high, "ongoing warnings", "#7c3aed", TrendingUp],
    ["Duplicate Candidates", p.duplicate, "corroborated", "#0891b2", Copy],
    ["Completed", p.completed, "in portfolio", "#059669", CheckCircle2],
  ];
  const donut = [{ name: "High", value: p.priority_dist.high, c: "#e11d48" }, { name: "Medium", value: p.priority_dist.med, c: "#f59e0b" }, { name: "Low", value: p.priority_dist.low, c: "#059669" }];
  const maxD = Math.max(1, ...(p.top_districts || []).map((x) => x.value));
  return (
    <div className="space-y-5">
      <div><h1 className="text-2xl font-bold text-slate-900">Namaste &#128075;</h1><p className="text-sm text-slate-500">{greet}</p></div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {cards.map(([label, val, sub, color, Icon]) => (
          <div key={label} className="rounded-xl bg-white border border-slate-200 p-4 shadow-sm">
            <div className="h-9 w-9 rounded-lg flex items-center justify-center" style={{ background: color + "1a" }}><Icon className="h-5 w-5" style={{ color }} /></div>
            <div className="mt-3 text-2xl font-bold text-slate-900">{Number(val || 0).toLocaleString("en-IN")}</div>
            <div className="text-xs text-slate-500">{label}</div><div className="text-[11px]" style={{ color }}>{sub}</div>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-white border border-slate-200 p-4 shadow-sm"><h3 className="text-sm font-semibold text-slate-700 mb-2">Priority distribution</h3>
          <div className="flex items-center"><div style={{ width: 150, height: 150 }}><ResponsiveContainer><PieChart><Pie data={donut} dataKey="value" innerRadius={45} outerRadius={70} paddingAngle={2}>{donut.map((e, i) => <Cell key={i} fill={e.c} />)}</Pie></PieChart></ResponsiveContainer></div>
            <ul className="text-sm space-y-2 ml-2">{donut.map((e) => <li key={e.name} className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: e.c }} /><span className="text-slate-600">{e.name}</span><b className="text-slate-900">{e.value}</b></li>)}</ul></div>
        </div>
        <div className="rounded-xl bg-white border border-slate-200 p-4 shadow-sm"><h3 className="text-sm font-semibold text-slate-700 mb-2">Top districts by high-priority works</h3>
          <ul className="space-y-2.5">{(p.top_districts || []).map((x) => <li key={x.name} className="flex items-center gap-3 text-sm"><span className="w-32 truncate text-slate-600">{x.name}</span><div className="flex-1 h-2.5 rounded bg-slate-100 overflow-hidden"><div className="h-full rounded" style={{ width: `${(x.value / maxD) * 100}%`, background: "#e11d48" }} /></div><span className="w-8 text-right font-mono text-slate-700">{x.value}</span></li>)}
          {!(p.top_districts || []).length && <li className="text-sm text-slate-400">No high-priority works.</li>}</ul>
        </div>
      </div>
      {p.notes && p.notes.length > 0 && <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"><b>Data notes:</b> {p.notes.join(" ")}</div>}
      <button onClick={() => setView("queue")} className="rounded-lg px-4 py-2 text-sm font-medium text-white" style={{ background: NAVY }}>Open review queue</button>
    </div>
  );
}

/* ================= QUEUE ================= */
function Queue({ openCase }) {
  const [d, l] = useApi("/queue");
  const [sig, setSig] = useState("all");
  if (l || !d) return <Loading />;
  const rows = (d.works || []).filter((x) => sig === "all" || x.evidence.some((e) => e.kind === sig));
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3"><h1 className="text-xl font-bold text-slate-900">Review Queue</h1>
        <span className="text-sm text-slate-500">{rows.length} prioritised works</span>
        <select value={sig} onChange={(e) => setSig(e.target.value)} className="ml-auto text-sm border border-slate-300 rounded-lg px-2 py-2">
          <option value="all">All signals</option><option value="cost">Cost anomaly</option><option value="duplicate">Duplicate</option><option value="delivery_risk">Delivery risk</option><option value="concentration">Concentration</option></select>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        <table className="w-full text-sm"><thead className="bg-slate-50 text-slate-500 text-xs uppercase"><tr>
          <th className="text-left px-4 py-2.5">Priority</th><th className="text-left px-4 py-2.5">Work</th><th className="text-left px-4 py-2.5">District</th><th className="text-right px-4 py-2.5">Amount</th><th className="text-left px-4 py-2.5">Confidence</th><th className="text-left px-4 py-2.5">Signals</th></tr></thead>
          <tbody>{rows.map((c) => (
            <tr key={c.id} onClick={() => openCase(c)} className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer">
              <td className="px-4 py-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full text-xs font-bold text-white" style={{ background: c.priority >= 3 ? "#e11d48" : c.priority >= 2 ? "#f59e0b" : "#059669" }}>{c.priority}</span></td>
              <td className="px-4 py-3"><div className="font-medium text-slate-800">{c.title}</div><div className="text-xs text-slate-400 font-mono">{c.id} &middot; {c.agency}</div></td>
              <td className="px-4 py-3 text-slate-600">{c.district}</td><td className="px-4 py-3 text-right font-mono text-slate-700">{lakh(c.amount)}</td>
              <td className="px-4 py-3 text-slate-600">{c.confidence}</td>
              <td className="px-4 py-3"><div className="flex gap-1 flex-wrap">{c.evidence.map((e, i) => { const k = KIND[e.kind]; return <span key={i} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ring-1 ${k.bg} ${k.tx} ${k.rg}`}><k.Icon className="h-3 w-3" />{k.name}</span>; })}</div></td>
            </tr>))}</tbody>
        </table>
        {!rows.length && <div className="p-6 text-center text-sm text-slate-400">No works match this filter.</div>}
      </div>
      <p className="text-[11px] text-slate-400 flex items-center gap-1"><Info className="h-3.5 w-3.5" /> Leads for human review \u2014 never accusations. The officer decides.</p>
    </div>
  );
}

/* ================= DOSSIER ================= */
function Dossier({ c, role, back }) {
  const [verdict, setVerdict] = useState(null);
  const [hist, setHist] = useState([]);
  useEffect(() => { api.get(`/reviews/${c.id}`).then((r) => setHist(r.history || [])); }, [c.id]);
  const decide = (action, label) => api.post("/reviews", { work_id: c.id, action, role, signals_snapshot: c.evidence }).then((r) => { setVerdict(label); setHist(r.history || []); });
  return (
    <div className="max-w-4xl">
      <button onClick={back} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 mb-3"><ArrowLeft className="h-4 w-4" /> Back to queue</button>
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="px-6 py-5 border-b border-slate-200">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-500"><FileSearch className="h-4 w-4" /> CASE FILE {c.id}</div>
          <h1 className="mt-1 text-2xl text-slate-900" style={{ fontFamily: "Georgia, serif" }}>{c.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-600"><span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{c.district}</span><span>{c.agency}</span><span className="font-mono text-slate-900">{inr(c.amount)}</span><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{c.status}</span><span className="text-slate-400">Confidence: {c.confidence}</span></div>
        </div>
        <div className="px-6 py-5 space-y-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Why is this here?</h3>
          {c.evidence.map((s, i) => { const k = KIND[s.kind]; return (
            <div key={i} className="rounded-lg border border-slate-200 overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-100"><k.Icon className="h-4 w-4" style={{ color: k.c }} /><span className={`text-xs font-medium rounded-full px-2 py-0.5 ring-1 ${k.bg} ${k.tx} ${k.rg}`}>{s.label}</span><span className="ml-auto text-[11px] text-slate-400">Evidence: {s.strength}</span></div>
              <div className="px-4 py-3 space-y-3">
                <p className="text-[15px] font-medium text-slate-900">{s.headline}</p>
                {s.kind === "cost" && c.expected && (<div className="space-y-2 py-1"><Bar label="This work" value={c.amount} max={c.amount} col="#e11d48" /><Bar label="Model expects" value={c.expected} max={c.amount} col="#94a3b8" /></div>)}
                <Field label="Compared against" text={s.compared} /><Field label="Rule out first" text={s.rule} muted />
                <div className="flex items-start gap-2 rounded-md bg-slate-50 px-3 py-2"><ClipboardCheck className="h-4 w-4 text-slate-500 mt-0.5 shrink-0" /><div><div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">What to verify</div><div className="text-sm text-slate-700">{s.verify}</div></div></div>
              </div>
            </div>); })}
          <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-3">Source record from the connected dataset &middot; models: expected-cost regression, delivery-risk logistic, TF-IDF duplicate corroboration.</div>
        </div>
        <div className="border-t border-slate-200 px-6 py-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Officer decision</div>
          <div className="flex flex-wrap gap-2">
            <Act col="rose" on={() => decide("order_inspection", "Inspection ordered")}>Order site inspection</Act>
            <Act col="amber" on={() => decide("request_documents", "Documents requested")}>Request BOQ / documents</Act>
            <Act col="emerald" on={() => decide("mark_no_issue", "Reviewed \u2014 no issue")}>Mark reviewed \u2014 no issue</Act>
          </div>
          {verdict && <p className="mt-3 text-sm text-slate-600">Recorded: <b className="text-slate-900">{verdict}</b>. Officer decisions are stored for audit and future model evaluation.</p>}
          {hist.length > 0 && <div className="mt-3 text-xs text-slate-500"><b>Review history:</b> {hist.map((h, i) => <span key={i}>{h.action} ({h.role}){i < hist.length - 1 ? " \u00b7 " : ""}</span>)}</div>}
        </div>
      </div>
    </div>
  );
}
const Bar = ({ label, value, max, col }) => (<div className="flex items-center gap-3"><span className="w-24 shrink-0 text-xs text-slate-500">{label}</span><div className="flex-1 h-6 rounded bg-slate-100 overflow-hidden"><div className="h-full" style={{ width: `${Math.max(2, (value / max) * 100)}%`, background: col }} /></div><span className="w-24 text-right font-mono text-xs text-slate-700">{inr(value)}</span></div>);
const Field = ({ label, text, muted }) => (<div><div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div><div className={`text-sm ${muted ? "text-slate-500 italic" : "text-slate-700"}`}>{text}</div></div>);
const Act = ({ children, on, col }) => { const m = { rose: "border-rose-200 text-rose-700 hover:bg-rose-50", amber: "border-amber-200 text-amber-700 hover:bg-amber-50", emerald: "border-emerald-200 text-emerald-700 hover:bg-emerald-50" }[col]; return <button onClick={on} className={`rounded-lg border px-3 py-2 text-sm font-medium ${m}`}>{children}</button>; };

/* ================= RISK / DUPES / GEO ================= */
function RiskView({ openCase }) {
  const [d, l] = useApi("/risk"); const [mr] = useApi("/model-runs");
  if (l || !d) return <Loading />;
  const dr = mr && mr.delivery_risk;
  return (<div className="space-y-4"><h1 className="text-xl font-bold text-slate-900">Delivery-risk early warning</h1>
    {dr && !dr.available ? <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{dr.reason || "Delivery-risk model unavailable."}</div>
      : dr && dr.available ? <p className="text-sm text-slate-500">Model: {dr.method}; held-out AUC {dr.auc}, PR-AUC {dr.pr_auc}, precision@10% {dr.precision_at_10pct}. Predictions on ongoing works only.</p> : null}
    <div className="grid gap-3 md:grid-cols-2">{(d.works || []).map((c) => (
      <div key={c.id} onClick={() => openCase(c)} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm cursor-pointer hover:border-blue-300">
        <div className="flex items-center justify-between"><div className="font-medium text-slate-800">{c.title}</div><span className="text-lg font-bold text-blue-600">{Math.round(c.risk * 100)}%</span></div>
        <div className="text-xs text-slate-400 font-mono">{c.id} &middot; {c.district}</div>
        <div className="mt-2 h-2 rounded bg-slate-100 overflow-hidden"><div className="h-full rounded" style={{ width: `${c.risk * 100}%`, background: "#2563eb" }} /></div></div>))}
      {!(d.works || []).length && <div className="text-sm text-slate-400">No ongoing works flagged.</div>}</div></div>);
}
function DupesView() {
  const [d, l] = useApi("/duplicates");
  if (l || !d) return <Loading />;
  return (<div className="space-y-4"><h1 className="text-xl font-bold text-slate-900">Duplicate detection</h1>
    <p className="text-sm text-slate-500">Candidates require corroboration (text + agency + amount + dates). A candidate is <b>not</b> proof.</p>
    <div className="space-y-3">{(d.pairs || []).map((w, i) => (
      <div key={i} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="font-mono text-xs bg-slate-100 rounded px-2 py-0.5 inline-block">{w.id}</div>
        <div className="mt-1 text-sm text-slate-700">{w.title} &middot; {w.district}</div>
        {(w.evidence || []).filter((e) => e.kind === "duplicate").map((e, j) => <div key={j} className="mt-1 text-[11px] text-slate-500">{e.compared} &mdash; verify: {e.verify}</div>)}
      </div>))}
      {!(d.pairs || []).length && <div className="text-sm text-slate-400">No corroborated duplicates found.</div>}</div></div>);
}
function GeoView() {
  const [p, l] = useApi("/portfolio/summary");
  if (l || !p) return <Loading />;
  const max = Math.max(1, ...(p.top_districts || []).map((x) => x.value));
  return (<div className="space-y-4"><h1 className="text-xl font-bold text-slate-900">Geographic view</h1>
    <p className="text-sm text-slate-500">A map renders per-work markers when the source provides latitude/longitude. Otherwise, district-level distribution. Coordinates are never fabricated.</p>
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">{(p.top_districts || []).map((x) => (
      <div key={x.name} className="flex items-center gap-3 text-sm mb-2"><MapPin className="h-4 w-4 text-slate-400" /><span className="w-40 text-slate-700">{x.name}</span>
        <div className="flex-1 h-3 rounded bg-slate-100 overflow-hidden"><div className="h-full rounded" style={{ width: `${(x.value / max) * 100}%`, background: NAVY }} /></div><span className="w-8 text-right font-mono">{x.value}</span></div>))}</div></div>);
}

/* ================= DATA SOURCES (import + provenance + model transparency) ================= */
function DataView({ mode, onImported }) {
  const [ds] = useApi("/data-source");
  const [dq] = useApi("/data-quality");
  const [mr] = useApi("/model-runs");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const onFile = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    setBusy(true); setResult(null);
    const fmt = f.name.toLowerCase().endsWith(".json") ? "json" : "csv";
    const r = await api.upload("/imports/file", f, { fmt, mode: "real" });
    setResult(r); setBusy(false); onImported();
  };
  return (
    <div className="space-y-5 max-w-3xl">
      <h1 className="text-xl font-bold text-slate-900">Data sources &amp; provenance</h1>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-slate-800 mb-2">Connect real MPLADS data</h3>
        <div className="grid sm:grid-cols-2 gap-3">
          <label className="rounded-lg border border-dashed border-slate-300 p-4 text-center cursor-pointer hover:bg-slate-50">
            <Upload className="h-6 w-6 mx-auto text-slate-400" /><div className="mt-2 text-sm font-medium text-slate-700">Import official e-SAKSHI export</div>
            <div className="text-[11px] text-slate-400">CSV or JSON &mdash; columns auto-detected</div>
            <input type="file" accept=".csv,.json" className="hidden" onChange={onFile} />
          </label>
          <div className="rounded-lg border border-slate-200 p-4">
            <div className="text-sm font-medium text-slate-700">data.gov.in Open Data API</div>
            <div className="text-[11px] text-slate-500 mt-1">Set <span className="font-mono">DATAGOVIN_API_KEY</span> + resource id, then POST <span className="font-mono">/imports/datagovin</span>.</div>
            <div className="text-[11px] mt-2 text-amber-700">Live e-SAKSHI API: not verified &mdash; use export/import.</div>
          </div>
        </div>
        {busy && <p className="text-sm text-slate-500 mt-3">Importing &amp; running the engine\u2026</p>}
        {result && result.quality && (
          <div className="mt-4 rounded-lg bg-slate-50 border border-slate-200 p-3 text-sm">
            <div className="font-semibold text-slate-800 mb-1">Data quality report</div>
            <Row k="Received / accepted / rejected" v={`${result.quality.received} / ${result.quality.accepted} / ${result.quality.rejected}`} />
            <Row k="Size/quantity present" v={result.quality.has_size ? "Yes" : "No (fair-comparison confidence reduced)"} />
            <Row k="Checksum" v={result.provenance.checksum} /><Row k="Import id" v={result.import_id} />
            {result.quality.mapping && result.quality.mapping.missing_required.length > 0 && <div className="text-rose-600 mt-1">Missing required: {result.quality.mapping.missing_required.join(", ")}</div>}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm text-sm space-y-2">
        <div className="font-semibold text-slate-800">Current source</div>
        {ds && ds.provenance ? <>
          <Row k="Source" v={ds.provenance.source} /><Row k="Imported" v={ds.provenance.imported_at} />
          <Row k="Records" v={ds.provenance.record_count} /><Row k="Checksum" v={ds.provenance.checksum} />
        </> : <div className="text-slate-400">No dataset connected.</div>}
        <Row k="data.gov.in API" v={ds && ds.api_status ? ds.api_status.datagovin : "-"} />
        <Row k="e-SAKSHI API" v={ds && ds.api_status ? ds.api_status.esakshi : "-"} />
      </div>

      {mr && mr.connected !== false && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm text-sm">
          <div className="font-semibold text-slate-800 mb-2">Model transparency</div>
          {mr.expected_cost && <div className="mb-2"><b>Expected-cost:</b> {mr.expected_cost.available ? `${mr.expected_cost.method}, R\u00B2=${mr.expected_cost.r2}, MAE(log)=${mr.expected_cost.mae_log}, n=${mr.expected_cost.n}, confidence=${mr.expected_cost.confidence}` : "unavailable (too few records)"} <span className="text-slate-400">(R\u00B2 is fit quality, not accuracy)</span></div>}
          {mr.delivery_risk && <div><b>Delivery-risk:</b> {mr.delivery_risk.available ? `${mr.delivery_risk.method}, AUC=${mr.delivery_risk.auc}, PR-AUC=${mr.delivery_risk.pr_auc}` : mr.delivery_risk.reason}</div>}
        </div>
      )}
    </div>
  );
}
const Row = ({ k, v }) => <div className="flex justify-between gap-4 border-b border-slate-100 pb-1"><span className="text-slate-500">{k}</span><span className="text-slate-800 text-right font-mono text-xs break-all">{String(v)}</span></div>;
