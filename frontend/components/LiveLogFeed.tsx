'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Zap, Activity } from 'lucide-react';

interface LogLine {
    timestamp: string;
    service: string;
    level: string;
    anomaly_type?: string;
    message: string;
    is_anomaly: boolean;
    anomaly_confidence?: number;
    source?: string;
}

interface Stats {
    lines_processed?: number;
    anomalies_detected?: number;
    normal_lines_filtered?: number;
    token_savings_pct?: number;
}

const LEVEL_COLOR: Record<string, string> = {
    ERROR: 'text-red-400',
    CRITICAL: 'text-red-500 font-bold',
    FATAL: 'text-red-600 font-bold',
    WARNING: 'text-yellow-400',
    WARN: 'text-yellow-400',
    INFO: 'text-green-700',
    DEBUG: 'text-gray-600',
};

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? '';

export default function LiveLogFeed() {
    const [logs, setLogs] = useState<LogLine[]>([]);
    const [stats, setStats] = useState<Stats>({});
    const [anomalyFlash, setAnomalyFlash] = useState(false);
    const [connected, setConnected] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Poll /api/logs/latest every 2s (SSE fallback)
    useEffect(() => {
        if (!BACKEND) return;

        const poll = async () => {
            try {
                const r = await fetch(`${BACKEND}/api/logs/latest?n=20`, { signal: AbortSignal.timeout(3000) });
                if (!r.ok) return;
                const data = await r.json();
                const newLogs: LogLine[] = data.logs ?? [];
                setStats(data.stats ?? {});
                setConnected(true);
                if (newLogs.length > 0) {
                    setLogs(prev => {
                        const combined = [...prev, ...newLogs].slice(-50);
                        return combined;
                    });
                    const hasAnomaly = newLogs.some(l => l.is_anomaly);
                    if (hasAnomaly) {
                        setAnomalyFlash(true);
                        setTimeout(() => setAnomalyFlash(false), 1500);
                    }
                }
            } catch {
                setConnected(false);
            }
        };

        poll();
        pollRef.current = setInterval(poll, 2000);
        return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }, []);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const anomalyCount = stats.anomalies_detected ?? 0;
    const processed = stats.lines_processed ?? 0;
    const filtered = stats.normal_lines_filtered ?? 0;
    const savings = stats.token_savings_pct ?? 0;

    return (
        <div className="cyber-card p-4 h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-cyber-accent" />
                    <span className="font-display text-sm text-cyber-accent">GAIA Log Stream</span>
                    <span className={`w-2 h-2 rounded-full ${connected ? 'bg-cyber-success animate-pulse' : 'bg-cyber-muted'}`} />
                </div>
                <div className="flex items-center gap-3 text-xs text-cyber-muted font-mono">
                    {processed > 0 && (
                        <>
                            <span>{processed.toLocaleString()} processed</span>
                            <span className="text-cyber-error">{anomalyCount} anomalies</span>
                            <span className="text-cyber-success">{savings.toFixed(0)}% filtered</span>
                        </>
                    )}
                </div>
            </div>

            {/* Anomaly flash overlay */}
            <AnimatePresence>
                {anomalyFlash && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 border-2 border-cyber-error/60 rounded pointer-events-none z-10 flex items-start justify-end p-2"
                    >
                        <span className="flex items-center gap-1 text-xs font-bold text-cyber-error bg-cyber-darker px-2 py-1 rounded">
                            <Zap className="h-3 w-3" /> Pipeline triggered
                        </span>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Log lines */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto font-mono text-xs space-y-0.5 bg-cyber-black/60 rounded border border-cyber-muted/10 p-2"
                style={{ minHeight: 160 }}
            >
                {logs.length === 0 ? (
                    <div className="text-cyber-muted text-center py-6">
                        {connected ? 'Waiting for log lines...' : `Connect backend at ${BACKEND || 'NEXT_PUBLIC_BACKEND_URL'} to stream logs`}
                    </div>
                ) : (
                    logs.map((log, i) => (
                        <div
                            key={i}
                            className={`flex gap-2 leading-5 ${log.is_anomaly ? 'bg-cyber-error/5 rounded px-1' : ''}`}
                        >
                            <span className="text-cyber-muted flex-shrink-0 w-5 text-right">{i + 1}</span>
                            <span className={`flex-shrink-0 w-16 ${LEVEL_COLOR[log.level] ?? 'text-gray-500'}`}>
                                {log.level}
                            </span>
                            <span className="text-cyber-secondary flex-shrink-0 w-24 truncate">
                                {log.service}
                            </span>
                            <span className="text-gray-400 truncate flex-1">
                                {log.message.slice(0, 120)}
                            </span>
                            {log.is_anomaly && (
                                <span className="flex-shrink-0 text-cyber-error">⚠</span>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Footer stats */}
            <div className="mt-2 flex gap-4 text-xs text-cyber-muted font-mono">
                <span><Activity className="h-3 w-3 inline mr-1" />{processed} lines</span>
                <span className="text-cyber-error">{anomalyCount} anomalies</span>
                <span className="text-green-700">{filtered} filtered ({savings.toFixed(0)}% savings)</span>
            </div>
        </div>
    );
}
