'use client';

import { motion } from 'framer-motion';
import { Activity, CheckCircle2, Clock, DollarSign } from 'lucide-react';

export interface DashboardMetrics {
    total: number;
    resolvedCount: number;
    resolvedPct: number;
    avgResTimeSec: string;
    totalCost: string;
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
            className="flex-1 cyber-card p-4 flex items-center gap-4"
        >
            <div className={`${color} opacity-80`}>{icon}</div>
            <div>
                <p className="text-cyber-muted text-xs font-display tracking-wider uppercase mb-0.5">{label}</p>
                <div className="flex items-baseline gap-2">
                    <span className={`font-display text-2xl font-bold ${color}`}>{value}</span>
                    {sub && <span className="text-cyber-muted text-xs">{sub}</span>}
                </div>
            </div>
        </motion.div>
    );
}

export default function MetricsBar({ metrics }: { metrics: DashboardMetrics }) {
    return (
        <div className="flex gap-4 flex-wrap mb-6">
            <MetricCard
                icon={<Activity className="h-6 w-6" />}
                label="Total Incidents"
                value={String(metrics.total)}
                color="text-cyber-primary"
                delay={0}
            />
            <MetricCard
                icon={<CheckCircle2 className="h-6 w-6" />}
                label="Resolved"
                value={String(metrics.resolvedCount)}
                sub={`(${metrics.resolvedPct}%)`}
                color="text-cyber-success"
                delay={0.05}
            />
            <MetricCard
                icon={<Clock className="h-6 w-6" />}
                label="Avg Resolution Time"
                value={metrics.avgResTimeSec === '—' ? '—' : `${metrics.avgResTimeSec}s`}
                color="text-cyber-accent"
                delay={0.1}
            />
            <MetricCard
                icon={<DollarSign className="h-6 w-6" />}
                label="Total AI Cost"
                value={`$${metrics.totalCost}`}
                color="text-cyber-warning"
                delay={0.15}
            />
        </div>
    );
}
