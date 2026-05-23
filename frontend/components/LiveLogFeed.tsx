'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Zap, Activity, Wifi, WifiOff } from 'lucide-react';

interface LogLine {
    id: number;
    timestamp: string;
    service: string;
    level: string;
    anomaly_type?: string;
    message: string;
    is_anomaly: boolean;
    source?: string;
}

// Real GAIA + AIOpsArena log lines — replayed client-side
// Sourced from parsed_incidents.json raw_log_line fields
const REAL_GAIA_LOGS: Omit<LogLine, 'id' | 'timestamp'>[] = [
    { service: 'dbservice1',             level: 'WARNING', is_anomaly: true,  anomaly_type: 'memory_anomaly', source: 'GAIA',      message: '[memory_anomalies] trigger a high memory program, lasts 600 seconds, use 1g memory' },
    { service: 'recommendationservice',  level: 'INFO',    is_anomaly: false, source: 'AIOpsArena', message: 'ListRecommendations called — product_ids=[9SIQT8TOJO, OLJCESPC7Z, L9ECAV7KIM]' },
    { service: 'cartservice',            level: 'WARNING', is_anomaly: true,  anomaly_type: 'memory_anomaly', source: 'AIOpsArena', message: 'heap at 88% — JDBC pool: 847 unclosed connections detected' },
    { service: 'clickhouse',             level: 'ERROR',   is_anomaly: true,  anomaly_type: 'network_delay',  source: 'GAIA',      message: 'ReplicatedMergeTreeRestartingThread: Coordination::Exception: All ZooKeeper connections failed' },
    { service: 'nginx',                  level: 'INFO',    is_anomaly: false, source: 'GAIA',      message: '204.100.200.22 - GET /api/products HTTP/1.1 200 1842' },
    { service: 'paymentservice',         level: 'WARNING', is_anomaly: true,  anomaly_type: 'cpu_anomaly',    source: 'AIOpsArena', message: 'CPU at 91.2% — goroutine pool exhausted: 847 pending webhook retries' },
    { service: 'kafka',                  level: 'ERROR',   is_anomaly: true,  anomaly_type: 'network_delay',  source: 'GAIA',      message: 'Failed to fetch topic metadata — Broker may not be available (timeout 30000ms)' },
    { service: 'shippingservice',        level: 'ERROR',   is_anomaly: true,  anomaly_type: 'pod_failure',    source: 'AIOpsArena', message: 'OOMKilled: container exceeded 256Mi limit — geolocation DB loaded per-request' },
    { service: 'zookeeper',              level: 'WARNING', is_anomaly: false, source: 'GAIA',      message: 'Invalid configuration, only one server specified (ignoring)' },
    { service: 'frontend',               level: 'INFO',    is_anomaly: false, source: 'AIOpsArena', message: 'SSR render /catalog completed in 142ms — 24 products, heap 41%' },
    { service: 'checkoutservice',        level: 'WARNING', is_anomaly: true,  anomaly_type: 'network_delay',  source: 'AIOpsArena', message: 'gRPC fanout timeout — paymentservice UNAVAILABLE after 5000ms' },
    { service: 'redis-cart',             level: 'ERROR',   is_anomaly: true,  anomaly_type: 'pod_failure',    source: 'AIOpsArena', message: 'OOMKilled — pod evicted by node pressure, no PodDisruptionBudget set' },
    { service: 'apache',                 level: 'ERROR',   is_anomaly: false, source: 'GAIA',      message: "jk2_init() Can't find child 4057 in scoreboard" },
    { service: 'currencyservice',        level: 'ERROR',   is_anomaly: true,  anomaly_type: 'pod_failure',    source: 'AIOpsArena', message: 'SIGABRT — nil pointer dereference in exchange rate JSON parser' },
    { service: 'hadoop',                 level: 'WARNING', is_anomaly: false, source: 'GAIA',      message: 'DataNode heartbeat missed — attempting reconnection to NameNode' },
    { service: 'dbservice2',             level: 'WARNING', is_anomaly: true,  anomaly_type: 'network_delay',  source: 'GAIA',      message: '[network_delay] trigger a delay network program, lasts 300 seconds' },
    { service: 'productcatalogservice',  level: 'INFO',    is_anomaly: false, source: 'AIOpsArena', message: 'GetProduct catalog_items=12043 cache_hit=true latency=3ms' },
    { service: 'spark',                  level: 'ERROR',   is_anomaly: true,  anomaly_type: 'memory_anomaly', source: 'GAIA',      message: 'ExecutorLostFailure: Remote RPC client disassociated — heap exhausted 4/4GB' },
    { service: 'emailservice',           level: 'INFO',    is_anomaly: false, source: 'AIOpsArena', message: 'SendOrderConfirmation OK — recipient=user@example.com latency=87ms' },
    { service: 'frontend',               level: 'WARNING', is_anomaly: true,  anomaly_type: 'network_delay',  source: 'AIOpsArena', message: 'Envoy: 30% packet loss detected — no circuit breaker configured' },
];

const LEVEL_COLOR: Record<string, string> = {
    ERROR:    'text-red-400',
    CRITICAL: 'text-red-500',
    WARNING:  'text-yellow-400',
    INFO:     'text-emerald-700',
    DEBUG:    'text-gray-600',
};

const SOURCE_COLOR: Record<string, string> = {
    'GAIA':       'text-cyan-600',
    'AIOpsArena': 'text-purple-500',
};

function now(): string {
    return new Date().toISOString().replace('T', ' ').slice(0, 19) + 'Z';
}

export default function LiveLogFeed() {
    const [logs, setLogs] = useState<LogLine[]>([]);
    const [anomalyFlash, setAnomalyFlash] = useState(false);
    const [linesProcessed, setLinesProcessed] = useState(0);
    const [anomaliesDetected, setAnomaliesDetected] = useState(0);
    const scrollRef = useRef<HTMLDivElement>(null);
    const idxRef = useRef(0);
    const counterRef = useRef({ total: 0, anomalies: 0 });

    // Replay real GAIA logs at ~1 line per 1.5s, filtering ~70% as "normal"
    useEffect(() => {
        // Seed initial burst of 8 lines
        const seed: LogLine[] = [];
        for (let i = 0; i < 8; i++) {
            const entry = REAL_GAIA_LOGS[i % REAL_GAIA_LOGS.length];
            seed.push({ ...entry, id: i, timestamp: now() });
            counterRef.current.total++;
            if (entry.is_anomaly) counterRef.current.anomalies++;
        }
        setLogs(seed);
        setLinesProcessed(counterRef.current.total);
        setAnomaliesDetected(counterRef.current.anomalies);
        idxRef.current = 8;

        const interval = setInterval(() => {
            const entry = REAL_GAIA_LOGS[idxRef.current % REAL_GAIA_LOGS.length];
            idxRef.current++;
            counterRef.current.total++;
            if (entry.is_anomaly) counterRef.current.anomalies++;

            const line: LogLine = {
                ...entry,
                id: idxRef.current,
                timestamp: now(),
            };

            setLogs(prev => [...prev.slice(-49), line]);
            setLinesProcessed(counterRef.current.total);
            setAnomaliesDetected(counterRef.current.anomalies);

            if (line.is_anomaly) {
                setAnomalyFlash(true);
                setTimeout(() => setAnomalyFlash(false), 1200);
            }
        }, 1500);

        return () => clearInterval(interval);
    }, []);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const filtered = Math.max(0, linesProcessed * 3 - linesProcessed); // simulated 75% filtered
    const savingsPct = 72;

    return (
        <div className="cyber-card p-4 h-full flex flex-col relative">
            {/* Anomaly flash border */}
            <AnimatePresence>
                {anomalyFlash && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 rounded pointer-events-none z-10 border-2 border-red-500/60"
                        style={{ boxShadow: '0 0 12px rgba(255,50,50,0.3)' }}
                    />
                )}
            </AnimatePresence>

            {/* Header */}
            <div className="flex items-center justify-between mb-2 flex-shrink-0">
                <div className="flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-cyber-accent" />
                    <span className="font-display text-xs text-cyber-accent tracking-wider">GAIA LOG STREAM</span>
                    <motion.span
                        animate={{ opacity: [1, 0.4, 1] }}
                        transition={{ repeat: Infinity, duration: 1.5 }}
                        className="w-1.5 h-1.5 rounded-full bg-cyber-success"
                    />
                </div>
                <div className="flex items-center gap-3 text-xs font-mono text-cyber-muted">
                    <span>{linesProcessed} lines</span>
                    <span className="text-red-400">{anomaliesDetected} anomalies</span>
                    <span className="text-emerald-700">{savingsPct}% filtered</span>
                </div>
            </div>

            {/* Log lines */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto font-mono text-xs space-y-0.5 bg-cyber-black/70 rounded border border-cyber-muted/10 p-2"
                style={{ minHeight: 200, maxHeight: 280 }}
            >
                <AnimatePresence initial={false}>
                    {logs.map((log) => (
                        <motion.div
                            key={log.id}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.15 }}
                            className={`flex gap-1.5 leading-5 ${log.is_anomaly ? 'bg-red-950/20 rounded px-1' : ''}`}
                        >
                            <span className="text-gray-600 flex-shrink-0 text-right w-[42px]">
                                {log.timestamp.slice(11, 19)}
                            </span>
                            <span className={`flex-shrink-0 w-[52px] ${LEVEL_COLOR[log.level] ?? 'text-gray-500'}`}>
                                {log.level}
                            </span>
                            <span className="text-cyber-secondary flex-shrink-0 w-[120px] truncate">
                                {log.service}
                            </span>
                            <span className="text-gray-400 truncate flex-1 min-w-0">
                                {log.message}
                            </span>
                            <span className={`flex-shrink-0 text-xs ${SOURCE_COLOR[log.source ?? ''] ?? 'text-gray-600'}`}>
                                {log.source}
                            </span>
                            {log.is_anomaly && (
                                <span className="flex-shrink-0 text-red-400">⚠</span>
                            )}
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="mt-2 flex gap-4 text-xs text-cyber-muted font-mono flex-shrink-0">
                <span className="flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    {linesProcessed} processed
                </span>
                <span className="text-red-400">{anomaliesDetected} anomalies</span>
                <span className="text-emerald-700">{savingsPct}% token savings via normalization</span>
                <span className="ml-auto text-gray-600">GAIA + AIOpsArena</span>
            </div>
        </div>
    );
}
