'use client';

import { motion } from 'framer-motion';
import { Activity, CheckCircle2, Clock, DollarSign, TrendingUp, AlertTriangle } from 'lucide-react';

export interface DashboardMetrics {
    total: number;
    resolvedCount: number;
    resolvedPct: number;
    avgResTimeSec: string;
    totalCost: string;
    mostCommonType?: string;
    worstIncident?: string;
    demoRuns?: number;
}

interface MetricCardProps {
    icon: React.ReactNode;
    label: string;
    value: string;
    sub?: string;
    delta?: string;
    valueClass?: string;
}

function MetricCard({ icon, label, value, sub, delta, valueClass }: MetricCardProps) {
    return (
        <div className="cyber-card min-w-0 p-4">
            <div className="flex items-center gap-2 text-cyber-muted">
                <span className="text-cyber-subtle">{icon}</span>
                <span className="truncate text-xs font-medium">{label}</span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
                <motion.span
                    key={value}
                    initial={{ opacity: 0.4 }}
                    animate={{ opacity: 1 }}
                    className={`truncate text-xl font-semibold sm:text-2xl tracking-tight tabular ${valueClass ?? 'text-cyber-text'}`}
                    title={value}
                >
                    {value}
                </motion.span>
                {delta && (
                    <span className="flex-shrink-0 rounded-md bg-cyber-success/10 px-1.5 py-0.5 text-[11px] font-medium text-cyber-success tabular">
                        {delta}
                    </span>
                )}
            </div>
            {sub && <p className="mt-1 truncate text-xs text-cyber-muted" title={sub}>{sub}</p>}
        </div>
    );
}

export default function MetricsBar({ metrics }: { metrics: DashboardMetrics }) {
    const runs = metrics.demoRuns ?? 0;
    const common = metrics.mostCommonType && metrics.mostCommonType !== '—' ? metrics.mostCommonType : null;
    const worst = metrics.worstIncident && metrics.worstIncident !== '—' ? metrics.worstIncident : null;

    return (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <MetricCard icon={<Activity className="h-4 w-4" />} label="Total incidents" value={String(metrics.total)} sub="GAIA + AIOpsArena datasets" />
            <MetricCard
                icon={<CheckCircle2 className="h-4 w-4" />}
                label="Resolved"
                value={String(metrics.resolvedCount)}
                sub={`${metrics.resolvedPct}% resolution rate`}
                delta={runs > 0 ? `+${runs}` : undefined}
            />
            <MetricCard
                icon={<Clock className="h-4 w-4" />}
                label="Avg. resolution"
                value={metrics.avgResTimeSec === '—' ? '—' : `${metrics.avgResTimeSec}s`}
                sub="detection to fix"
            />
            <MetricCard
                icon={<DollarSign className="h-4 w-4" />}
                label="Total AI cost"
                value={`$${metrics.totalCost}`}
                sub="Bedrock inference"
                delta={runs > 0 ? `+$${(runs * 0.000934).toFixed(4)}` : undefined}
            />
            <MetricCard
                icon={<TrendingUp className="h-4 w-4" />}
                label="Most common"
                value={common ? common.split(' (')[0].replace(/^cpu/, 'CPU').replace(/^\w/, c => c.toUpperCase()) : '—'}
                sub={common?.includes('(') ? `${common.split('(')[1].replace(')', '')} incidents` : undefined}
            />
            <MetricCard
                icon={<AlertTriangle className="h-4 w-4" />}
                label="Worst peak"
                value={worst ? (worst.split('·')[1]?.trim().replace(' peak', '') ?? '—') : '—'}
                sub={worst ? worst.split('·')[0].trim() : undefined}
                valueClass={worst ? 'text-cyber-error' : undefined}
            />
        </div>
    );
}
