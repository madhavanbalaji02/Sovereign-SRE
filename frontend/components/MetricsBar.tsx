'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Activity, CheckCircle2, Clock, DollarSign, TrendingUp, AlertTriangle, Zap } from 'lucide-react';

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
    highlight?: boolean;
    badge?: string;
}

function MetricCard({ icon, label, value, sub, color, delay, highlight, badge }: MetricCardProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay }}
            className={`flex-1 cyber-card p-4 flex items-center gap-4 min-w-[140px] relative overflow-hidden transition-all duration-300 ${
                highlight ? 'border border-cyber-success/60 shadow-[0_0_12px_rgba(0,255,136,0.25)]' : ''
            }`}
        >
            {/* Pulse overlay when highlighted */}
            {highlight && (
                <motion.div
                    className="absolute inset-0 bg-cyber-success/5 pointer-events-none"
                    animate={{ opacity: [0.3, 0.6, 0.3] }}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                />
            )}
            <div className={`${color} opacity-80 flex-shrink-0 relative z-10`}>{icon}</div>
            <div className="min-w-0 relative z-10">
                <p className="text-cyber-muted text-xs font-display tracking-wider uppercase mb-0.5 truncate">{label}</p>
                <div className="flex items-baseline gap-1.5 flex-wrap">
                    <motion.span
                        key={value}
                        initial={{ scale: 1.3, color: '#00ff88' }}
                        animate={{ scale: 1, color: '' }}
                        transition={{ duration: 0.4 }}
                        className={`font-display text-xl font-bold ${color} truncate`}
                    >
                        {value}
                    </motion.span>
                    {sub && <span className="text-cyber-muted text-xs truncate">{sub}</span>}
                </div>
                {badge && (
                    <span className="mt-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-bold bg-cyber-success/20 text-cyber-success border border-cyber-success/40">
                        <Zap className="h-2.5 w-2.5" /> {badge}
                    </span>
                )}
            </div>
        </motion.div>
    );
}

export default function MetricsBar({ metrics }: { metrics: DashboardMetrics }) {
    const runs = metrics.demoRuns ?? 0;

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
                sub={`(${metrics.resolvedPct}%)`}
                color="text-cyber-success"
                delay={0.05}
                highlight={runs > 0}
                badge={runs > 0 ? `+${runs} from pipeline` : undefined}
            />
            <MetricCard
                icon={<Clock className="h-5 w-5" />}
                label="Avg Resolution"
                value={metrics.avgResTimeSec === '—' ? '—' : `${metrics.avgResTimeSec}s`}
                color="text-cyber-accent"
                delay={0.1}
                highlight={runs > 0}
            />
            <MetricCard
                icon={<DollarSign className="h-5 w-5" />}
                label="Total AI Cost"
                value={`$${metrics.totalCost}`}
                color="text-cyber-warning"
                delay={0.15}
                highlight={runs > 0}
                badge={runs > 0 ? `+$${(runs * 0.000934).toFixed(4)}` : undefined}
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
