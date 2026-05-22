'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ChevronDown, ChevronRight, Clock, DollarSign, Cpu, Target,
    AlertCircle, ExternalLink, Activity, FileCode, Terminal,
} from 'lucide-react';
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

function StatusBadge({ status }: { status: string }) {
    if (status === 'resolved') {
        return (
            <span className="px-2 py-0.5 rounded-full text-xs font-display font-bold bg-cyber-success/20 text-cyber-success border border-cyber-success/40 whitespace-nowrap">
                RESOLVED ✓
            </span>
        );
    }
    if (status === 'failed') {
        return (
            <span className="px-2 py-0.5 rounded-full text-xs font-display font-bold bg-cyber-error/20 text-cyber-error border border-cyber-error/40 whitespace-nowrap">
                FAILED
            </span>
        );
    }
    return (
        <motion.span
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ repeat: Infinity, duration: 2 }}
            className="px-2 py-0.5 rounded-full text-xs font-display font-bold bg-cyber-warning/20 text-cyber-warning border border-cyber-warning/40 whitespace-nowrap"
        >
            OPEN
        </motion.span>
    );
}

function SeverityBadge({ severity }: { severity?: string }) {
    if (!severity) return null;
    const colors: Record<string, string> = {
        high: 'text-cyber-error border-cyber-error/40 bg-cyber-error/10',
        medium: 'text-cyber-warning border-cyber-warning/40 bg-cyber-warning/10',
        low: 'text-cyber-success border-cyber-success/40 bg-cyber-success/10',
    };
    return (
        <span className={`px-1.5 py-0.5 rounded text-xs font-display border uppercase ${colors[severity] ?? colors.low}`}>
            {severity}
        </span>
    );
}

function DataSourceBadge({ source }: { source?: string }) {
    if (!source) return null;
    const isGaia = source === 'gaia';
    return (
        <a
            href={isGaia
                ? 'https://github.com/CloudWise-OpenSource/GAIA-DataSet'
                : 'https://github.com/MicroServo/dataset'}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="flex items-center gap-1 text-xs text-cyber-muted hover:text-cyber-primary transition-colors"
        >
            <ExternalLink className="h-2.5 w-2.5" />
            Data: {isGaia ? 'GAIA (CloudWise)' : 'AIOpsArena'}
        </a>
    );
}

const TIMELINE_STEPS = ['Detected', 'Diagnosed', 'Fix Generated', 'Approved', 'Resolved'];

function getTimelineActive(step: string, incident: Incident): boolean {
    if (step === 'Detected') return true;
    if (step === 'Diagnosed') return ['resolved', 'open', 'waiting_approval'].includes(incident.status);
    if (step === 'Fix Generated') return ['resolved', 'waiting_approval'].includes(incident.status);
    if (step === 'Approved') return incident.status === 'resolved' && incident.approval_status === 'approved';
    if (step === 'Resolved') return incident.status === 'resolved';
    return false;
}

function DiffViewer({ diff }: { diff: string }) {
    return (
        <div className="bg-cyber-black/70 rounded border border-cyber-muted/20 p-3 overflow-x-auto">
            <pre className="text-xs font-mono">
                {diff.split('\n').map((line, i) => (
                    <div
                        key={i}
                        className={
                            line.startsWith('+++') ? 'text-cyber-primary' :
                                line.startsWith('---') ? 'text-cyber-error' :
                                    line.startsWith('+') ? 'text-cyber-success' :
                                        line.startsWith('-') ? 'text-cyber-error' :
                                            line.startsWith('@@') ? 'text-cyber-accent' :
                                                'text-gray-500'
                        }
                    >
                        {line || ' '}
                    </div>
                ))}
            </pre>
        </div>
    );
}

export default function IncidentLog({ incidents }: { incidents: Incident[] }) {
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [showRawLog, setShowRawLog] = useState<string | null>(null);

    if (incidents.length === 0) {
        return (
            <div className="text-center py-16 text-cyber-muted">
                <AlertCircle className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p className="font-display text-sm">No incidents recorded</p>
                <p className="text-xs mt-2 opacity-60">Click ▶ Run Live Demo to see the system in action</p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {incidents.map((inc) => {
                const isExpanded = expandedId === inc.incident_id;
                const resTimeSec = inc.resolution_time_ms
                    ? (Number(inc.resolution_time_ms) / 1000).toFixed(1)
                    : null;
                const confPct = inc.confidence
                    ? `${Math.round(Number(inc.confidence) * 100)}%`
                    : null;
                const modelShort = inc.bedrock_model_used?.includes('haiku')
                    ? 'Claude Haiku'
                    : (inc.bedrock_model_used ?? '');
                const isReal = inc.incident_id?.startsWith('REAL-');
                const atype = inc.anomaly_type ?? 'cpu_anomaly';
                const baseline = inc.metric_baseline ? parseFloat(inc.metric_baseline) : undefined;
                const peak = inc.metric_peak ? parseFloat(inc.metric_peak) : undefined;

                return (
                    <motion.div
                        key={inc.incident_id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`cyber-card border transition-all cursor-pointer ${isReal
                            ? 'border-cyber-primary/30 hover:border-cyber-primary/60'
                            : 'border-cyber-muted/30 hover:border-cyber-primary/50'
                            }`}
                        onClick={() => setExpandedId(isExpanded ? null : inc.incident_id)}
                    >
                        <div className="p-4">
                            {/* Header row */}
                            <div className="flex items-start gap-3">
                                <div className="flex-shrink-0 pt-0.5 text-cyber-muted">
                                    {isExpanded
                                        ? <ChevronDown className="h-4 w-4" />
                                        : <ChevronRight className="h-4 w-4" />
                                    }
                                </div>
                                <div className="flex-grow min-w-0">
                                    {/* ID row */}
                                    <div className="flex items-center gap-2 flex-wrap mb-1">
                                        <StatusBadge status={inc.status} />
                                        <span className="font-display text-xs text-cyber-primary font-bold">{inc.incident_id}</span>
                                        <span className="font-mono text-xs text-cyber-accent">{atype.replace(/_/g, ' ')}</span>
                                        {inc.severity && <SeverityBadge severity={inc.severity} />}
                                    </div>

                                    {/* Service · duration · confidence · cost */}
                                    <div className="flex items-center gap-3 flex-wrap mb-2 text-xs text-cyber-muted">
                                        {inc.service && (
                                            <span className="font-mono text-cyber-secondary">{inc.service}</span>
                                        )}
                                        {inc.duration_seconds && (
                                            <span>{inc.duration_seconds}s duration</span>
                                        )}
                                        {confPct && (
                                            <span className="text-cyber-success font-bold">confidence {confPct}</span>
                                        )}
                                        {inc.cost_usd && Number(inc.cost_usd) > 0 && (
                                            <span className="text-cyber-warning">${inc.cost_usd}</span>
                                        )}
                                    </div>

                                    {/* Root cause preview */}
                                    <p className="text-sm text-gray-300 truncate">
                                        {(inc.root_cause ?? '').slice(0, 110)}{(inc.root_cause ?? '').length > 110 ? '…' : ''}
                                    </p>

                                    {/* Bottom meta row */}
                                    <div className="flex items-center justify-between mt-2 flex-wrap gap-2">
                                        <div className="flex items-center gap-3 flex-wrap">
                                            {resTimeSec && (
                                                <span className="flex items-center gap-1 text-xs text-cyber-muted">
                                                    <Clock className="h-3 w-3" />
                                                    <span className="text-cyber-primary font-bold">{resTimeSec}s</span>
                                                </span>
                                            )}
                                            {peak != null && (
                                                <span className="flex items-center gap-1 text-xs text-cyber-muted">
                                                    <Activity className="h-3 w-3" />
                                                    peak <span className="text-cyber-error font-bold ml-1">{peak.toFixed(1)}%</span>
                                                </span>
                                            )}
                                            {modelShort && (
                                                <span className="flex items-center gap-1 text-xs text-cyber-muted">
                                                    <Cpu className="h-3 w-3" />
                                                    <span className="text-cyber-secondary">{modelShort}</span>
                                                </span>
                                            )}
                                        </div>
                                        <DataSourceBadge source={inc.source_dataset} />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Expanded section */}
                        <AnimatePresence>
                            {isExpanded && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                >
                                    <div className="px-4 pb-5 border-t border-cyber-muted/20 pt-4 space-y-5">

                                        {/* Sparkline */}
                                        {inc.timeseries && inc.timeseries.length > 0 && (
                                            <div>
                                                <h4 className="font-display text-xs text-cyber-primary mb-2 tracking-widest flex items-center gap-2">
                                                    <Activity className="h-3.5 w-3.5" />
                                                    METRIC TIME SERIES
                                                    <span className="text-cyber-muted font-mono normal-case tracking-normal">
                                                        (baseline {baseline?.toFixed(1)}% → peak {peak?.toFixed(1)}%)
                                                    </span>
                                                </h4>
                                                <div
                                                    className="rounded border border-cyber-muted/10 bg-cyber-black/40 p-2"
                                                    onClick={e => e.stopPropagation()}
                                                >
                                                    <IncidentSparkline
                                                        data={inc.timeseries}
                                                        anomalyType={atype}
                                                        baseline={baseline}
                                                        peak={peak}
                                                    />
                                                    <p className="text-xs text-cyber-muted text-center mt-1">
                                                        X-axis: relative time (min) · Red region = anomaly window · ✓ = recovery
                                                    </p>
                                                </div>
                                            </div>
                                        )}

                                        {/* Root cause */}
                                        <div>
                                            <h4 className="font-display text-xs text-cyber-secondary mb-1.5 tracking-widest">ROOT CAUSE</h4>
                                            <p className="text-sm text-gray-300 leading-relaxed">{inc.root_cause}</p>
                                        </div>

                                        {/* Proposed fix */}
                                        {inc.proposed_fix && (
                                            <div>
                                                <h4 className="font-display text-xs text-cyber-success mb-1.5 tracking-widest">PROPOSED FIX</h4>
                                                <p className="text-sm text-gray-300 leading-relaxed">{inc.proposed_fix}</p>
                                            </div>
                                        )}

                                        {/* Code diff */}
                                        {inc.diff_preview && (
                                            <div>
                                                <h4 className="font-display text-xs text-cyber-accent mb-1.5 tracking-widest flex items-center gap-2">
                                                    <FileCode className="h-3.5 w-3.5" />
                                                    CODE DIFF
                                                </h4>
                                                <DiffViewer diff={inc.diff_preview} />
                                            </div>
                                        )}

                                        {/* Raw log line (collapsible) */}
                                        {inc.raw_log_line && (
                                            <div>
                                                <button
                                                    className="flex items-center gap-2 font-display text-xs text-cyber-muted hover:text-cyber-primary transition-colors tracking-widest"
                                                    onClick={e => {
                                                        e.stopPropagation();
                                                        setShowRawLog(showRawLog === inc.incident_id ? null : inc.incident_id);
                                                    }}
                                                >
                                                    <Terminal className="h-3.5 w-3.5" />
                                                    RAW LOG LINE
                                                    {showRawLog === inc.incident_id
                                                        ? <ChevronDown className="h-3 w-3" />
                                                        : <ChevronRight className="h-3 w-3" />}
                                                </button>
                                                <AnimatePresence>
                                                    {showRawLog === inc.incident_id && (
                                                        <motion.div
                                                            initial={{ height: 0, opacity: 0 }}
                                                            animate={{ height: 'auto', opacity: 1 }}
                                                            exit={{ height: 0, opacity: 0 }}
                                                            className="overflow-hidden"
                                                        >
                                                            <pre className="mt-2 text-xs font-mono text-gray-400 bg-cyber-black/70 rounded border border-cyber-muted/20 p-3 whitespace-pre-wrap break-all">
                                                                {inc.raw_log_line}
                                                            </pre>
                                                        </motion.div>
                                                    )}
                                                </AnimatePresence>
                                            </div>
                                        )}

                                        {/* Timeline */}
                                        <div>
                                            <h4 className="font-display text-xs text-cyber-primary mb-2 tracking-widest">TIMELINE</h4>
                                            <div className="flex items-center gap-1 overflow-x-auto pb-1">
                                                {TIMELINE_STEPS.map((step, i) => {
                                                    const active = getTimelineActive(step, inc);
                                                    return (
                                                        <div key={step} className="flex items-center gap-1 flex-shrink-0">
                                                            {i > 0 && (
                                                                <div className={`w-6 h-px ${active ? 'bg-cyber-success' : 'bg-cyber-muted/40'}`} />
                                                            )}
                                                            <span className={`text-xs px-2 py-0.5 rounded border whitespace-nowrap ${active
                                                                ? 'text-cyber-success border-cyber-success/40 bg-cyber-success/10'
                                                                : 'text-cyber-muted border-cyber-muted/20'
                                                                }`}>
                                                                {step}
                                                            </span>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>

                                        {/* Model / tokens / cost */}
                                        {inc.bedrock_model_used && (
                                            <div className="flex gap-6 text-xs flex-wrap">
                                                <div>
                                                    <span className="text-cyber-muted">Model: </span>
                                                    <span className="text-cyber-secondary font-mono">{inc.bedrock_model_used}</span>
                                                </div>
                                                {inc.tokens_used && Number(inc.tokens_used) > 0 && (
                                                    <div>
                                                        <span className="text-cyber-muted">Tokens: </span>
                                                        <span className="text-cyber-primary font-bold">{inc.tokens_used}</span>
                                                    </div>
                                                )}
                                                {inc.cost_usd && Number(inc.cost_usd) > 0 && (
                                                    <div>
                                                        <span className="text-cyber-muted">Cost: </span>
                                                        <span className="text-cyber-warning font-bold">${inc.cost_usd}</span>
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Data source attribution */}
                                        {inc.source_dataset && (
                                            <div className="flex items-center gap-2 pt-1 border-t border-cyber-muted/10">
                                                <span className="text-xs text-cyber-muted">Source:</span>
                                                <DataSourceBadge source={inc.source_dataset} />
                                                {inc.affected_containers && (
                                                    <span className="text-xs text-cyber-muted">
                                                        · Containers: <span className="text-cyber-secondary font-mono">{inc.affected_containers}</span>
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                );
            })}
        </div>
    );
}
