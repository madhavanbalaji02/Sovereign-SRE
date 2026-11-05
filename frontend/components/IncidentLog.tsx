'use client';

import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, AlertCircle, ExternalLink, Activity, FileCode, Terminal, Check } from 'lucide-react';
import dynamic from 'next/dynamic';

const IncidentSparkline = dynamic(() => import('@/components/IncidentSparkline'), { ssr: false });

export interface SparkPoint { t: number; v: number; }

export interface Incident {
    incident_id: string;
    alarm_name: string;
    root_cause: string;
    proposed_fix?: string;
    confidence?: string;
    status: string;
    approval_status?: string;
    resolution_time_ms?: string;
    bedrock_model_used?: string;
    tokens_used?: string;
    cost_usd?: string;
    diff_preview?: string;
    timestamp?: string;
    // Real dataset fields
    source_dataset?: string;
    service?: string;
    anomaly_type?: string;
    severity?: string;
    duration_seconds?: string;
    metric_baseline?: string;
    metric_peak?: string;
    spike_ratio?: string;
    raw_log_line?: string;
    affected_containers?: string;
    timeseries?: SparkPoint[];
}

const STATUS_STYLE: Record<string, { label: string; cls: string }> = {
    resolved: { label: 'Resolved', cls: 'text-cyber-success bg-cyber-success/10 ring-cyber-success/25' },
    failed: { label: 'Failed', cls: 'text-cyber-error bg-cyber-error/10 ring-cyber-error/25' },
    open: { label: 'Open', cls: 'text-cyber-warning bg-cyber-warning/10 ring-cyber-warning/25' },
};

function StatusBadge({ status }: { status: string }) {
    const s = STATUS_STYLE[status] ?? { label: status.replace(/_/g, ' '), cls: 'text-cyber-warning bg-cyber-warning/10 ring-cyber-warning/25' };
    return (
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ring-1 whitespace-nowrap ${s.cls}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {s.label}
        </span>
    );
}

function DataSourceBadge({ source }: { source?: string }) {
    if (!source) return null;
    const isGaia = source === 'gaia';
    return (
        <a
            href={isGaia ? 'https://github.com/CloudWise-OpenSource/GAIA-DataSet' : 'https://github.com/MicroServo/dataset'}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-xs text-cyber-muted transition-colors hover:text-cyber-primary"
        >
            {isGaia ? 'GAIA (CloudWise)' : 'AIOpsArena'}
            <ExternalLink className="h-3 w-3" />
        </a>
    );
}

const TIMELINE_STEPS = ['Detected', 'Diagnosed', 'Fix generated', 'Approved', 'Resolved'];

function getTimelineActive(step: string, incident: Incident): boolean {
    if (step === 'Detected') return true;
    if (step === 'Diagnosed') return ['resolved', 'open', 'waiting_approval'].includes(incident.status);
    if (step === 'Fix generated') return ['resolved', 'waiting_approval'].includes(incident.status);
    if (step === 'Approved') return incident.status === 'resolved' && incident.approval_status === 'approved';
    if (step === 'Resolved') return incident.status === 'resolved';
    return false;
}

function DiffViewer({ diff }: { diff: string }) {
    return (
        <pre className="max-h-80 overflow-auto rounded-lg border border-cyber-border bg-cyber-dark py-2 font-mono text-xs leading-relaxed">
            {diff.split('\n').map((line, i) => {
                const tone = line.startsWith('+++') || line.startsWith('---')
                    ? 'text-cyber-text font-medium'
                    : line.startsWith('+')
                        ? 'text-cyber-success bg-cyber-success/[0.07]'
                        : line.startsWith('-')
                            ? 'text-cyber-error bg-cyber-error/[0.07]'
                            : line.startsWith('@@')
                                ? 'text-cyber-accent/80'
                                : 'text-cyber-muted';
                return <div key={i} className={`px-3 ${tone}`}>{line || ' '}</div>;
            })}
        </pre>
    );
}

function Section({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
    return (
        <div>
            <h4 className="eyebrow mb-2 flex items-center gap-1.5">{icon}{title}</h4>
            {children}
        </div>
    );
}

const isUuid = (id: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(id);
const ANOMALY_LABEL: Record<string, string> = {
    cpu_anomaly: 'CPU anomaly', memory_anomaly: 'Memory anomaly', network_delay: 'Network delay',
    pod_failure: 'Pod failure', disk_anomaly: 'Disk anomaly', io_anomaly: 'I/O anomaly',
};
const anomalyLabel = (t: string) => ANOMALY_LABEL[t] ?? t.replace(/_/g, ' ');
const shortId = (id: string) => (isUuid(id) ? `RUN-${id.slice(0, 8)}` : id);

type Filter = 'all' | 'open' | 'resolved' | 'failed';

export default function IncidentLog({ incidents }: { incidents: Incident[] }) {
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [showRawLog, setShowRawLog] = useState<string | null>(null);
    const [filter, setFilter] = useState<Filter>('all');

    const counts = useMemo(() => {
        const c: Record<Filter, number> = { all: incidents.length, open: 0, resolved: 0, failed: 0 };
        for (const i of incidents) {
            if (i.status === 'resolved') c.resolved++;
            else if (i.status === 'failed') c.failed++;
            else c.open++;
        }
        return c;
    }, [incidents]);

    const visible = incidents.filter(i =>
        filter === 'all' ? true
            : filter === 'open' ? !['resolved', 'failed'].includes(i.status)
                : i.status === filter,
    );

    if (incidents.length === 0) {
        return (
            <div className="rounded-lg border border-dashed border-cyber-border py-14 text-center">
                <AlertCircle className="mx-auto mb-3 h-8 w-8 text-cyber-subtle" />
                <p className="text-sm font-medium text-cyber-text">No incidents recorded</p>
                <p className="mt-1 text-xs text-cyber-muted">Run the live demo to see the system in action.</p>
            </div>
        );
    }

    return (
        <div>
            {/* Filters */}
            <div className="mb-3 flex flex-wrap gap-1.5" role="tablist" aria-label="Filter incidents">
                {(['all', 'open', 'resolved', 'failed'] as Filter[]).map(f => (
                    <button
                        key={f}
                        role="tab"
                        aria-selected={filter === f}
                        onClick={() => setFilter(f)}
                        className={`inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium capitalize transition-colors ${filter === f
                            ? 'bg-white/[0.08] text-cyber-text ring-1 ring-cyber-border'
                            : 'text-cyber-muted hover:bg-white/[0.04] hover:text-cyber-text'}`}
                    >
                        {f}
                        <span className="tabular text-cyber-subtle">{counts[f]}</span>
                    </button>
                ))}
            </div>

            <ul className="max-h-[44rem] divide-y divide-cyber-border overflow-y-auto rounded-lg border border-cyber-border">
                {visible.map((inc) => {
                    const isExpanded = expandedId === inc.incident_id;
                    const resTimeSec = inc.resolution_time_ms ? (Number(inc.resolution_time_ms) / 1000).toFixed(0) : null;
                    const confPct = inc.confidence ? `${Math.round(Number(inc.confidence) * 100)}%` : null;
                    const modelShort = inc.bedrock_model_used?.includes('haiku') ? 'Claude Haiku' : (inc.bedrock_model_used ?? '');
                    const atype = inc.anomaly_type ?? 'cpu_anomaly';
                    const baseline = inc.metric_baseline ? parseFloat(inc.metric_baseline) : undefined;
                    const peak = inc.metric_peak ? parseFloat(inc.metric_peak) : undefined;
                    const cost = inc.cost_usd && Number(inc.cost_usd) > 0 ? `$${Number(inc.cost_usd).toFixed(4)}` : null;

                    return (
                        <li key={inc.incident_id} className={isExpanded ? 'bg-white/[0.02]' : ''}>
                            <button
                                type="button"
                                aria-expanded={isExpanded}
                                onClick={() => setExpandedId(isExpanded ? null : inc.incident_id)}
                                className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.03]"
                            >
                                <ChevronRight className={`mt-0.5 h-4 w-4 flex-shrink-0 text-cyber-subtle transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                                <div className="min-w-0 flex-1">
                                    <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
                                        <StatusBadge status={inc.status} />
                                        <span className="font-mono text-xs font-medium text-cyber-text" title={inc.incident_id}>{shortId(inc.incident_id)}</span>
                                        <span className="text-xs text-cyber-muted">{anomalyLabel(atype)}</span>
                                        {inc.service && <span className="font-mono text-xs text-cyber-muted">· {inc.service}</span>}
                                    </div>
                                    <p className={`mt-1.5 line-clamp-1 text-sm ${inc.root_cause ? 'text-cyber-text/90' : 'italic text-cyber-subtle'}`}>
                                        {inc.root_cause || 'No root cause recorded for this pipeline run.'}
                                    </p>
                                </div>
                                <div className="hidden flex-shrink-0 flex-col items-end gap-1 text-xs tabular sm:flex">
                                    {confPct && <span className="text-cyber-text">{confPct} <span className="text-cyber-subtle">conf.</span></span>}
                                    <span className="text-cyber-muted">
                                        {[resTimeSec && `${resTimeSec}s`, cost].filter(Boolean).join(' · ') || '—'}
                                    </span>
                                </div>
                            </button>

                            <AnimatePresence initial={false}>
                                {isExpanded && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        transition={{ duration: 0.2 }}
                                        className="overflow-hidden"
                                    >
                                        <div className="space-y-5 px-4 pb-5 pl-11 pt-1">
                                            {/* Key facts */}
                                            <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-cyber-border bg-cyber-border sm:grid-cols-4">
                                                {[
                                                    ['Peak', peak != null ? `${peak.toFixed(1)}%` : '—'],
                                                    ['Duration', inc.duration_seconds ? `${inc.duration_seconds}s` : '—'],
                                                    ['Resolution', resTimeSec ? `${resTimeSec}s` : '—'],
                                                    ['Model', modelShort || '—'],
                                                ].map(([k, v]) => (
                                                    <div key={k} className="bg-cyber-dark px-3 py-2">
                                                        <dt className="text-[11px] text-cyber-muted">{k}</dt>
                                                        <dd className="mt-0.5 truncate text-sm font-medium text-cyber-text tabular">{v}</dd>
                                                    </div>
                                                ))}
                                            </dl>

                                            {inc.timeseries && inc.timeseries.length > 0 && (
                                                <Section title="Metric time series" icon={<Activity className="h-3.5 w-3.5" />}>
                                                    <div className="rounded-lg border border-cyber-border bg-cyber-dark p-2">
                                                        <IncidentSparkline data={inc.timeseries} anomalyType={atype} baseline={baseline} peak={peak} />
                                                        <p className="mt-1 text-center text-[11px] text-cyber-muted">
                                                            Relative time (min) · shaded region is the anomaly window
                                                            {baseline != null && peak != null && ` · baseline ${baseline.toFixed(1)}% → peak ${peak.toFixed(1)}%`}
                                                        </p>
                                                    </div>
                                                </Section>
                                            )}

                                            {inc.root_cause && (
                                                <Section title="Root cause">
                                                    <p className="text-sm leading-relaxed text-cyber-text/90">{inc.root_cause}</p>
                                                </Section>
                                            )}

                                            {inc.proposed_fix && (
                                                <Section title="Proposed fix">
                                                    <ul className="list-disc space-y-1 pl-4 text-sm leading-relaxed text-cyber-text/90 marker:text-cyber-subtle">
                                                        {inc.proposed_fix.split(/;\s+/).map((step, i) => <li key={i}>{step}</li>)}
                                                    </ul>
                                                </Section>
                                            )}

                                            {inc.diff_preview && (
                                                <Section title="Code diff" icon={<FileCode className="h-3.5 w-3.5" />}>
                                                    <DiffViewer diff={inc.diff_preview} />
                                                </Section>
                                            )}

                                            {inc.raw_log_line && (
                                                <div>
                                                    <button
                                                        className="eyebrow flex items-center gap-1.5 transition-colors hover:text-cyber-text"
                                                        onClick={() => setShowRawLog(showRawLog === inc.incident_id ? null : inc.incident_id)}
                                                    >
                                                        <Terminal className="h-3.5 w-3.5" />
                                                        Raw log line
                                                        <ChevronRight className={`h-3 w-3 transition-transform ${showRawLog === inc.incident_id ? 'rotate-90' : ''}`} />
                                                    </button>
                                                    {showRawLog === inc.incident_id && (
                                                        <pre className="mt-2 whitespace-pre-wrap break-all rounded-lg border border-cyber-border bg-cyber-dark p-3 font-mono text-xs text-cyber-muted">
                                                            {inc.raw_log_line}
                                                        </pre>
                                                    )}
                                                </div>
                                            )}

                                            <Section title="Timeline">
                                                <ol className="flex flex-wrap items-center gap-1">
                                                    {TIMELINE_STEPS.map((step, i) => {
                                                        const active = getTimelineActive(step, inc);
                                                        return (
                                                            <li key={step} className="flex items-center gap-1">
                                                                {i > 0 && <span className={`h-px w-4 ${active ? 'bg-cyber-success/50' : 'bg-cyber-border'}`} />}
                                                                <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs ring-1 ${active
                                                                    ? 'text-cyber-success bg-cyber-success/10 ring-cyber-success/25'
                                                                    : 'text-cyber-subtle ring-cyber-border'}`}>
                                                                    {active && <Check className="h-3 w-3" />}
                                                                    {step}
                                                                </span>
                                                            </li>
                                                        );
                                                    })}
                                                </ol>
                                            </Section>

                                            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-t border-cyber-border pt-3 text-xs text-cyber-muted">
                                                {inc.bedrock_model_used && <span>Model <span className="font-mono text-cyber-text">{inc.bedrock_model_used}</span></span>}
                                                {inc.tokens_used && Number(inc.tokens_used) > 0 && <span>Tokens <span className="text-cyber-text tabular">{inc.tokens_used}</span></span>}
                                                {cost && <span>Cost <span className="text-cyber-text tabular">{cost}</span></span>}
                                                {inc.affected_containers && <span>Containers <span className="font-mono text-cyber-text">{inc.affected_containers}</span></span>}
                                                {inc.source_dataset && <span className="flex items-center gap-1.5">Source <DataSourceBadge source={inc.source_dataset} /></span>}
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </li>
                    );
                })}
                {visible.length === 0 && (
                    <li className="px-4 py-10 text-center text-sm text-cyber-muted">No {filter} incidents.</li>
                )}
            </ul>
        </div>
    );
}
