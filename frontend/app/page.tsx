'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, Brain, GitPullRequest, Terminal, Shield, Zap } from 'lucide-react';
import DecisionTree from '@/components/DecisionTree';
import ThoughtStream from '@/components/ThoughtStream';
import StatusPanel from '@/components/StatusPanel';
import LogViewer from '@/components/LogViewer';

export default function Dashboard() {
    const [isConnected, setIsConnected] = useState(false);
    const [currentNode, setCurrentNode] = useState('idle');
    const [thoughts, setThoughts] = useState<Array<{ id: string; agent: string; thought: string; timestamp: string }>>([]);
    const [logs, setLogs] = useState<Array<{ level: string; message: string; timestamp: string }>>([]);

    // Simulated WebSocket connection for demo
    useEffect(() => {
        const timer = setTimeout(() => setIsConnected(true), 1000);
        return () => clearTimeout(timer);
    }, []);

    // Demo data
    useEffect(() => {
        const demoThoughts = [
            { id: '1', agent: 'LogMonitor', thought: 'Scanning logs for anomalies...', timestamp: new Date().toISOString() },
            { id: '2', agent: 'Senior SRE', thought: 'Detected timeout pattern in API responses', timestamp: new Date().toISOString() },
            { id: '3', agent: 'Researcher', thought: 'Querying codebase for error handling patterns', timestamp: new Date().toISOString() },
        ];

        const demoLogs = [
            { level: 'INFO', message: 'System initialized', timestamp: new Date().toISOString() },
            { level: 'WARNING', message: 'High latency detected on /api/users', timestamp: new Date().toISOString() },
            { level: 'ERROR', message: 'TimeoutError: Connection to database timed out', timestamp: new Date().toISOString() },
        ];

        setThoughts(demoThoughts);
        setLogs(demoLogs);
        setCurrentNode('log_monitor');
    }, []);

    return (
        <div className="min-h-screen p-6">
            {/* Header */}
            <motion.header
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-8"
            >
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
                            <p className="text-sm text-cyber-muted">Self-Healing Infrastructure System</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                            <span className={`status-dot ${isConnected ? 'active' : 'error'}`} />
                            <span className="text-sm text-cyber-muted">
                                {isConnected ? 'Connected' : 'Connecting...'}
                            </span>
                        </div>

                        <button className="cyber-button flex items-center gap-2">
                            <Zap className="h-4 w-4" />
                            Run Pipeline
                        </button>
                    </div>
                </div>
            </motion.header>

            {/* Main Grid */}
            <div className="grid grid-cols-12 gap-6">
                {/* Left Column - Decision Tree */}
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                    className="col-span-4"
                >
                    <div className="cyber-card p-6 h-full">
                        <div className="flex items-center gap-2 mb-4">
                            <Brain className="h-5 w-5 text-cyber-secondary" />
                            <h2 className="font-display text-lg text-cyber-secondary">Agent Pipeline</h2>
                        </div>
                        <DecisionTree currentNode={currentNode} />
                    </div>
                </motion.div>

                {/* Center Column - Thought Stream */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="col-span-5"
                >
                    <div className="cyber-card p-6 h-full">
                        <div className="flex items-center gap-2 mb-4">
                            <Activity className="h-5 w-5 text-cyber-primary" />
                            <h2 className="font-display text-lg text-cyber-primary">Agent Thoughts</h2>
                        </div>
                        <ThoughtStream thoughts={thoughts} />
                    </div>
                </motion.div>

                {/* Right Column - Status Panel */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                    className="col-span-3"
                >
                    <div className="cyber-card p-6 h-full">
                        <div className="flex items-center gap-2 mb-4">
                            <GitPullRequest className="h-5 w-5 text-cyber-success" />
                            <h2 className="font-display text-lg text-cyber-success">Status</h2>
                        </div>
                        <StatusPanel
                            status="running"
                            issuesDetected={3}
                            fixesProposed={1}
                            prCreated={false}
                        />
                    </div>
                </motion.div>

                {/* Bottom Row - Log Viewer */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="col-span-12"
                >
                    <div className="cyber-card p-6">
                        <div className="flex items-center gap-2 mb-4">
                            <Terminal className="h-5 w-5 text-cyber-accent" />
                            <h2 className="font-display text-lg text-cyber-accent">System Logs</h2>
                        </div>
                        <LogViewer logs={logs} />
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
