'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, Clock, DollarSign, Cpu, Target, AlertCircle } from 'lucide-react';

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
}

function StatusBadge({ status }: { status: string }) {
    if (status === 'resolved') {
        return (
            <span className="px-2 py-0.5 rounded-full text-xs font-display font-bold bg-cyber-success/20 text-cyber-success border border-cyber-success/40 whitespace-nowrap">
                RESOLVED
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

const TIMELINE_STEPS = ['Detected', 'Diagnosed', 'Fix Generated', 'Approved', 'Resolved'];

function getTimelineActive(step: string, incident: Incident): boolean {
    if (step === 'Detected') return true;
    if (step === 'Diagnosed') return ['resolved', 'open', 'waiting_approval'].includes(incident.status);
    if (step === 'Fix Generated') return ['resolved', 'waiting_approval'].includes(incident.status);
    if (step === 'Approved') return incident.status === 'resolved' && incident.approval_status === 'approved';
    if (step === 'Resolved') return incident.status === 'resolved';
    return false;
}

export default function IncidentLog({ incidents }: { incidents: Incident[] }) {
    const [expandedId, setExpandedId] = useState<string | null>(null);

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

                return (
                    <motion.div
                        key={inc.incident_id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="cyber-card border border-cyber-muted/30 hover:border-cyber-primary/50 transition-all cursor-pointer"
                        onClick={() => setExpandedId(isExpanded ? null : inc.incident_id)}
                    >
                        <div className="p-4">
                            <div className="flex items-start gap-3">
                                <div className="flex-shrink-0 pt-0.5 text-cyber-muted">
                                    {isExpanded
                                        ? <ChevronDown className="h-4 w-4" />
                                        : <ChevronRight className="h-4 w-4" />
                                    }
                                </div>
                                <div className="flex-grow min-w-0">
                                    <div className="flex items-center gap-3 flex-wrap mb-1.5">
                                        <StatusBadge status={inc.status} />
                                        <span className="font-display text-xs text-cyber-primary font-bold">{inc.incident_id}</span>
                                        <span className="font-mono text-xs text-cyber-accent truncate max-w-[240px]">{inc.alarm_name}</span>
                                    </div>
                                    <p className="text-sm text-gray-300 mb-2 truncate">
                                        {(inc.root_cause ?? '').slice(0, 100)}{(inc.root_cause ?? '').length > 100 ? '…' : ''}
                                    </p>
                                    <div className="flex items-center gap-4 flex-wrap">
                                        {confPct && (
                                            <span className="flex items-center gap-1 text-xs text-cyber-muted">
                                                <Target className="h-3 w-3" />
                                                Confidence: <span className="text-cyber-success font-bold ml-1">{confPct}</span>
                                            </span>
                                        )}
                                        {resTimeSec && (
                                            <span className="flex items-center gap-1 text-xs text-cyber-muted">
                                                <Clock className="h-3 w-3" />
                                                Resolution: <span className="text-cyber-primary font-bold ml-1">{resTimeSec}s</span>
                                            </span>
                                        )}
                                        {inc.cost_usd && (
                                            <span className="flex items-center gap-1 text-xs text-cyber-muted">
                                                <DollarSign className="h-3 w-3" />
                                                Cost: <span className="text-cyber-warning font-bold ml-1">${inc.cost_usd}</span>
                                            </span>
                                        )}
                                        {modelShort && (
                                            <span className="flex items-center gap-1 text-xs text-cyber-muted">
                                                <Cpu className="h-3 w-3" />
                                                <span className="text-cyber-secondary ml-1">{modelShort}</span>
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <AnimatePresence>
                            {isExpanded && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                >
                                    <div className="px-4 pb-5 border-t border-cyber-muted/20 pt-4 space-y-5">
                                        <div>
                                            <h4 className="font-display text-xs text-cyber-secondary mb-1.5 tracking-widest">ROOT CAUSE</h4>
                                            <p className="text-sm text-gray-300 leading-relaxed">{inc.root_cause}</p>
                                        </div>

                                        {inc.proposed_fix && (
                                            <div>
                                                <h4 className="font-display text-xs text-cyber-success mb-1.5 tracking-widest">PROPOSED FIX</h4>
                                                <p className="text-sm text-gray-300 leading-relaxed">{inc.proposed_fix}</p>
                                            </div>
                                        )}

                                        {inc.diff_preview && (
                                            <div>
                                                <h4 className="font-display text-xs text-cyber-accent mb-1.5 tracking-widest">CODE DIFF</h4>
                                                <div className="bg-cyber-black/70 rounded border border-cyber-muted/20 p-3 overflow-x-auto">
                                                    <pre className="text-xs font-mono">
                                                        {inc.diff_preview.split('\n').map((line, i) => (
                                                            <div
                                                                key={i}
                                                                className={
                                                                    line.startsWith('+') ? 'text-cyber-success' :
                                                                        line.startsWith('-') ? 'text-cyber-error' :
                                                                            'text-gray-400'
                                                                }
                                                            >
                                                                {line || ' '}
                                                            </div>
                                                        ))}
                                                    </pre>
                                                </div>
                                            </div>
                                        )}

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

                                        {inc.bedrock_model_used && (
                                            <div className="flex gap-6 text-xs flex-wrap">
                                                <div>
                                                    <span className="text-cyber-muted">Model: </span>
                                                    <span className="text-cyber-secondary font-mono">{inc.bedrock_model_used}</span>
                                                </div>
                                                {inc.tokens_used && (
                                                    <div>
                                                        <span className="text-cyber-muted">Tokens: </span>
                                                        <span className="text-cyber-primary font-bold">{inc.tokens_used}</span>
                                                    </div>
                                                )}
                                                {inc.cost_usd && (
                                                    <div>
                                                        <span className="text-cyber-muted">Cost: </span>
                                                        <span className="text-cyber-warning font-bold">${inc.cost_usd}</span>
                                                    </div>
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
