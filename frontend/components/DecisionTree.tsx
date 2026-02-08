'use client';

import { motion } from 'framer-motion';
import { CheckCircle, Circle, Loader2, AlertCircle, User } from 'lucide-react';

interface DecisionTreeProps {
    currentNode: string;
}

interface NodeInfo {
    id: string;
    label: string;
    description: string;
}

const nodes: NodeInfo[] = [
    { id: 'log_monitor', label: 'Log Monitor', description: 'Scanning for anomalies' },
    { id: 'root_cause_analyst', label: 'Root Cause Analyst', description: 'Diagnosing issues' },
    { id: 'code_fixer', label: 'Code Fixer', description: 'Generating patches' },
    { id: 'human_approval', label: 'Human Approval', description: 'Awaiting confirmation' },
    { id: 'validator', label: 'Validator', description: 'Running tests' },
];

export default function DecisionTree({ currentNode }: DecisionTreeProps) {
    const currentIndex = nodes.findIndex(n => n.id === currentNode);

    const getNodeStatus = (index: number) => {
        if (index < currentIndex) return 'completed';
        if (index === currentIndex) return 'active';
        return 'pending';
    };

    const getNodeIcon = (status: string, nodeId: string) => {
        if (nodeId === 'human_approval') {
            return <User className="h-5 w-5" />;
        }

        switch (status) {
            case 'completed':
                return <CheckCircle className="h-5 w-5" />;
            case 'active':
                return <Loader2 className="h-5 w-5 animate-spin" />;
            default:
                return <Circle className="h-5 w-5" />;
        }
    };

    const getNodeColors = (status: string) => {
        switch (status) {
            case 'completed':
                return 'border-cyber-success text-cyber-success bg-cyber-success/10';
            case 'active':
                return 'border-cyber-primary text-cyber-primary bg-cyber-primary/10 shadow-neon-cyan';
            default:
                return 'border-cyber-muted text-cyber-muted bg-cyber-dark';
        }
    };

    return (
        <div className="space-y-4">
            {nodes.map((node, index) => {
                const status = getNodeStatus(index);
                const colors = getNodeColors(status);

                return (
                    <motion.div
                        key={node.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                    >
                        {/* Connector line */}
                        {index > 0 && (
                            <div className="flex justify-center -my-2">
                                <div
                                    className={`h-4 w-0.5 ${index <= currentIndex ? 'bg-cyber-success' : 'bg-cyber-muted'
                                        }`}
                                />
                            </div>
                        )}

                        {/* Node */}
                        <div
                            className={`
                relative flex items-center gap-4 p-4 rounded-lg border-2 
                transition-all duration-300 ${colors}
              `}
                        >
                            {/* Icon */}
                            <div className="flex-shrink-0">
                                {getNodeIcon(status, node.id)}
                            </div>

                            {/* Content */}
                            <div className="flex-grow">
                                <h3 className="font-display text-sm font-semibold">{node.label}</h3>
                                <p className="text-xs opacity-70">{node.description}</p>
                            </div>

                            {/* Active indicator */}
                            {status === 'active' && (
                                <motion.div
                                    className="absolute -right-1 -top-1 w-3 h-3 bg-cyber-primary rounded-full"
                                    animate={{ scale: [1, 1.5, 1] }}
                                    transition={{ repeat: Infinity, duration: 1.5 }}
                                />
                            )}
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}
