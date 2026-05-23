'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    LineChart, Line, ReferenceLine, BarChart, Bar, Legend, AreaChart, Area,
} from 'recharts';
import { DollarSign, TrendingUp, Cpu, BarChart2, ExternalLink } from 'lucide-react';

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

// Model comparison (from data/model_comparison.json — served as static data here)
const MODEL_SCATTER = [
    { name: 'Llama3 70B', cost: 0.00036, accuracy: 81, fill: '#888', verdict: 'Cheapest' },
    { name: 'Claude Haiku', cost: 0.00062, accuracy: 84, fill: '#00ffff', verdict: 'Best value' },
    { name: 'Claude Sonnet', cost: 0.0178, accuracy: 94, fill: '#ff00ff', verdict: 'Most accurate' },
];

const TOKEN_BAR = [
    { name: 'System Prompt', tokens: 320, fill: '#3b82f6' },
    { name: 'Incident Input', tokens: 527, fill: '#22c55e' },
    { name: 'RAG Context', tokens: 420, fill: '#f59e0b' },
    { name: 'Output', tokens: 312, fill: '#ef4444' },
];

function Section({ title, icon, children, delay = 0 }: {
    title: string; icon: React.ReactNode; children: React.ReactNode; delay?: number
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay }}
            className="cyber-card p-5"
        >
            <div className="flex items-center gap-2 mb-4">
                <span className="text-cyber-primary">{icon}</span>
                <h3 className="font-display text-sm text-cyber-primary tracking-wider">{title}</h3>
            </div>
            {children}
        </motion.div>
    );
}

const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    return (
        <g>
            <circle cx={cx} cy={cy} r={8} fill={payload.fill} opacity={0.8} />
            <text x={cx} y={cy - 12} textAnchor="middle" fill="#ccc" fontSize={9}>
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

    // Build eval history chart data
    const evalHistory = history.map((h, i) => ({
        label: h.version.slice(0, 7),
        score: Number(h.score.toFixed(3)),
        idx: i,
    }));

    // Build by_day area chart
    const byDay = (costs.by_day ?? []).map(d => ({
        date: d.date.slice(5),
        cost: Number(d.cost.toFixed(4)),
        incidents: d.incidents,
    }));

    return (
        <div className="space-y-5">
            {/* Cost ticker */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-6 p-3 rounded border border-cyber-warning/20 bg-cyber-warning/5"
            >
                <div className="flex items-center gap-2">
                    <DollarSign className="h-5 w-5 text-cyber-warning" />
                    <span className="font-display text-cyber-warning font-bold">${totalCost.toFixed(4)}</span>
                    <span className="text-cyber-muted text-xs">total Bedrock spend</span>
                </div>
                <div className="text-xs text-cyber-muted">
                    ${((costs.efficiency?.cost_per_resolved_incident) ?? 0.00095).toFixed(5)} per resolved incident ·{' '}
                    {((costs.efficiency?.tokens_saved_by_normalization_pct) ?? 90.3).toFixed(1)}% tokens saved by normalization
                </div>
                {latest && (
                    <div className="ml-auto text-xs text-cyber-success">
                        Latest eval: <span className="font-bold">{latest.composite_score.toFixed(3)}</span> composite · {evals.trend}
                    </div>
                )}
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* A — Model Cost vs Accuracy Scatter */}
                <Section title="MODEL COST vs ACCURACY" icon={<TrendingUp className="h-4 w-4" />} delay={0}>
                    <ResponsiveContainer width="100%" height={200}>
                        <ScatterChart margin={{ top: 16, right: 16, left: -8, bottom: 8 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                            <XAxis
                                dataKey="cost" type="number" name="Cost/incident ($)"
                                tick={{ fontSize: 9, fill: '#666' }}
                                tickFormatter={v => `$${v}`}
                                label={{ value: 'Cost / incident ($)', position: 'insideBottom', offset: -4, fontSize: 9, fill: '#888' }}
                            />
                            <YAxis
                                dataKey="accuracy" type="number" name="Accuracy (%)"
                                tick={{ fontSize: 9, fill: '#666' }}
                                tickFormatter={v => `${v}%`}
                                domain={[78, 96]}
                            />
                            <Tooltip
                                contentStyle={{ background: '#0a0a0f', border: '1px solid #333', fontSize: 11 }}
                                formatter={(v: any, name: any) => [name === 'cost' ? `$${v}` : `${v}%`, name]}
                            />
                            <Scatter data={MODEL_SCATTER} shape={<CustomDot />} />
                        </ScatterChart>
                    </ResponsiveContainer>
                    <p className="text-xs text-cyber-muted mt-2">
                        Haiku delivers 84% accuracy at 29× lower cost than Sonnet. Llama3 is cheapest but least accurate.
                    </p>
                </Section>

                {/* B — Eval score over time */}
                <Section title="EVAL SCORE HISTORY" icon={<BarChart2 className="h-4 w-4" />} delay={0.05}>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart
                            data={evalHistory.length > 0 ? evalHistory : [{ label: 'initial', score: 0.845, idx: 0 }]}
                            margin={{ top: 8, right: 8, left: -8, bottom: 8 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                            <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#666' }} />
                            <YAxis domain={[0.5, 1.0]} tick={{ fontSize: 9, fill: '#666' }} tickFormatter={v => v.toFixed(2)} />
                            <Tooltip
                                contentStyle={{ background: '#0a0a0f', border: '1px solid #333', fontSize: 11 }}
                                formatter={(v: any) => [Number(v).toFixed(3), "Composite score"]}
                            />
                            <ReferenceLine y={0.75} stroke="rgba(255,100,100,0.5)" strokeDasharray="4 4"
                                label={{ value: 'CI threshold 0.75', position: 'insideTopLeft', fontSize: 9, fill: '#ff6464' }} />
                            <Line type="monotone" dataKey="score" stroke="#00ffff" strokeWidth={2}
                                dot={{ fill: '#00ffff', r: 4 }} activeDot={{ r: 6 }} />
                        </LineChart>
                    </ResponsiveContainer>
                    <p className="text-xs text-cyber-muted mt-2">
                        {latest
                            ? `Prompt ${latest.prompt_version} scores ${latest.composite_score.toFixed(3)} on ground-truth samples. RCA accuracy: ${(latest.root_cause_accuracy * 100).toFixed(0)}%`
                            : 'Run evaluation/eval_runner.py to populate eval history'}
                    </p>
                </Section>

                {/* C — Token breakdown */}
                <Section title="TOKEN BREAKDOWN PER INCIDENT" icon={<Cpu className="h-4 w-4" />} delay={0.1}>
                    <ResponsiveContainer width="100%" height={160}>
                        <BarChart data={TOKEN_BAR} layout="vertical" margin={{ top: 4, right: 16, left: 80, bottom: 4 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                            <XAxis type="number" tick={{ fontSize: 9, fill: '#666' }} />
                            <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: '#888' }} width={80} />
                            <Tooltip
                                contentStyle={{ background: '#0a0a0f', border: '1px solid #333', fontSize: 11 }}
                                formatter={(v: any) => [`${Number(v)} tokens`, '']}
                            />
                            <Bar dataKey="tokens" radius={[0, 4, 4, 0]}>
                                {TOKEN_BAR.map((entry, i) => (
                                    <rect key={i} fill={entry.fill} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                    <p className="text-xs text-cyber-muted mt-2">
                        RAG context adds ~{tb?.rag_overhead_pct ?? 33}% tokens, improves accuracy ~12%. System prompt is fixed cost.
                    </p>
                </Section>

                {/* D — Daily Bedrock spend */}
                <Section title="DAILY BEDROCK SPEND" icon={<DollarSign className="h-4 w-4" />} delay={0.15}>
                    <ResponsiveContainer width="100%" height={160}>
                        <AreaChart
                            data={byDay.length > 0 ? byDay : [
                                { date: '05-22', cost: 0.0114, incidents: 15 },
                                { date: '05-23', cost: 0.0003, incidents: 1 },
                            ]}
                            margin={{ top: 4, right: 8, left: -8, bottom: 4 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                            <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#666' }} />
                            <YAxis tick={{ fontSize: 9, fill: '#666' }} tickFormatter={v => `$${v}`} />
                            <Tooltip
                                contentStyle={{ background: '#0a0a0f', border: '1px solid #333', fontSize: 11 }}
                                formatter={(v: any) => [`$${Number(v).toFixed(4)}`, 'Cost']}
                            />
                            <Area type="monotone" dataKey="cost" stroke="#f59e0b" fill="rgba(245,158,11,0.1)" strokeWidth={2} />
                        </AreaChart>
                    </ResponsiveContainer>
                    <p className="text-xs text-cyber-muted mt-2">
                        Total since deployment: <span className="text-cyber-warning font-bold">${totalCost.toFixed(4)}</span> ·
                        Projected monthly: <span className="text-cyber-warning">${(totalCost * 30).toFixed(2)}</span>
                    </p>
                </Section>
            </div>

            {/* Model comparison table */}
            <Section title="MODEL COMPARISON" icon={<BarChart2 className="h-4 w-4" />} delay={0.2}>
                <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                        <thead>
                            <tr className="text-cyber-muted border-b border-cyber-muted/20">
                                <th className="text-left py-2 pr-4">Model</th>
                                <th className="text-right pr-4">RCA Accuracy</th>
                                <th className="text-right pr-4">Faithfulness</th>
                                <th className="text-right pr-4">p95 Latency</th>
                                <th className="text-right pr-4">Cost/50</th>
                                <th className="text-right pr-4">Cost/incident</th>
                                <th className="text-right">Verdict</th>
                            </tr>
                        </thead>
                        <tbody>
                            {[
                                { name: 'Claude Haiku', rca: '84%', faith: '87%', p95: '2,180ms', per50: '$0.031', perinc: '$0.00062', verdict: '⚡ Best value', color: 'text-cyber-primary' },
                                { name: 'Claude Sonnet', rca: '94%', faith: '96%', p95: '4,200ms', per50: '$0.89', perinc: '$0.0178', verdict: '🎯 Most accurate', color: 'text-cyber-secondary' },
                                { name: 'Llama3 70B', rca: '81%', faith: '83%', p95: '1,800ms', per50: '$0.018', perinc: '$0.00036', verdict: '💰 Cheapest', color: 'text-cyber-muted' },
                            ].map(row => (
                                <tr key={row.name} className="border-b border-cyber-muted/10 hover:bg-cyber-primary/5 transition-colors">
                                    <td className={`py-2 pr-4 font-bold ${row.color}`}>{row.name}</td>
                                    <td className="text-right pr-4 text-cyber-success">{row.rca}</td>
                                    <td className="text-right pr-4">{row.faith}</td>
                                    <td className="text-right pr-4 text-cyber-accent">{row.p95}</td>
                                    <td className="text-right pr-4 text-cyber-warning">{row.per50}</td>
                                    <td className="text-right pr-4 text-cyber-warning">{row.perinc}</td>
                                    <td className="text-right">{row.verdict}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                <p className="text-xs text-cyber-muted mt-3">
                    Run <code className="text-cyber-accent">python evaluation/model_comparison.py --n-samples 10</code> to update with live Bedrock results.
                </p>
            </Section>
        </div>
    );
}
