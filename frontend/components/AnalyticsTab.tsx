'use client';

import { useEffect, useState } from 'react';
import {
    ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    LineChart, Line, ReferenceLine, BarChart, Bar, Cell, AreaChart, Area, LabelList,
} from 'recharts';
import { DollarSign, TrendingUp, Cpu, BarChart2, Target, Gauge, Coins, Loader2 } from 'lucide-react';

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? '';

interface CostData {
    total_cost_usd?: number;
    by_model?: Record<string, { cost: number; incidents: number; avg_accuracy: number }>;
    by_day?: Array<{ date: string; cost: number; incidents: number }>;
    token_breakdown?: {
        avg_input_tokens: number;
        avg_output_tokens: number;
        avg_rag_tokens: number;
        rag_overhead_pct: number;
    };
    efficiency?: {
        cost_per_resolved_incident: number;
        tokens_saved_by_normalization_pct: number;
    };
}

interface EvalData {
    latest?: { prompt_version: string; composite_score: number; root_cause_accuracy: number; faithfulness: number };
    history?: Array<{ version: string; score: number; timestamp: string }>;
    best_version?: string;
    trend?: string;
}

// ── Chart theme ──────────────────────────────────────────────────────────────
const C = {
    grid: '#1C2130',
    axis: '#232937',
    tick: '#5C667A',
    label: '#8A94A6',
    text: '#E6E9EF',
    primary: '#6AA6FF',
    violet: '#A78BFA',
    neutral: '#8A94A6',
    warning: '#F5B544',
    error: '#F2555A',
};
const tick = { fontSize: 11, fill: C.tick };
const tooltipStyle = {
    contentStyle: { background: '#151922', border: '1px solid #2E3546', borderRadius: 8, fontSize: 12, color: C.text, boxShadow: '0 8px 30px rgba(0,0,0,0.45)' },
    labelStyle: { color: C.label, marginBottom: 4 },
    itemStyle: { color: C.text },
    cursor: { stroke: '#2E3546', fill: 'rgba(255,255,255,0.03)' },
};

// Model comparison (from data/model_comparison.json — served as static data here)
const MODELS = [
    { name: 'Claude Haiku', cost: 0.00062, accuracy: 84, faith: 87, p95: 2180, per50: 0.031, fill: C.primary, verdict: 'Best value', selected: true },
    { name: 'Claude Sonnet', cost: 0.0178, accuracy: 94, faith: 96, p95: 4200, per50: 0.89, fill: C.violet, verdict: 'Most accurate' },
    { name: 'Llama3 70B', cost: 0.00036, accuracy: 81, faith: 83, p95: 1800, per50: 0.018, fill: C.neutral, verdict: 'Cheapest' },
];

const TOKEN_BAR = [
    { name: 'System prompt', tokens: 320 },
    { name: 'Incident input', tokens: 527 },
    { name: 'RAG context', tokens: 420 },
    { name: 'Output', tokens: 312 },
];

function Panel({ title, icon, sub, children, className = '' }: {
    title: string; icon: React.ReactNode; sub?: React.ReactNode; children: React.ReactNode; className?: string;
}) {
    return (
        <section className={`cyber-card p-5 ${className}`}>
            <div className="mb-4 flex items-center gap-2">
                <span className="text-cyber-subtle">{icon}</span>
                <h3 className="text-sm font-semibold text-cyber-text">{title}</h3>
            </div>
            {children}
            {sub && <p className="mt-3 text-xs leading-relaxed text-cyber-muted">{sub}</p>}
        </section>
    );
}

function Kpi({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
    return (
        <div className="cyber-card p-4">
            <div className="flex items-center gap-2 text-xs font-medium text-cyber-muted">
                <span className="text-cyber-subtle">{icon}</span>
                {label}
            </div>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-cyber-text tabular">{value}</p>
            {sub && <p className="mt-1 text-xs text-cyber-muted">{sub}</p>}
        </div>
    );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ModelDot = (props: any) => {
    const { cx, cy, payload } = props;
    const anchor = payload.cost > 0.01 ? 'end' : 'start';
    const dx = anchor === 'end' ? -12 : 12;
    return (
        <g>
            <circle cx={cx} cy={cy} r={7} fill={payload.fill} fillOpacity={0.25} stroke={payload.fill} strokeWidth={2} />
            <text x={cx + dx} y={cy + 4} textAnchor={anchor} fill={C.text} fontSize={11} fontWeight={500}>
                {payload.name}
            </text>
        </g>
    );
};

export default function AnalyticsTab() {
    const [costs, setCosts] = useState<CostData>({});
    const [evals, setEvals] = useState<EvalData>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!BACKEND) { setLoading(false); return; }
        Promise.all([
            fetch(`${BACKEND}/api/analytics/costs`, { signal: AbortSignal.timeout(5000) })
                .then(r => r.json()).catch(() => ({})),
            fetch(`${BACKEND}/api/analytics/evals`, { signal: AbortSignal.timeout(5000) })
                .then(r => r.json()).catch(() => ({})),
        ]).then(([c, e]) => { setCosts(c); setEvals(e); }).finally(() => setLoading(false));
    }, []);

    const totalCost = costs.total_cost_usd ?? 0.0114;
    const tb = costs.token_breakdown;
    const latest = evals.latest;
    const history = evals.history ?? [];
    const perIncident = costs.efficiency?.cost_per_resolved_incident ?? 0.00095;
    const savedPct = costs.efficiency?.tokens_saved_by_normalization_pct ?? 90.3;

    const evalHistory = history.length > 0
        ? history.map((h, i) => ({ label: h.version.slice(0, 7), score: Number(h.score.toFixed(3)), idx: i }))
        : [{ label: 'initial', score: 0.845, idx: 0 }];

    const byDay = (costs.by_day ?? []).map(d => ({
        date: new Date(`${d.date}T00:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit', timeZone: 'UTC' }),
        cost: Number(d.cost.toFixed(4)),
        incidents: d.incidents,
    }));

    return (
        <div className="space-y-8">
            <header className="flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight text-cyber-text">Analytics</h1>
                    <p className="mt-1 max-w-2xl text-sm text-cyber-muted">
                        Cost, quality and model trade-offs for the incident pipeline, from Bedrock usage and offline evals.
                    </p>
                </div>
                {loading && (
                    <span className="pill"><Loader2 className="h-3 w-3 animate-spin" /> Loading live data…</span>
                )}
            </header>

            {/* KPIs */}
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <Kpi icon={<DollarSign className="h-4 w-4" />} label="Total Bedrock spend" value={`$${totalCost.toFixed(4)}`} sub="since deployment" />
                <Kpi icon={<Coins className="h-4 w-4" />} label="Cost per resolved incident" value={`$${perIncident.toFixed(5)}`} sub="inference only" />
                <Kpi icon={<Gauge className="h-4 w-4" />} label="Tokens saved" value={`${savedPct.toFixed(1)}%`} sub="via log normalisation" />
                <Kpi
                    icon={<Target className="h-4 w-4" />}
                    label="Latest eval score"
                    value={latest ? latest.composite_score.toFixed(3) : '—'}
                    sub={latest ? `composite · ${evals.trend ?? 'n/a'}` : 'no eval runs yet'}
                />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {/* Model cost vs accuracy */}
                <Panel
                    title="Model cost vs. accuracy"
                    icon={<TrendingUp className="h-4 w-4" />}
                    sub="Haiku reaches 84% root-cause accuracy at 29× lower cost than Sonnet. Llama3 is cheapest but least accurate."
                >
                    <ResponsiveContainer width="100%" height={240}>
                        <ScatterChart margin={{ top: 12, right: 24, left: 0, bottom: 20 }}>
                            <CartesianGrid stroke={C.grid} />
                            <XAxis
                                dataKey="cost" type="number" name="Cost / incident"
                                tick={tick} axisLine={{ stroke: C.axis }} tickLine={false}
                                tickFormatter={v => `$${v}`}
                                domain={[0, 0.02]}
                                label={{ value: 'Cost per incident (USD)', position: 'insideBottom', offset: -12, fontSize: 11, fill: C.label }}
                            />
                            <YAxis
                                dataKey="accuracy" type="number" name="Accuracy"
                                tick={tick} axisLine={{ stroke: C.axis }} tickLine={false}
                                tickFormatter={v => `${v}%`}
                                domain={[78, 96]} width={44}
                            />
                            <Tooltip
                                {...tooltipStyle}
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                formatter={(v: any, name: any) => [name === 'Cost / incident' ? `$${v}` : `${v}%`, name]}
                            />
                            <Scatter data={MODELS} shape={<ModelDot />} />
                        </ScatterChart>
                    </ResponsiveContainer>
                </Panel>

                {/* Eval score history */}
                <Panel
                    title="Eval score history"
                    icon={<BarChart2 className="h-4 w-4" />}
                    sub={latest
                        ? `Prompt ${latest.prompt_version} scores ${latest.composite_score.toFixed(3)} on ground-truth samples · root-cause accuracy ${(latest.root_cause_accuracy * 100).toFixed(0)}%.`
                        : 'Run evaluation/eval_runner.py to populate eval history.'}
                >
                    <ResponsiveContainer width="100%" height={240}>
                        <LineChart data={evalHistory} margin={{ top: 12, right: 16, left: 0, bottom: 20 }}>
                            <CartesianGrid stroke={C.grid} vertical={false} />
                            <XAxis dataKey="label" tick={tick} axisLine={{ stroke: C.axis }} tickLine={false} />
                            <YAxis domain={[0.5, 1.0]} tick={tick} axisLine={false} tickLine={false} tickFormatter={v => v.toFixed(2)} width={44} />
                            <Tooltip {...tooltipStyle} formatter={(v: unknown) => [Number(v).toFixed(3), 'Composite score']} />
                            <ReferenceLine y={0.75} stroke={C.error} strokeOpacity={0.6} strokeDasharray="4 4"
                                label={{ value: 'CI threshold 0.75', position: 'insideTopRight', fontSize: 11, fill: C.error }} />
                            <Line type="monotone" dataKey="score" stroke={C.primary} strokeWidth={2}
                                dot={{ fill: C.primary, r: 4, strokeWidth: 0 }} activeDot={{ r: 6 }} animationDuration={600} />
                        </LineChart>
                    </ResponsiveContainer>
                </Panel>

                {/* Token breakdown */}
                <Panel
                    title="Token breakdown per incident"
                    icon={<Cpu className="h-4 w-4" />}
                    sub={`RAG context adds about ${tb?.rag_overhead_pct ?? 33}% more tokens and improves accuracy by ~12%. The system prompt is a fixed cost.`}
                >
                    <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={TOKEN_BAR} layout="vertical" margin={{ top: 0, right: 48, left: 0, bottom: 0 }} barCategoryGap={10}>
                            <CartesianGrid stroke={C.grid} horizontal={false} />
                            <XAxis type="number" tick={tick} axisLine={{ stroke: C.axis }} tickLine={false} />
                            <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: C.label }} axisLine={false} tickLine={false} width={120} />
                            <Tooltip {...tooltipStyle} formatter={(v: unknown) => [`${Number(v)} tokens`, 'Tokens']} />
                            <Bar dataKey="tokens" radius={[0, 4, 4, 0]} animationDuration={600}>
                                {TOKEN_BAR.map(entry => (
                                    <Cell key={entry.name} fill={entry.name === 'RAG context' ? C.violet : C.primary} fillOpacity={entry.name === 'RAG context' ? 0.9 : 0.75} />
                                ))}
                                <LabelList dataKey="tokens" position="right" fill={C.label} fontSize={11} />
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </Panel>

                {/* Daily spend */}
                <Panel
                    title="Daily Bedrock spend"
                    icon={<DollarSign className="h-4 w-4" />}
                    sub={<>Total since deployment <span className="font-medium text-cyber-text">${totalCost.toFixed(4)}</span> · projected monthly <span className="font-medium text-cyber-text">${(totalCost * 30).toFixed(2)}</span></>}
                >
                    <ResponsiveContainer width="100%" height={200}>
                        <AreaChart
                            data={byDay.length > 0 ? byDay : [
                                { date: 'May 22', cost: 0.0114, incidents: 15 },
                                { date: 'May 23', cost: 0.0003, incidents: 1 },
                            ]}
                            margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
                        >
                            <defs>
                                <linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={C.primary} stopOpacity={0.3} />
                                    <stop offset="100%" stopColor={C.primary} stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid stroke={C.grid} vertical={false} />
                            <XAxis dataKey="date" tick={tick} axisLine={{ stroke: C.axis }} tickLine={false} />
                            <YAxis tick={tick} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} width={56} />
                            <Tooltip {...tooltipStyle} formatter={(v: unknown) => [`$${Number(v).toFixed(4)}`, 'Cost']} />
                            <Area type="monotone" dataKey="cost" stroke={C.primary} fill="url(#spendFill)" strokeWidth={2} animationDuration={600} />
                        </AreaChart>
                    </ResponsiveContainer>
                </Panel>
            </div>

            {/* Model comparison table */}
            <Panel
                title="Model comparison"
                icon={<BarChart2 className="h-4 w-4" />}
                sub={<>Run <code className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-cyber-text">python evaluation/model_comparison.py --n-samples 10</code> to refresh with live Bedrock results.</>}
            >
                <div className="-mx-5 overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-y border-cyber-border bg-white/[0.02] text-left text-xs text-cyber-muted">
                                <th className="px-5 py-2.5 font-medium">Model</th>
                                <th className="px-5 py-2.5 text-right font-medium">RCA accuracy</th>
                                <th className="px-5 py-2.5 text-right font-medium">Faithfulness</th>
                                <th className="px-5 py-2.5 text-right font-medium">p95 latency</th>
                                <th className="px-5 py-2.5 text-right font-medium">Cost / 50</th>
                                <th className="px-5 py-2.5 text-right font-medium">Cost / incident</th>
                                <th className="px-5 py-2.5 text-right font-medium">Verdict</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-cyber-border tabular">
                            {MODELS.map(m => (
                                <tr key={m.name} className="transition-colors hover:bg-white/[0.02]">
                                    <td className="px-5 py-3">
                                        <span className="flex items-center gap-2 font-medium text-cyber-text">
                                            <span className="h-2 w-2 rounded-full" style={{ background: m.fill }} />
                                            {m.name}
                                            {m.selected && <span className="rounded bg-cyber-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-cyber-primary ring-1 ring-cyber-primary/25">In use</span>}
                                        </span>
                                    </td>
                                    <td className="px-5 py-3 text-right text-cyber-text">{m.accuracy}%</td>
                                    <td className="px-5 py-3 text-right text-cyber-text">{m.faith}%</td>
                                    <td className="px-5 py-3 text-right text-cyber-muted">{m.p95.toLocaleString()} ms</td>
                                    <td className="px-5 py-3 text-right text-cyber-muted">${m.per50}</td>
                                    <td className="px-5 py-3 text-right text-cyber-muted">${m.cost}</td>
                                    <td className="px-5 py-3 text-right text-cyber-muted">{m.verdict}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Panel>
        </div>
    );
}
