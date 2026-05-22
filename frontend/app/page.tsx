'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Activity, Brain, GitPullRequest, Terminal, Shield, Zap, RefreshCw } from 'lucide-react';
import DecisionTree from '@/components/DecisionTree';
import ThoughtStream from '@/components/ThoughtStream';
import StatusPanel from '@/components/StatusPanel';
import LogViewer from '@/components/LogViewer';

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? '';

export default function Dashboard() {
    const [isConnected, setIsConnected] = useState(false);
    const [currentNode, setCurrentNode] = useState('idle');
    const [pipelineStatus, setPipelineStatus] = useState<'idle' | 'running' | 'waiting_approval' | 'completed' | 'failed'>('idle');
    const [thoughts, setThoughts] = useState<Array<{ id: string; agent: string; thought: string; timestamp: string }>>([]);
    const [logs, setLogs] = useState<Array<{ level: string; message: string; timestamp: string }>>([]);
    const [incidents, setIncidents] = useState<Array<Record<string, string>>>([]);
    const [issuesDetected, setIssuesDetected] = useState(0);
    const [fixesProposed, setFixesProposed] = useState(0);
    const [isTriggering, setIsTriggering] = useState(false);

    // Fetch incidents from DynamoDB via backend
    const fetchIncidents = useCallback(async () => {
        try {
            const res = await fetch(`${BACKEND}/api/incidents`);
            if (res.ok) {
                const data = await res.json();
                setIncidents(data.incidents ?? []);
                const resolved = (data.incidents ?? []).filter((i: Record<string, string>) => i.status === 'resolved').length;
                setFixesProposed(resolved);
                setIsConnected(true);
            }
        } catch {
            setIsConnected(false);
        }
    }, []);

    useEffect(() => {
        fetchIncidents();
        const interval = setInterval(fetchIncidents, 15000);
        return () => clearInterval(interval);
    }, [fetchIncidents]);

    // Populate logs from incidents
    useEffect(() => {
        const recentLogs = incidents.slice(0, 10).map(inc => ({
            level: inc.status === 'resolved' ? 'INFO' : 'ERROR',
            message: inc.root_cause || `Incident ${inc.incident_id?.slice(0, 8)} — ${inc.status}`,
            timestamp: inc.timestamp || new Date().toISOString(),
        }));
        if (recentLogs.length > 0) {
            setLogs(recentLogs);
            setIssuesDetected(incidents.filter(i => i.status !== 'resolved').length);
        }
    }, [incidents]);

    const triggerPipeline = async () => {
        setIsTriggering(true);
        setPipelineStatus('running');
        setCurrentNode('log_monitor');
        setThoughts([]);

        const newThoughts = [
            { id: '1', agent: 'LogMonitor', thought: 'Scanning CloudWatch Logs for anomalies...', timestamp: new Date().toISOString() },
            { id: '2', agent: 'Step Functions', thought: 'Starting sovereign-sre-pipeline execution...', timestamp: new Date().toISOString() },
        ];
        setThoughts(newThoughts);

        try {
            const res = await fetch(`${BACKEND}/api/pipeline/trigger`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    trigger_source: 'dashboard',
                    alarm_name: 'sovereign-sre-dashboard-trigger',
                    severity: 'high',
                    logs: [{
                        level: 'ERROR',
                        message: 'OOMKilled on pod payments-service. Memory limit 512Mi exceeded.',
                        timestamp: new Date().toISOString(),
                    }],
                }),
            });

            if (res.ok) {
                const data = await res.json();
                setCurrentNode('root_cause_analyst');
                setThoughts(prev => [...prev,
                    { id: '3', agent: 'Senior SRE', thought: 'Analyzing root cause with Bedrock Claude Haiku...', timestamp: new Date().toISOString() },
                    { id: '4', agent: 'Step Functions', thought: `Execution started: ${data.execution_arn?.slice(-36) || data.incident_id}`, timestamp: new Date().toISOString() },
                    { id: '5', agent: 'SNS', thought: 'Approval email sent to madbala@iu.edu — awaiting response...', timestamp: new Date().toISOString() },
                ]);
                setPipelineStatus('waiting_approval');
                setCurrentNode('waiting_approval');
                setTimeout(fetchIncidents, 3000);
            } else {
                setPipelineStatus('failed');
            }
        } catch {
            setPipelineStatus('failed');
            setThoughts(prev => [...prev,
                { id: 'err', agent: 'System', thought: 'Backend unreachable. Is EC2 running?', timestamp: new Date().toISOString() },
            ]);
        } finally {
            setIsTriggering(false);
        }
    };

    return (
        <div className="min-h-screen p-6">
            {/* Header */}
            <motion.header initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <Shield className="h-10 w-10 text-cyber-primary" />
                            <div className="absolute -top-1 -right-1 w-3 h-3 bg-cyber-success rounded-full animate-pulse" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-display font-bold text-cyber-primary text-glow-cyan">
                                SOVEREIGN-SRE
                            </h1>
                            <p className="text-sm text-cyber-muted">Autonomous Self-Healing Infrastructure — AWS Edition</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                            <span className={`status-dot ${isConnected ? 'active' : 'error'}`} />
                            <span className="text-sm text-cyber-muted">
                                {isConnected ? `Connected · ${incidents.length} incidents` : 'Connecting to EC2...'}
                            </span>
                        </div>
                        <button onClick={fetchIncidents} className="cyber-button flex items-center gap-2 text-xs px-3 py-1">
                            <RefreshCw className="h-3 w-3" />
                        </button>
                        <button
                            onClick={triggerPipeline}
                            disabled={isTriggering}
                            className="cyber-button flex items-center gap-2"
                        >
                            <Zap className="h-4 w-4" />
                            {isTriggering ? 'Running...' : 'Trigger Pipeline'}
                        </button>
                    </div>
                </div>
            </motion.header>

            {/* Incident count bar */}
            {incidents.length > 0 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6 flex gap-4 flex-wrap">
                    {['resolved', 'running', 'failed', 'waiting_approval'].map(s => {
                        const count = incidents.filter(i => i.status === s).length;
                        if (!count) return null;
                        const colors: Record<string, string> = { resolved: 'text-cyber-success border-cyber-success', running: 'text-cyber-primary border-cyber-primary', failed: 'text-cyber-error border-cyber-error', waiting_approval: 'text-cyber-warning border-cyber-warning' };
                        return (
                            <span key={s} className={`px-3 py-1 rounded border text-xs font-display ${colors[s] ?? ''}`}>
                                {count} {s.replace('_', ' ')}
                            </span>
                        );
                    })}
                </motion.div>
            )}

            {/* Main Grid */}
            <div className="grid grid-cols-12 gap-6">
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="col-span-4">
                    <div className="cyber-card p-6 h-full">
                        <div className="flex items-center gap-2 mb-4">
                            <Brain className="h-5 w-5 text-cyber-secondary" />
                            <h2 className="font-display text-lg text-cyber-secondary">Agent Pipeline</h2>
                        </div>
                        <DecisionTree currentNode={currentNode} />
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="col-span-5">
                    <div className="cyber-card p-6 h-full">
                        <div className="flex items-center gap-2 mb-4">
                            <Activity className="h-5 w-5 text-cyber-primary" />
                            <h2 className="font-display text-lg text-cyber-primary">Agent Thoughts</h2>
                        </div>
                        <ThoughtStream thoughts={thoughts} />
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} className="col-span-3">
                    <div className="cyber-card p-6 h-full">
                        <div className="flex items-center gap-2 mb-4">
                            <GitPullRequest className="h-5 w-5 text-cyber-success" />
                            <h2 className="font-display text-lg text-cyber-success">Status</h2>
                        </div>
                        <StatusPanel
                            status={pipelineStatus}
                            issuesDetected={issuesDetected}
                            fixesProposed={fixesProposed}
                            prCreated={false}
                        />
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="col-span-12">
                    <div className="cyber-card p-6">
                        <div className="flex items-center gap-2 mb-4">
                            <Terminal className="h-5 w-5 text-cyber-accent" />
                            <h2 className="font-display text-lg text-cyber-accent">Incident Log</h2>
                        </div>
                        <LogViewer logs={logs} />
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
