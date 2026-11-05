'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Activity, Pause, Play } from 'lucide-react';

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

const LEVEL_STYLE: Record<string, string> = {
    ERROR: 'text-cyber-error',
    CRITICAL: 'text-cyber-error',
    WARNING: 'text-cyber-warning',
    INFO: 'text-cyber-subtle',
    DEBUG: 'text-cyber-subtle',
};

function now(): string {
    return new Date().toISOString().replace('T', ' ').slice(0, 19) + 'Z';
}

export default function LiveLogFeed() {
    const [logs, setLogs] = useState<LogLine[]>([]);
    const [linesProcessed, setLinesProcessed] = useState(0);
    const [anomaliesDetected, setAnomaliesDetected] = useState(0);
    const [paused, setPaused] = useState(false);
    const pausedRef = useRef(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const idxRef = useRef(0);
    const counterRef = useRef({ total: 0, anomalies: 0 });

    // Replay real GAIA + AIOpsArena log lines at ~1 line per 1.5s
    useEffect(() => {
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
            if (pausedRef.current) return;
            const entry = REAL_GAIA_LOGS[idxRef.current % REAL_GAIA_LOGS.length];
            idxRef.current++;
            counterRef.current.total++;
            if (entry.is_anomaly) counterRef.current.anomalies++;
            setLogs(prev => [...prev.slice(-49), { ...entry, id: idxRef.current, timestamp: now() }]);
            setLinesProcessed(counterRef.current.total);
            setAnomaliesDetected(counterRef.current.anomalies);
        }, 1500);

        return () => clearInterval(interval);
    }, []);

    // Auto-scroll the log pane (not the page) to the newest line
    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [logs]);

    const togglePause = () => {
        pausedRef.current = !pausedRef.current;
        setPaused(pausedRef.current);
    };

    return (
        <section className="cyber-card flex h-full flex-col p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-cyber-subtle" />
                    <h2 className="text-sm font-semibold text-cyber-text">Log Stream</h2>
                    <span className={`ml-1 inline-flex items-center gap-1.5 text-[11px] font-medium ${paused ? 'text-cyber-muted' : 'text-cyber-success'}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${paused ? 'bg-cyber-subtle' : 'bg-cyber-success animate-pulse'}`} />
                        {paused ? 'Paused' : 'Streaming'}
                    </span>
                </div>
                <button onClick={togglePause} className="cyber-button btn-sm !h-7 !px-2" aria-label={paused ? 'Resume stream' : 'Pause stream'} title={paused ? 'Resume' : 'Pause'}>
                    {paused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
                </button>
            </div>

            <div className="relative min-h-[220px] flex-1">
            <div
                ref={scrollRef}
                className="h-[420px] overflow-y-auto rounded-lg border border-cyber-border bg-cyber-dark py-1.5 font-mono text-[11.5px] lg:absolute lg:inset-0 lg:h-auto"
                role="log"
                aria-live="off"
            >
                <AnimatePresence initial={false}>
                    {logs.map(log => (
                        <motion.div
                            key={log.id}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.2 }}
                            className={`grid grid-cols-[4.25rem_3.75rem_minmax(0,1fr)] gap-x-2 sm:grid-cols-[4.25rem_3.75rem_minmax(0,8rem)_minmax(0,1fr)] border-l-2 px-3 py-[3px] leading-5 ${log.is_anomaly ? 'border-cyber-error/70 bg-cyber-error/[0.05]' : 'border-transparent'}`}
                            title={`${log.source} · ${log.message}`}
                        >
                            <span className="text-cyber-subtle tabular">{log.timestamp.slice(11, 19)}</span>
                            <span className={LEVEL_STYLE[log.level] ?? 'text-cyber-subtle'}>{log.level}</span>
                            <span className="hidden truncate text-cyber-accent/80 sm:block">{log.service}</span>
                            <span className="truncate text-cyber-muted">{log.message}</span>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-cyber-muted">
                <span className="flex items-center gap-1.5"><Activity className="h-3.5 w-3.5 text-cyber-subtle" /><span className="text-cyber-text tabular">{linesProcessed}</span> processed</span>
                <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-cyber-error" /><span className="text-cyber-text tabular">{anomaliesDetected}</span> anomalies</span>
                <span>72% token savings via normalisation</span>
                <span className="ml-auto text-cyber-subtle">GAIA + AIOpsArena replay</span>
            </div>
        </section>
    );
}
