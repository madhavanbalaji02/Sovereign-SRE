'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Shield, Zap, RefreshCw, Brain, Activity, GitPullRequest,
    Terminal, ExternalLink, RotateCcw, CheckCircle2, X,
    Layers, LayoutDashboard,
} from 'lucide-react';
import DecisionTree from '@/components/DecisionTree';
import ThoughtStream from '@/components/ThoughtStream';
import StatusPanel from '@/components/StatusPanel';
import IncidentLog, { type Incident } from '@/components/IncidentLog';
import MetricsBar from '@/components/MetricsBar';
import ArchitectureTab from '@/components/ArchitectureTab';

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? '';

// ── Static incidents (shown when backend unreachable) ───────────────────────
const STATIC_INCIDENTS: Incident[] = [
    {
        incident_id: 'INC-2025-001',
        alarm_name: 'payments-service-memory-critical',
        root_cause: 'Memory leak in payment processor connection pool. Unclosed JDBC connections accumulating over 6 hours.',
        proposed_fix: 'Set connection pool max-size=20, added finally block to ensure connection.close() on all code paths.',
        confidence: '0.94',
        status: 'resolved',
        approval_status: 'approved',
        resolution_time_ms: '3420',
        bedrock_model_used: 'us.anthropic.claude-haiku-4-5-20251001-v1:0',
        tokens_used: '2480',
        cost_usd: '0.00105',
        timestamp: '2025-01-15T10:23:00Z',
        diff_preview: '- connection_pool = ConnectionPool(max_size=100)\n+ connection_pool = ConnectionPool(max_size=20,\n+     timeout=30, validate_on_checkout=True)\n+\n+ def process_payment(self, data):\n+     conn = self.pool.get_connection()\n+     try:\n+         return self._execute(conn, data)\n+     finally:\n+         conn.close()  # guaranteed cleanup',
    },
    {
        incident_id: 'INC-2025-002',
        alarm_name: 'api-gateway-5xx-rate-critical',
        root_cause: 'Downstream ML inference endpoint timing out after model update increased p95 latency from 180ms to 4200ms.',
        proposed_fix: 'Added circuit breaker with 2s timeout + fallback to cached predictions for non-critical requests.',
        confidence: '0.91',
        status: 'resolved',
        approval_status: 'approved',
        resolution_time_ms: '5100',
        bedrock_model_used: 'us.anthropic.claude-haiku-4-5-20251001-v1:0',
        tokens_used: '1940',
        cost_usd: '0.00082',
        timestamp: '2025-01-18T14:07:00Z',
    },
    {
        incident_id: 'INC-2025-003',
        alarm_name: 'worker-node-disk-utilization-critical',
        root_cause: 'Log rotation disabled after last deployment. /var/log growing at 2.3 GB/day, disk 94% full.',
        proposed_fix: 'Re-enabled logrotate, set 7-day retention, compressed old logs, freed 47 GB immediately.',
        confidence: '0.98',
        status: 'resolved',
        approval_status: 'approved',
        resolution_time_ms: '1890',
        bedrock_model_used: 'us.anthropic.claude-haiku-4-5-20251001-v1:0',
        tokens_used: '1120',
        cost_usd: '0.00048',
        timestamp: '2025-01-22T09:45:00Z',
    },
    {
        incident_id: 'INC-2025-004',
        alarm_name: 'llm-eval-faithfulness-below-threshold',
        root_cause: 'Faithfulness score dropped from 0.89 to 0.61 after prompt template update. RAGAS detects hallucination rate 3× above baseline on financial domain queries.',
        proposed_fix: 'Roll back prompt template to v2.3, re-run eval harness on affected query categories.',
        confidence: '0.87',
        status: 'open',
        approval_status: 'pending',
        timestamp: '2025-01-24T16:30:00Z',
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
type Tab = 'dashboard' | 'architecture';

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
            {/* Subtle grid overlay */}
            <div
                className="absolute inset-0 pointer-events-none opacity-20"
                style={{
                    backgroundImage: 'linear-gradient(rgba(0,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,255,0.05) 1px, transparent 1px)',
                    backgroundSize: '40px 40px',
                }}
            />

            <div className="relative px-8 py-10">
                {/* Heading */}
                <h2 className="font-display text-2xl sm:text-3xl font-bold text-white mb-1 leading-tight max-w-3xl">
                    Autonomous AI that{' '}
                    <span className="text-cyber-primary text-glow-cyan">detects</span>,{' '}
                    <span className="text-cyber-secondary" style={{ textShadow: '0 0 10px #ff00ff' }}>diagnoses</span>, and{' '}
                    <span className="text-cyber-success" style={{ textShadow: '0 0 10px #00ff88' }}>fixes</span>{' '}
                    infrastructure problems — without human intervention.
                </h2>

                {/* One-liner */}
                <p className="text-sm text-cyber-muted mt-3 mb-5 max-w-2xl leading-relaxed">
                    When a CloudWatch alarm fires, Sovereign-SRE&apos;s LangGraph agent pipeline diagnoses the root cause,
                    generates a code fix, and emails you for approval — all autonomously.
                </p>

                {/* Stat pills */}
                <div className="flex flex-wrap gap-3 mb-7">
                    {[
                        { icon: '⚡', text: '~3.4s mean time to diagnose' },
                        { icon: '🤖', text: 'Powered by AWS Bedrock Claude Haiku' },
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

                {/* CTA buttons */}
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
const DEMO_DIFF = `- connection_pool = ConnectionPool(max_size=100)
+ connection_pool = ConnectionPool(max_size=20,
+     timeout=30, validate_on_checkout=True)`;

function DemoDiffPanel() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="cyber-card border border-cyber-accent/40 p-4"
        >
            <p className="font-display text-xs text-cyber-accent mb-2 tracking-widest">GENERATED CODE FIX</p>
            <pre className="text-xs font-mono bg-cyber-black/60 rounded p-3 border border-cyber-muted/20">
                {DEMO_DIFF.split('\n').map((line, i) => (
                    <div
                        key={i}
                        className={line.startsWith('+') ? 'text-cyber-success' : line.startsWith('-') ? 'text-cyber-error' : 'text-gray-400'}
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
            <p className="text-xs text-gray-400 mb-3">Fix ready for ConnectionPool.java · Confidence: 94%</p>
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
            <p className="text-sm text-cyber-muted mb-4">
                $0.00105 · 3.4 seconds · 0 human-hours
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

    // Connection state (polling-based, no WebSocket)
    const [isConnected, setIsConnected] = useState(false);
    const [connectionChecked, setConnectionChecked] = useState(false);

    // Incidents — live from backend, or static fallback
    const [liveIncidents, setLiveIncidents] = useState<Incident[]>([]);
    const incidents = isConnected && liveIncidents.length > 0 ? liveIncidents : STATIC_INCIDENTS;

    // Pipeline / agent panel state
    const [currentNode, setCurrentNode] = useState('idle');
    const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>('idle');
    const [thoughts, setThoughts] = useState<Thought[]>([]);
    const [issuesDetected, setIssuesDetected] = useState(0);
    const [fixesProposed, setFixesProposed] = useState(0);
    const [prCreated, setPrCreated] = useState(false);

    // Demo mode
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

    // Sync pipeline stats from incidents
    useEffect(() => {
        if (demoState !== 'idle') return;
        setIssuesDetected(incidents.filter(i => i.status !== 'resolved').length);
        setFixesProposed(incidents.filter(i => i.status === 'resolved').length);
    }, [incidents, demoState]);

    // ── Demo runner ────────────────────────────────────────────────────────
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
        add('d1', 'LogMonitor', '🔍 Scanning CloudWatch log group /sovereign-sre/incidents...');
        await sleep(1600); if (!go()) return;

        add('d2', 'LogMonitor', '📊 Detected anomaly: payments-service memory usage at 94%');
        await sleep(1400); if (!go()) return;

        add('d3', 'LogMonitor', '⚠️  Threshold breach: > 85% for 3 consecutive minutes');
        await sleep(1000); if (!go()) return;

        // ── t=4s: Root Cause Analyst ──────────────────────────────────────
        setCurrentNode('root_cause_analyst');
        add('d4', 'Senior SRE', '🧠 Querying codebase RAG (pgvector, 1,247 chunks indexed)...');
        await sleep(1800); if (!go()) return;

        add('d5', 'Senior SRE', '🔎 Retrieved 5 relevant files: PaymentProcessor.java, ConnectionPool.java, DatabaseConfig.java');
        await sleep(2200); if (!go()) return;

        add('d6', 'Senior SRE', '💡 Root cause identified: unclosed JDBC connections in payment processor. Confidence: 94%');
        await sleep(1200); if (!go()) return;

        add('d7', 'Senior SRE', '📝 Generating remediation plan...');
        await sleep(800); if (!go()) return;

        // ── t=10s: Code Fixer ─────────────────────────────────────────────
        setCurrentNode('code_fixer');
        setIssuesDetected(1);
        add('d8', 'CodeFixer', '⚙️  Invoking AWS Bedrock Claude Haiku...');
        await sleep(1200); if (!go()) return;

        add('d9', 'CodeFixer', '📝 Model: us.anthropic.claude-haiku-4-5-20251001-v1:0');
        await sleep(1000); if (!go()) return;

        add('d10', 'CodeFixer', '✍️  Generating code fix for ConnectionPool.java...');
        await sleep(2000); if (!go()) return;

        add('d11', 'CodeFixer', '✅ Fix generated. Tokens: 2,480 | Cost: $0.00105');
        setDemoShowDiff(true);
        await sleep(2500); if (!go()) return;

        // ── t=18s: Human Approval ─────────────────────────────────────────
        setCurrentNode('human_approval');
        setPipelineStatus('waiting_approval');
        setDemoState('waiting_approval');
        setFixesProposed(1);
        add('d12', 'Senior SRE', '📧 Sending approval request via Amazon SNS...');
        await sleep(800); if (!go()) return;

        add('d13', 'Senior SRE', '📬 Email sent to: madhavan@example.com');
        await sleep(600); if (!go()) return;

        add('d14', 'Senior SRE', '⏳ Waiting for human approval (timeout: 1 hr)...');
        setDemoShowApproval(true);

        // Pause until approve clicked
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

        add('d17', 'Researcher', '📊 Memory projection: 94% → 31% after fix applied');
        await sleep(1000); if (!go()) return;

        add('d18', 'Researcher', '🔀 Creating GitHub Pull Request...');
        await sleep(1800); if (!go()) return;

        // ── t=28s: Complete ───────────────────────────────────────────────
        setCurrentNode('complete');
        setPipelineStatus('completed');
        setPrCreated(true);
        add('d19', 'Senior SRE', '✅ Incident INC-2025-001 resolved');
        await sleep(600); if (!go()) return;

        add('d20', 'Senior SRE', '📋 Saved to DynamoDB | Diff stored in S3');
        await sleep(600); if (!go()) return;

        add('d21', 'Senior SRE', '💰 Total pipeline cost: $0.00105');
        await sleep(400); if (!go()) return;

        add('d22', 'Senior SRE', '⏱️  Resolution time: 3,420ms');
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

    // ── Metrics ────────────────────────────────────────────────────────────
    const metrics = useMemo(() => {
        const total = incidents.length;
        const resolved = incidents.filter(i => i.status === 'resolved');
        const resolvedCount = resolved.length;
        const resolvedPct = total ? Math.round((resolvedCount / total) * 100) : 0;
        const totalMs = resolved.reduce((s, i) => s + Number(i.resolution_time_ms ?? 0), 0);
        const avgResTimeSec = resolvedCount ? (totalMs / resolvedCount / 1000).toFixed(1) : '—';
        const totalCost = incidents.reduce((s, i) => s + Number(i.cost_usd ?? 0), 0).toFixed(4);
        return { total, resolvedCount, resolvedPct, avgResTimeSec, totalCost };
    }, [incidents]);

    // ── Connection indicator label ─────────────────────────────────────────
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

                                {/* Demo: diff panel */}
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

                                {/* Demo: approval card */}
                                <AnimatePresence>
                                    {demoShowApproval && (
                                        <DemoApprovalCard key="approval" onApprove={handleApprove} />
                                    )}
                                </AnimatePresence>

                                {/* Demo: success banner */}
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
                                    {isConnected ? 'live data' : 'demo data — connect backend for live'}
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
        </div>
    );
}
