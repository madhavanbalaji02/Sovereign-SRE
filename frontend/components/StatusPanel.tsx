'use client';

import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, GitPullRequest, Bug, Loader2 } from 'lucide-react';

interface StatusPanelProps {
    status: 'idle' | 'running' | 'waiting_approval' | 'completed' | 'failed';
    issuesDetected: number;
    fixesProposed: number;
    prCreated: boolean;
}

export default function StatusPanel({
    status,
    issuesDetected,
    fixesProposed,
    prCreated
}: StatusPanelProps) {
    const getStatusDisplay = () => {
        switch (status) {
            case 'running':
                return {
                    label: 'PIPELINE ACTIVE',
                    color: 'text-cyber-primary',
                    icon: <Loader2 className="h-6 w-6 animate-spin" />,
                };
            case 'waiting_approval':
                return {
                    label: 'AWAITING APPROVAL',
                    color: 'text-cyber-warning',
                    icon: <AlertTriangle className="h-6 w-6" />,
                };
            case 'completed':
                return {
                    label: 'COMPLETED',
                    color: 'text-cyber-success',
                    icon: <CheckCircle2 className="h-6 w-6" />,
                };
            case 'failed':
                return {
                    label: 'FAILED',
                    color: 'text-cyber-error',
                    icon: <Bug className="h-6 w-6" />,
                };
            default:
                return {
                    label: 'IDLE',
                    color: 'text-cyber-muted',
                    icon: <CheckCircle2 className="h-6 w-6" />,
                };
        }
    };

    const statusDisplay = getStatusDisplay();

    return (
        <div className="space-y-6">
            {/* Current Status */}
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="text-center py-4"
            >
                <div className={`inline-flex items-center gap-2 ${statusDisplay.color}`}>
                    {statusDisplay.icon}
                    <span className="font-display text-lg font-bold">{statusDisplay.label}</span>
                </div>
            </motion.div>

            {/* Stats */}
            <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded bg-cyber-dark/50 border border-cyber-muted/20">
                    <div className="flex items-center gap-2 text-cyber-error">
                        <Bug className="h-4 w-4" />
                        <span className="text-sm">Issues Detected</span>
                    </div>
                    <span className="font-display text-xl font-bold text-cyber-error">
                        {issuesDetected}
                    </span>
                </div>

                <div className="flex items-center justify-between p-3 rounded bg-cyber-dark/50 border border-cyber-muted/20">
                    <div className="flex items-center gap-2 text-cyber-primary">
                        <CheckCircle2 className="h-4 w-4" />
                        <span className="text-sm">Fixes Proposed</span>
                    </div>
                    <span className="font-display text-xl font-bold text-cyber-primary">
                        {fixesProposed}
                    </span>
                </div>

                <div className="flex items-center justify-between p-3 rounded bg-cyber-dark/50 border border-cyber-muted/20">
                    <div className="flex items-center gap-2 text-cyber-success">
                        <GitPullRequest className="h-4 w-4" />
                        <span className="text-sm">PR Created</span>
                    </div>
                    <span className={`font-display text-xl font-bold ${prCreated ? 'text-cyber-success' : 'text-cyber-muted'}`}>
                        {prCreated ? 'YES' : 'NO'}
                    </span>
                </div>
            </div>

            {/* Approval Button */}
            {status === 'waiting_approval' && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-2"
                >
                    <button className="w-full cyber-button bg-cyber-success/20 border-cyber-success text-cyber-success hover:bg-cyber-success hover:text-cyber-black">
                        ✓ Approve Fix
                    </button>
                    <button className="w-full cyber-button bg-cyber-error/20 border-cyber-error text-cyber-error hover:bg-cyber-error hover:text-cyber-black">
                        ✗ Reject
                    </button>
                </motion.div>
            )}
        </div>
    );
}
