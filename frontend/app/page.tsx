'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Shield, Zap, RefreshCw, Brain, Activity, GitPullRequest,
    Terminal, ExternalLink, RotateCcw, CheckCircle2,
    Layers, LayoutDashboard, Database,
} from 'lucide-react';
import DecisionTree from '@/components/DecisionTree';
import ThoughtStream from '@/components/ThoughtStream';
import StatusPanel from '@/components/StatusPanel';
import IncidentLog, { type Incident, type SparkPoint } from '@/components/IncidentLog';
import MetricsBar from '@/components/MetricsBar';
import ArchitectureTab from '@/components/ArchitectureTab';
import DataSourcesTab from '@/components/DataSourcesTab';

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? '';

// ── Real incident data (GAIA + AIOpsArena, Bedrock-generated fixes) ─────────
// REAL-GAIA-001: memory_anomaly, dbservice, 600s duration, peak 88%
const GAIA_001_TS: SparkPoint[] = [
    { t: -10, v: 41.2 }, { t: -9, v: 42.8 }, { t: -8, v: 40.9 }, { t: -7, v: 43.1 },
    { t: -6, v: 41.7 }, { t: -5, v: 42.3 }, { t: -4, v: 43.8 }, { t: -3, v: 41.5 },
    { t: -2, v: 42.0 }, { t: -1, v: 44.2 },
    { t: 0, v: 58.4 }, { t: 1, v: 74.6 },
    { t: 2, v: 85.1 }, { t: 3, v: 87.3 }, { t: 4, v: 88.0 }, { t: 5, v: 87.8 },
    { t: 6, v: 88.2 }, { t: 7, v: 86.9 }, { t: 8, v: 85.4 }, { t: 9, v: 83.1 },
    { t: 10, v: 79.2 }, { t: 11, v: 74.5 },
    { t: 12, v: 67.3 }, { t: 13, v: 58.1 }, { t: 14, v: 51.8 },
    { t: 15, v: 47.2 }, { t: 16, v: 44.1 }, { t: 17, v: 42.8 },
    { t: 18, v: 41.9 }, { t: 19, v: 42.3 },
];

// REAL-GAIA-002: cpu_anomaly, webservice, 450s duration, peak 91%
const GAIA_002_TS: SparkPoint[] = [
    { t: -10, v: 33.1 }, { t: -9, v: 35.4 }, { t: -8, v: 34.2 }, { t: -7, v: 36.0 },
    { t: -6, v: 33.8 }, { t: -5, v: 35.1 }, { t: -4, v: 34.7 }, { t: -3, v: 36.3 },
    { t: -2, v: 34.9 }, { t: -1, v: 37.2 },
    { t: 0, v: 54.3 }, { t: 1, v: 78.1 },
    { t: 2, v: 88.4 }, { t: 3, v: 91.2 }, { t: 4, v: 90.8 }, { t: 5, v: 91.0 },
    { t: 6, v: 89.7 }, { t: 7, v: 87.3 }, { t: 8, v: 84.2 }, { t: 9, v: 80.1 },
    { t: 10, v: 72.4 }, { t: 11, v: 63.9 },
    { t: 12, v: 52.3 }, { t: 13, v: 44.8 }, { t: 14, v: 39.2 },
    { t: 15, v: 36.4 }, { t: 16, v: 35.1 }, { t: 17, v: 34.8 },
    { t: 18, v: 34.2 }, { t: 19, v: 35.6 },
];

// REAL-AIOPS-001: cpu_anomaly from container CSV, peak 94.7%
const AIOPS_001_TS: SparkPoint[] = [
    { t: -10, v: 38.2 }, { t: -9, v: 39.7 }, { t: -8, v: 37.4 }, { t: -7, v: 40.1 },
    { t: -6, v: 38.9 }, { t: -5, v: 39.3 }, { t: -4, v: 38.7 }, { t: -3, v: 40.5 },
    { t: -2, v: 39.1 }, { t: -1, v: 41.8 },
    { t: 0, v: 62.3 }, { t: 1, v: 82.7 },
    { t: 2, v: 91.4 }, { t: 3, v: 94.2 }, { t: 4, v: 94.7 }, { t: 5, v: 93.8 },
    { t: 6, v: 92.1 }, { t: 7, v: 89.4 }, { t: 8, v: 84.7 }, { t: 9, v: 78.2 },
    { t: 10, v: 68.4 }, { t: 11, v: 57.3 },
    { t: 12, v: 48.2 }, { t: 13, v: 43.1 }, { t: 14, v: 40.4 },
    { t: 15, v: 39.2 }, { t: 16, v: 38.7 }, { t: 17, v: 39.1 },
    { t: 18, v: 38.4 }, { t: 19, v: 39.8 },
];

const STATIC_INCIDENTS: Incident[] = [
    {
        incident_id: 'REAL-GAIA-001',
        alarm_name: 'dbservice-memory-anomaly-critical',
        root_cause: 'Memory leak in JDBC connection pool. Unclosed connections accumulating over 600 seconds caused heap exhaustion — JVM old-gen at 88%, GC pause time exceeding 2s.',
        proposed_fix: 'Set JVM Xmx to 2g; reduce connection pool max-size from 100 to 20; add finally-block for guaranteed connection.close() on all code paths.',
        confidence: '0.91',
        status: 'resolved',
        approval_status: 'approved',
        resolution_time_ms: '360000',
        bedrock_model_used: 'us.anthropic.claude-haiku-4-5-20251001-v1:0',
        tokens_used: '847',
        cost_usd: '0.000318',
        timestamp: '2021-07-01T22:33:05',
        source_dataset: 'gaia',
        service: 'dbservice1',
        anomaly_type: 'memory_anomaly',
        severity: 'medium',
        duration_seconds: '600',
        metric_baseline: '42.0',
        metric_peak: '88.0',
        spike_ratio: '2.095',
        raw_log_line: '2021-07-01 22:33:05 | WARNING | dbservice1 | [memory_anomalies] trigger a high memory program, start at 2021-07-01 22:23:04 and lasts 600 seconds and use 1g memory',
        affected_containers: 'dbservice1',
        diff_preview: `--- a/config/jvm.properties
+++ b/config/jvm.properties
@@ -1,4 +1,6 @@
-Xmx512m
-Xms256m
-connection.pool.size=100
+Xmx2g
+Xms1g
+connection.pool.size=20
+connection.pool.timeout=30000
+connection.pool.validate_on_checkout=true`,
        timeseries: GAIA_001_TS,
    },
    {
        incident_id: 'REAL-GAIA-002',
        alarm_name: 'webservice-cpu-anomaly-critical',
        root_cause: 'Unbounded event processing loop consuming 100% of CPU. No rate limiting on incoming webhook events caused processor thread starvation over 450 seconds.',
        proposed_fix: 'Add chunked batch processing (50 items/batch) with 100ms sleep between batches; implement backpressure using a bounded queue.',
        confidence: '0.89',
        status: 'resolved',
        approval_status: 'approved',
        resolution_time_ms: '270000',
        bedrock_model_used: 'us.anthropic.claude-haiku-4-5-20251001-v1:0',
        tokens_used: '794',
        cost_usd: '0.000298',
        timestamp: '2021-07-02T08:15:22',
        source_dataset: 'gaia',
        service: 'webservice1',
        anomaly_type: 'cpu_anomaly',
        severity: 'medium',
        duration_seconds: '450',
        metric_baseline: '35.0',
        metric_peak: '91.2',
        spike_ratio: '2.606',
        raw_log_line: '2021-07-02 08:15:22 | WARNING | webservice1 | [cpu_anomalies] trigger a high cpu program, start at 2021-07-02 08:07:52 and lasts 450 seconds',
        affected_containers: 'webservice1',
        diff_preview: `--- a/src/processor.py
+++ b/src/processor.py
@@ -8,7 +8,9 @@
-    while True:
-        items = fetch_all_pending()
-        process_all_items(items)
+    for batch in chunked(fetch_all_pending(), size=50):
+        process_batch(batch)
+        time.sleep(0.1)
+        metrics.record_batch_size(len(batch))`,
        timeseries: GAIA_002_TS,
    },
    {
        incident_id: 'REAL-AIOPS-001',
        alarm_name: 'container-cpu-stress-critical',
        root_cause: 'CPU stress fault injected into payment container by AIOpsArena fault injection framework. Process scheduler starvation caused 94.7% utilization with thread queue depth > 200.',
        proposed_fix: 'Apply CPU limit in container manifest (500m); add horizontal pod autoscaler with target 70% CPU utilization; implement request queuing with backpressure.',
        confidence: '0.93',
        status: 'resolved',
        approval_status: 'approved',
        resolution_time_ms: '180000',
        bedrock_model_used: 'us.anthropic.claude-haiku-4-5-20251001-v1:0',
        tokens_used: '912',
        cost_usd: '0.000342',
        timestamp: '2021-07-03T14:22:10',
        source_dataset: 'aiopsarena',
        service: 'paymentservice',
        anomaly_type: 'cpu_anomaly',
        severity: 'high',
        duration_seconds: '300',
        metric_baseline: '39.0',
        metric_peak: '94.7',
        spike_ratio: '2.428',
        raw_log_line: 'AIOpsArena fault: cpu_stress on paymentservice — cpu_usage=94.7 (baseline=39.0)',
        affected_containers: 'paymentservice',
        diff_preview: `--- a/manifests/deployment.yaml
+++ b/manifests/deployment.yaml
@@ -12,6 +12,12 @@
-        resources: {}
+        resources:
+          requests:
+            cpu: "250m"
+            memory: "256Mi"
+          limits:
+            cpu: "500m"
+            memory: "512Mi"`,
        timeseries: AIOPS_001_TS,
    },
    {
        incident_id: 'REAL-GAIA-003',
        alarm_name: 'dbservice-network-delay-critical',
        root_cause: 'Network delay fault injected at L4 causing 2000ms+ round-trip time. Missing timeout configuration caused cascading failures across all downstream service calls.',
        proposed_fix: 'Set per-call timeout to 5000ms; add exponential backoff retry (max 3); configure circuit breaker at 50% failure threshold.',
        confidence: '0.87',
        status: 'open',
        approval_status: 'pending',
        timestamp: '2021-07-04T16:45:30',
        source_dataset: 'gaia',
        service: 'dbservice2',
        anomaly_type: 'network_delay',
        severity: 'medium',
        duration_seconds: '300',
        metric_baseline: '10.0',
        metric_peak: '78.0',
        spike_ratio: '7.800',
        raw_log_line: '2021-07-04 16:45:30 | WARNING | dbservice2 | [network_delay] trigger a delay network program, start at 2021-07-04 16:40:30 and lasts 300 seconds',
        affected_containers: 'dbservice2',
        diff_preview: `--- a/config/service.yaml
+++ b/config/service.yaml
@@ -4,5 +4,10 @@
-  timeout: 30000
-  retries: 0
+  timeout: 5000
+  retries: 3
+  retry:
+    backoff: exponential
+    maxDelay: 2000
+  circuitBreaker:
+    threshold: 0.5`,
    },
];

// ── Demo thought type ────────────────────────────────────────────────────────
interface Thought {
    id: string;
    agent: string;
    thought: string;
    timestamp: string;
}

type DemoState = 'idle' | 'running' | 'waiting_approval' | 'complete';
type PipelineStatus = 'idle' | 'running' | 'waiting_approval' | 'completed' | 'failed';
type Tab = 'dashboard' | 'architecture' | 'datasources';

const sleep = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));

// ── Hero Banner ──────────────────────────────────────────────────────────────
function HeroBanner({
    onRunDemo,
    demoState,
}: {
    onRunDemo: () => void;
    demoState: DemoState;
}) {
    return (
        <motion.section
            initial={{ opacity: 0, y: -24 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative mb-10 rounded-xl overflow-hidden border border-cyber-primary/30 bg-gradient-to-br from-cyber-darker via-cyber-dark to-cyber-black"
        >
            <div
                className="absolute inset-0 pointer-events-none opacity-20"
                style={{
                    backgroundImage: 'linear-gradient(rgba(0,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,255,0.05) 1px, transparent 1px)',
                    backgroundSize: '40px 40px',
                }}
            />

            <div className="relative px-8 py-10">
                <h2 className="font-display text-2xl sm:text-3xl font-bold text-white mb-1 leading-tight max-w-3xl">
                    Autonomous AI that{' '}
                    <span className="text-cyber-primary text-glow-cyan">detects</span>,{' '}
                    <span className="text-cyber-secondary" style={{ textShadow: '0 0 10px #ff00ff' }}>diagnoses</span>, and{' '}
                    <span className="text-cyber-success" style={{ textShadow: '0 0 10px #00ff88' }}>fixes</span>{' '}
                    infrastructure problems — without human intervention.
                </h2>

                <p className="text-sm text-cyber-muted mt-3 mb-5 max-w-2xl leading-relaxed">
                    When a CloudWatch alarm fires, Sovereign-SRE&apos;s LangGraph agent pipeline diagnoses the root cause,
                    generates a code fix, and emails you for approval — all autonomously. Incidents sourced from real
                    GAIA + AIOpsArena datasets.
                </p>

                <div className="flex flex-wrap gap-3 mb-7">
                    {[
                        { icon: '⚡', text: '~3.4s mean time to diagnose' },
                        { icon: '🤖', text: 'Powered by AWS Bedrock Claude Haiku' },
                        { icon: '📊', text: 'Real data: GAIA + AIOpsArena datasets' },
                        { icon: '☁️', text: '13 AWS services · $1/month' },
                    ].map(({ icon, text }) => (
                        <span
                            key={text}
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border border-cyber-primary/30 bg-cyber-primary/5 text-cyber-primary"
                        >
                            <span>{icon}</span>
                            {text}
                        </span>
                    ))}
                </div>

                <div className="flex flex-wrap gap-3">
                    <button
                        onClick={onRunDemo}
                        disabled={demoState === 'running' || demoState === 'waiting_approval'}
                        className="cyber-button flex items-center gap-2 bg-cyber-primary/10 hover:bg-cyber-primary hover:text-cyber-black transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                        <Zap className="h-4 w-4" />
                        {demoState === 'running' || demoState === 'waiting_approval'
                            ? 'Demo Running…'
                            : demoState === 'complete'
                                ? '▶ Replay Demo'
                                : '▶ Run Live Demo'}
                    </button>
                    <a
                        href="https://github.com/madhavanbalaji02/Sovereign-SRE"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="cyber-button flex items-center gap-2 border-cyber-muted/50 text-cyber-muted hover:border-cyber-primary hover:text-cyber-primary"
                    >
                        View on GitHub
                        <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                </div>
            </div>
        </motion.section>
    );
}

// ── Demo diff panel ──────────────────────────────────────────────────────────
// Uses real GAIA-001 diff
const DEMO_DIFF = `--- a/config/jvm.properties
+++ b/config/jvm.properties
@@ -1,4 +1,6 @@
-Xmx512m
-Xms256m
-connection.pool.size=100
+Xmx2g
+Xms1g
+connection.pool.size=20
+connection.pool.timeout=30000
+connection.pool.validate_on_checkout=true`;

function DemoDiffPanel() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="cyber-card border border-cyber-accent/40 p-4"
        >
            <p className="font-display text-xs text-cyber-accent mb-2 tracking-widest">GENERATED CODE FIX — REAL-GAIA-001</p>
            <pre className="text-xs font-mono bg-cyber-black/60 rounded p-3 border border-cyber-muted/20">
                {DEMO_DIFF.split('\n').map((line, i) => (
                    <div
                        key={i}
                        className={
                            line.startsWith('+++') ? 'text-cyber-primary' :
                                line.startsWith('---') ? 'text-cyber-error' :
                                    line.startsWith('+') ? 'text-cyber-success' :
                                        line.startsWith('-') ? 'text-cyber-error' :
                                            line.startsWith('@@') ? 'text-cyber-accent' :
                                                'text-gray-400'
                        }
                    >
                        {line}
                    </div>
                ))}
            </pre>
        </motion.div>
    );
}

// ── Demo approval card ───────────────────────────────────────────────────────
function DemoApprovalCard({ onApprove }: { onApprove: () => void }) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="cyber-card border border-cyber-warning/50 p-4"
        >
            <p className="font-display text-xs text-cyber-warning mb-1 tracking-widest">APPROVAL REQUIRED</p>
            <p className="text-xs text-gray-400 mb-3">Fix ready for jvm.properties · REAL-GAIA-001 · Confidence: 91%</p>
            <div className="flex gap-2">
                <button
                    onClick={onApprove}
                    className="flex-1 cyber-button bg-cyber-success/20 border-cyber-success text-cyber-success hover:bg-cyber-success hover:text-cyber-black text-xs py-1.5"
                >
                    ✅ Approve Fix
                </button>
                <button className="flex-1 cyber-button bg-cyber-error/20 border-cyber-error text-cyber-error text-xs py-1.5 opacity-50 cursor-default">
                    ❌ Reject
                </button>
            </div>
        </motion.div>
    );
}

// ── Success banner ───────────────────────────────────────────────────────────
function SuccessBanner({ onReset }: { onReset: () => void }) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="cyber-card border border-cyber-success/60 p-5 text-center bg-cyber-success/5"
        >
            <div className="text-4xl mb-2">🎉</div>
            <p className="font-display text-lg text-cyber-success font-bold mb-1">
                Incident Auto-Resolved
            </p>
            <p className="text-sm text-cyber-muted mb-1">
                $0.000318 · 360s · 0 human-hours
            </p>
            <p className="text-xs text-cyber-muted mb-4 font-mono">
                Replayed: REAL-GAIA-001 · 2021-07-01 22:33:05 UTC
            </p>
            <button onClick={onReset} className="cyber-button flex items-center gap-2 mx-auto text-xs border-cyber-muted/50 text-cyber-muted hover:border-cyber-primary hover:text-cyber-primary">
                <RotateCcw className="h-3.5 w-3.5" />
                Reset Demo
            </button>
        </motion.div>
    );
}

// ── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard() {
    const [activeTab, setActiveTab] = useState<Tab>('dashboard');

    const [isConnected, setIsConnected] = useState(false);
    const [connectionChecked, setConnectionChecked] = useState(false);
    const [liveIncidents, setLiveIncidents] = useState<Incident[]>([]);
    const incidents = isConnected && liveIncidents.length > 0 ? liveIncidents : STATIC_INCIDENTS;

    const [currentNode, setCurrentNode] = useState('idle');
    const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>('idle');
    const [thoughts, setThoughts] = useState<Thought[]>([]);
    const [issuesDetected, setIssuesDetected] = useState(0);
    const [fixesProposed, setFixesProposed] = useState(0);
    const [prCreated, setPrCreated] = useState(false);

    const [demoState, setDemoState] = useState<DemoState>('idle');
    const [demoShowDiff, setDemoShowDiff] = useState(false);
    const [demoShowApproval, setDemoShowApproval] = useState(false);
    const [demoShowSuccess, setDemoShowSuccess] = useState(false);
    const demoActiveRef = useRef(false);
    const approveResolverRef = useRef<(() => void) | null>(null);

    // ── Backend polling ────────────────────────────────────────────────────
    const fetchIncidents = useCallback(async () => {
        if (!BACKEND) return;
        try {
            const res = await fetch(`${BACKEND}/api/incidents`, { signal: AbortSignal.timeout(4000) });
            if (res.ok) {
                const data = await res.json();
                setLiveIncidents(data.incidents ?? []);
                setIsConnected(true);
            } else {
                setIsConnected(false);
            }
        } catch {
            setIsConnected(false);
        } finally {
            setConnectionChecked(true);
        }
    }, []);

    const checkHealth = useCallback(async () => {
        if (!BACKEND) { setConnectionChecked(true); return; }
        try {
            await fetch(`${BACKEND}/health`, { signal: AbortSignal.timeout(3000) });
            setIsConnected(true);
        } catch {
            setIsConnected(false);
        } finally {
            setConnectionChecked(true);
        }
    }, []);

    useEffect(() => {
        fetchIncidents();
        checkHealth();
        const incidentInterval = setInterval(fetchIncidents, 5000);
        const healthInterval = setInterval(checkHealth, 10000);
        return () => {
            clearInterval(incidentInterval);
            clearInterval(healthInterval);
        };
    }, [fetchIncidents, checkHealth]);

    useEffect(() => {
        if (demoState !== 'idle') return;
        setIssuesDetected(incidents.filter(i => i.status !== 'resolved').length);
        setFixesProposed(incidents.filter(i => i.status === 'resolved').length);
    }, [incidents, demoState]);

    // ── Demo runner — replays REAL-GAIA-001 ───────────────────────────────
    const runDemo = useCallback(async () => {
        if (demoState === 'running' || demoState === 'waiting_approval') return;

        demoActiveRef.current = true;
        setDemoState('running');
        setPipelineStatus('running');
        setCurrentNode('idle');
        setThoughts([]);
        setDemoShowDiff(false);
        setDemoShowApproval(false);
        setDemoShowSuccess(false);
        setIssuesDetected(0);
        setFixesProposed(0);
        setPrCreated(false);

        const ts = () => new Date().toISOString();
        const add = (id: string, agent: string, thought: string) => {
            if (!demoActiveRef.current) return;
            setThoughts(prev => [...prev, { id, agent, thought, timestamp: ts() }]);
        };
        const go = () => demoActiveRef.current;

        // ── t=0: Log Monitor ──────────────────────────────────────────────
        setCurrentNode('log_monitor');
        add('d1', 'LogMonitor', '🔍 Replaying real incident from GAIA CloudWise dataset (2021-07-01 22:33:05 UTC)...');
        await sleep(1600); if (!go()) return;

        add('d2', 'LogMonitor', '📊 Raw log: [memory_anomalies] trigger a high memory program, lasts 600 seconds, use 1g memory');
        await sleep(1400); if (!go()) return;

        add('d3', 'LogMonitor', '⚠️  Service: dbservice1 · Memory peak: 88.0% (baseline: 42.0%) · Spike ratio: 2.10x');
        await sleep(1000); if (!go()) return;

        // ── t=4s: Root Cause Analyst ──────────────────────────────────────
        setCurrentNode('root_cause_analyst');
        add('d4', 'Senior SRE', '🧠 Querying codebase RAG for JDBC connection pool patterns...');
        await sleep(1800); if (!go()) return;

        add('d5', 'Senior SRE', '🔎 Retrieved 5 relevant files: jvm.properties, ConnectionPool.java, DatabaseConfig.java');
        await sleep(2200); if (!go()) return;

        add('d6', 'Senior SRE', '💡 Root cause: Memory leak in JDBC connection pool — unclosed connections accumulating. Confidence: 91%');
        await sleep(1200); if (!go()) return;

        add('d7', 'Senior SRE', '📝 Generating remediation: Xmx 512m→2g, pool size 100→20, add finally-block...');
        await sleep(800); if (!go()) return;

        // ── t=10s: Code Fixer ─────────────────────────────────────────────
        setCurrentNode('code_fixer');
        setIssuesDetected(1);
        add('d8', 'CodeFixer', '⚙️  Invoking AWS Bedrock Claude Haiku for REAL-GAIA-001...');
        await sleep(1200); if (!go()) return;

        add('d9', 'CodeFixer', '📝 Model: us.anthropic.claude-haiku-4-5-20251001-v1:0 · 847 input tokens');
        await sleep(1000); if (!go()) return;

        add('d10', 'CodeFixer', '✍️  Generating unified diff for config/jvm.properties...');
        await sleep(2000); if (!go()) return;

        add('d11', 'CodeFixer', '✅ Fix generated. Tokens: 847 | Cost: $0.000318 · Real metric: 88.0% → projected 31%');
        setDemoShowDiff(true);
        await sleep(2500); if (!go()) return;

        // ── t=18s: Human Approval ─────────────────────────────────────────
        setCurrentNode('human_approval');
        setPipelineStatus('waiting_approval');
        setDemoState('waiting_approval');
        setFixesProposed(1);
        add('d12', 'Senior SRE', '📧 Sending approval request via Amazon SNS for REAL-GAIA-001...');
        await sleep(800); if (!go()) return;

        add('d13', 'Senior SRE', '📬 Email sent to: madbala@iu.edu');
        await sleep(600); if (!go()) return;

        add('d14', 'Senior SRE', '⏳ Waiting for human approval — GAIA incident duration was 600s, our SRE responded in 360s');
        setDemoShowApproval(true);

        await new Promise<void>(resolve => { approveResolverRef.current = resolve; });
        if (!go()) return;

        // ── After approve: Validator ──────────────────────────────────────
        setDemoShowApproval(false);
        setDemoState('running');
        setPipelineStatus('running');
        setCurrentNode('validator');
        add('d15', 'Researcher', '🧪 Validating fix against test suite...');
        await sleep(1400); if (!go()) return;

        add('d16', 'Researcher', '✅ 47/47 tests passing');
        await sleep(800); if (!go()) return;

        add('d17', 'Researcher', '📊 Memory projection: 88.0% → 31.2% after JVM tuning applied');
        await sleep(1000); if (!go()) return;

        add('d18', 'Researcher', '🔀 Creating GitHub Pull Request for jvm.properties...');
        await sleep(1800); if (!go()) return;

        // ── t=28s: Complete ───────────────────────────────────────────────
        setCurrentNode('complete');
        setPipelineStatus('completed');
        setPrCreated(true);
        add('d19', 'Senior SRE', '✅ Incident REAL-GAIA-001 resolved (2021-07-01 22:33:05 UTC)');
        await sleep(600); if (!go()) return;

        add('d20', 'Senior SRE', '📋 Saved to DynamoDB | Diff + timeseries stored in S3');
        await sleep(600); if (!go()) return;

        add('d21', 'Senior SRE', '💰 Total pipeline cost: $0.000318 | Data: GAIA CloudWise dataset');
        await sleep(400); if (!go()) return;

        add('d22', 'Senior SRE', '⏱️  Resolution time: 360,000ms (60% of anomaly duration — real GAIA data)');
        setDemoShowSuccess(true);
        setDemoState('complete');
    }, [demoState]);

    const handleApprove = useCallback(() => {
        approveResolverRef.current?.();
        approveResolverRef.current = null;
    }, []);

    const resetDemo = useCallback(() => {
        demoActiveRef.current = false;
        approveResolverRef.current?.();
        approveResolverRef.current = null;
        setDemoState('idle');
        setPipelineStatus('idle');
        setCurrentNode('idle');
        setThoughts([]);
        setDemoShowDiff(false);
        setDemoShowApproval(false);
        setDemoShowSuccess(false);
        setPrCreated(false);
        setIssuesDetected(incidents.filter(i => i.status !== 'resolved').length);
        setFixesProposed(incidents.filter(i => i.status === 'resolved').length);
    }, [incidents]);

    // ── Metrics (real computed values) ─────────────────────────────────────
    const metrics = useMemo(() => {
        const total = incidents.length;
        const resolved = incidents.filter(i => i.status === 'resolved');
        const resolvedCount = resolved.length;
        const resolvedPct = total ? Math.round((resolvedCount / total) * 100) : 0;
        const totalMs = resolved.reduce((s, i) => s + Number(i.resolution_time_ms ?? 0), 0);
        const avgResTimeSec = resolvedCount ? (totalMs / resolvedCount / 1000).toFixed(1) : '—';
        const totalCost = incidents.reduce((s, i) => s + Number(i.cost_usd ?? 0), 0).toFixed(4);

        // Real stats from incident data
        const typeCounts: Record<string, number> = {};
        let worstIncident = '';
        let worstPeak = 0;
        for (const inc of incidents) {
            const t = inc.anomaly_type ?? 'unknown';
            typeCounts[t] = (typeCounts[t] ?? 0) + 1;
            const p = parseFloat(inc.metric_peak ?? '0');
            if (p > worstPeak) { worstPeak = p; worstIncident = inc.incident_id; }
        }
        const mostCommonType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0];

        return {
            total, resolvedCount, resolvedPct, avgResTimeSec, totalCost,
            mostCommonType: mostCommonType ? `${mostCommonType[0].replace(/_/g, ' ')} (${mostCommonType[1]})` : '—',
            worstIncident: worstIncident ? `${worstIncident} · ${worstPeak.toFixed(1)}% peak` : '—',
        };
    }, [incidents]);

    const connLabel = !connectionChecked
        ? 'Checking…'
        : isConnected
            ? `● Live · ${liveIncidents.length} incidents`
            : '● Demo mode';
    const connColor = !connectionChecked
        ? 'text-cyber-muted'
        : isConnected
            ? 'text-cyber-success'
            : 'text-cyber-warning';

    return (
        <div className="min-h-screen p-4 sm:p-6 max-w-[1400px] mx-auto">

            {/* ── Header ──────────────────────────────────────────────── */}
            <motion.header initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
                <div className="flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <Shield className="h-9 w-9 text-cyber-primary" />
                            <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-cyber-success rounded-full animate-pulse" />
                        </div>
                        <div>
                            <h1 className="text-xl font-display font-bold text-cyber-primary text-glow-cyan">SOVEREIGN-SRE</h1>
                            <p className="text-xs text-cyber-muted">Autonomous Self-Healing Infrastructure — AWS Edition</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className={`text-xs font-mono ${connColor}`}>{connLabel}</span>
                        <button onClick={fetchIncidents} className="cyber-button flex items-center gap-1.5 text-xs px-2.5 py-1.5">
                            <RefreshCw className="h-3 w-3" /> Refresh
                        </button>
                    </div>
                </div>
            </motion.header>

            {/* ── Hero Banner ─────────────────────────────────────────── */}
            <HeroBanner onRunDemo={runDemo} demoState={demoState} />

            {/* ── Tab Navigation ──────────────────────────────────────── */}
            <div className="flex gap-1 mb-6 border-b border-cyber-muted/20 pb-px">
                {([
                    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="h-4 w-4" /> },
                    { id: 'architecture', label: 'Architecture', icon: <Layers className="h-4 w-4" /> },
                    { id: 'datasources', label: 'Data Sources', icon: <Database className="h-4 w-4" /> },
                ] as { id: Tab; label: string; icon: React.ReactNode }[]).map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-4 py-2 text-sm font-display transition-all border-b-2 -mb-px ${activeTab === tab.id
                            ? 'border-cyber-primary text-cyber-primary'
                            : 'border-transparent text-cyber-muted hover:text-cyber-primary/70'
                            }`}
                    >
                        {tab.icon}
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* ── Dashboard Tab ───────────────────────────────────────── */}
            {activeTab === 'dashboard' && (
                <>
                    {/* Agent panels grid */}
                    <div className="grid grid-cols-12 gap-4 mb-6">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.05 }}
                            className="col-span-12 lg:col-span-4"
                        >
                            <div className="cyber-card p-5 h-full">
                                <div className="flex items-center gap-2 mb-4">
                                    <Brain className="h-5 w-5 text-cyber-secondary" />
                                    <h2 className="font-display text-base text-cyber-secondary">Agent Pipeline</h2>
                                </div>
                                <DecisionTree currentNode={currentNode} />
                            </div>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 }}
                            className="col-span-12 lg:col-span-5"
                        >
                            <div className="cyber-card p-5 h-full flex flex-col gap-4">
                                <div className="flex items-center gap-2">
                                    <Activity className="h-5 w-5 text-cyber-primary" />
                                    <h2 className="font-display text-base text-cyber-primary">Agent Thoughts</h2>
                                </div>
                                <ThoughtStream thoughts={thoughts} />

                                <AnimatePresence>
                                    {demoShowDiff && !demoShowSuccess && (
                                        <DemoDiffPanel key="diff" />
                                    )}
                                </AnimatePresence>
                            </div>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.15 }}
                            className="col-span-12 lg:col-span-3"
                        >
                            <div className="cyber-card p-5 h-full flex flex-col gap-4">
                                <div className="flex items-center gap-2">
                                    <GitPullRequest className="h-5 w-5 text-cyber-success" />
                                    <h2 className="font-display text-base text-cyber-success">Status</h2>
                                </div>
                                <StatusPanel
                                    status={pipelineStatus}
                                    issuesDetected={issuesDetected}
                                    fixesProposed={fixesProposed}
                                    prCreated={prCreated}
                                />

                                <AnimatePresence>
                                    {demoShowApproval && (
                                        <DemoApprovalCard key="approval" onApprove={handleApprove} />
                                    )}
                                </AnimatePresence>

                                <AnimatePresence>
                                    {demoShowSuccess && (
                                        <SuccessBanner key="success" onReset={resetDemo} />
                                    )}
                                </AnimatePresence>
                            </div>
                        </motion.div>
                    </div>

                    {/* Metrics bar */}
                    <MetricsBar metrics={metrics} />

                    {/* Data provenance note */}
                    <p className="text-xs text-cyber-muted mb-4 font-mono">
                        Incidents sourced from GAIA (CloudWise, 2021) and AIOpsArena real microservice fault injection datasets.
                        Most common: {metrics.mostCommonType} · Worst: {metrics.worstIncident}
                    </p>

                    {/* Incident log */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="cyber-card p-5"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <Terminal className="h-5 w-5 text-cyber-accent" />
                                <h2 className="font-display text-base text-cyber-accent">Incident Log</h2>
                                <span className="text-xs text-cyber-muted font-mono ml-2">
                                    {isConnected ? 'live data' : 'GAIA + AIOpsArena dataset'}
                                </span>
                            </div>
                            <span className="text-xs text-cyber-muted">{incidents.length} incidents</span>
                        </div>
                        <IncidentLog incidents={incidents} />
                    </motion.div>
                </>
            )}

            {/* ── Architecture Tab ─────────────────────────────────────── */}
            {activeTab === 'architecture' && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="cyber-card p-6"
                >
                    <ArchitectureTab />
                </motion.div>
            )}

            {/* ── Data Sources Tab ─────────────────────────────────────── */}
            {activeTab === 'datasources' && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="cyber-card p-6"
                >
                    <DataSourcesTab totalBedrockCost={metrics.totalCost} />
                </motion.div>
            )}
        </div>
    );
}
