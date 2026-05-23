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
    color: string;
    delay: number;
}

function MetricCard({ icon, label, value, sub, color, delay }: MetricCardProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay }}
            className="flex-1 cyber-card p-4 flex items-center gap-4 min-w-[140px]"
        >
            <div className={`${color} opacity-80 flex-shrink-0`}>{icon}</div>
            <div className="min-w-0">
                <p className="text-cyber-muted text-xs font-display tracking-wider uppercase mb-0.5 truncate">{label}</p>
                <div className="flex items-baseline gap-1.5 flex-wrap">
                    <span className={`font-display text-xl font-bold ${color} truncate`}>{value}</span>
                    {sub && <span className="text-cyber-muted text-xs truncate">{sub}</span>}
                </div>
            </div>
        </motion.div>
    );
}

export default function MetricsBar({ metrics }: { metrics: DashboardMetrics }) {
    return (
        <div className="flex gap-3 flex-wrap mb-4">
            <MetricCard
                icon={<Activity className="h-5 w-5" />}
                label="Total Incidents"
                value={String(metrics.total)}
                sub="real datasets"
                color="text-cyber-primary"
                delay={0}
            />
            <MetricCard
                icon={<CheckCircle2 className="h-5 w-5" />}
                label="Resolved"
                value={String(metrics.resolvedCount)}
                sub={`(${metrics.resolvedPct}%)${metrics.demoRuns ? ` +${metrics.demoRuns} live` : ''}`}
                color="text-cyber-success"
                delay={0.05}
            />
            <MetricCard
                icon={<Clock className="h-5 w-5" />}
                label="Avg Resolution"
                value={metrics.avgResTimeSec === '—' ? '—' : `${metrics.avgResTimeSec}s`}
                color="text-cyber-accent"
                delay={0.1}
            />
            <MetricCard
                icon={<DollarSign className="h-5 w-5" />}
                label="Total AI Cost"
                value={`$${metrics.totalCost}`}
                color="text-cyber-warning"
                delay={0.15}
            />
            {metrics.mostCommonType && metrics.mostCommonType !== '—' && (
                <MetricCard
                    icon={<TrendingUp className="h-5 w-5" />}
                    label="Most Common"
                    value={metrics.mostCommonType.split(' (')[0]}
                    sub={metrics.mostCommonType.includes('(') ? `×${metrics.mostCommonType.split('(')[1].replace(')', '')}` : ''}
                    color="text-cyber-secondary"
                    delay={0.2}
                />
            )}
            {metrics.worstIncident && metrics.worstIncident !== '—' && (
                <MetricCard
                    icon={<AlertTriangle className="h-5 w-5" />}
                    label="Worst Peak"
                    value={metrics.worstIncident.split('·')[0].trim()}
                    sub={metrics.worstIncident.split('·')[1]?.trim()}
                    color="text-cyber-error"
                    delay={0.25}
                />
            )}
        </div>
    );
}
