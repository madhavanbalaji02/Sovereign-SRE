'use client';

import { motion } from 'framer-motion';
import { CheckCircle, Circle, Loader2, User } from 'lucide-react';

interface DecisionTreeProps {
    currentNode: string;
}

const NODES = [
    {
        id: 'log_monitor',
        label: 'Log Monitor',
        description: 'Watches CloudWatch for anomalies',
    },
    {
        id: 'root_cause_analyst',
        label: 'Root Cause Analyst',
        description: 'Bedrock AI diagnoses the problem',
    },
    {
        id: 'code_fixer',
        label: 'Code Fixer',
        description: 'Generates a code patch automatically',
    },
    {
        id: 'human_approval',
        label: 'Human Approval',
        description: 'Emails you for sign-off via SNS',
    },
    {
        id: 'validator',
        label: 'Validator',
        description: 'Runs tests, creates GitHub PR',
    },
];

const NODE_ORDER = NODES.map(n => n.id);

export default function DecisionTree({ currentNode }: DecisionTreeProps) {
    const currentIndex = NODE_ORDER.indexOf(currentNode);

    const getStatus = (index: number) => {
        if (currentIndex === -1) return 'pending';
        if (index < currentIndex) return 'completed';
        if (index === currentIndex) return 'active';
        return 'pending';
    };

    const getIcon = (status: string, nodeId: string) => {
        if (nodeId === 'human_approval' && status === 'active') {
            return <User className="h-5 w-5 animate-pulse" />;
        }
        switch (status) {
            case 'completed': return <CheckCircle className="h-5 w-5" />;
            case 'active': return <Loader2 className="h-5 w-5 animate-spin" />;
            default: return <Circle className="h-5 w-5" />;
        }
    };

    const getColors = (status: string, nodeId: string) => {
        if (nodeId === 'human_approval' && status === 'active') {
            return 'border-cyber-warning text-cyber-warning bg-cyber-warning/10 shadow-[0_0_12px_rgba(255,170,0,0.3)]';
        }
        switch (status) {
            case 'completed': return 'border-cyber-success text-cyber-success bg-cyber-success/10';
            case 'active': return 'border-cyber-primary text-cyber-primary bg-cyber-primary/10 shadow-neon-cyan';
            default: return 'border-cyber-muted/40 text-cyber-muted bg-cyber-dark/50';
        }
    };

    return (
        <div className="space-y-3">
            {NODES.map((node, index) => {
                const status = getStatus(index);
                const colors = getColors(status, node.id);

                return (
                    <motion.div
                        key={node.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.08 }}
                    >
                        {index > 0 && (
                            <div className="flex justify-center -my-1.5">
                                <div className={`h-4 w-px ${index <= currentIndex && currentIndex !== -1 ? 'bg-cyber-success' : 'bg-cyber-muted/30'}`} />
                            </div>
                        )}
                        <div className={`relative flex items-center gap-3 p-3 rounded-lg border-2 transition-all duration-300 ${colors}`}>
                            <div className="flex-shrink-0">{getIcon(status, node.id)}</div>
                            <div className="flex-grow min-w-0">
                                <h3 className="font-display text-sm font-semibold leading-tight">{node.label}</h3>
                                <p className="text-xs opacity-60 mt-0.5 leading-tight">{node.description}</p>
                            </div>
                            {status === 'active' && (
                                <motion.div
                                    className="absolute -right-1 -top-1 w-2.5 h-2.5 bg-current rounded-full"
                                    animate={{ scale: [1, 1.6, 1], opacity: [1, 0.6, 1] }}
                                    transition={{ repeat: Infinity, duration: 1.4 }}
                                />
                            )}
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}
