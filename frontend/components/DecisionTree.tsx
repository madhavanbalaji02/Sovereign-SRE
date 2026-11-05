'use client';

import { Check, Loader2, UserCheck } from 'lucide-react';

interface DecisionTreeProps {
    currentNode: string;
}

const NODES = [
    { id: 'log_monitor', label: 'Log Monitor', description: 'Watches CloudWatch for anomalies' },
    { id: 'root_cause_analyst', label: 'Root Cause Analyst', description: 'Bedrock diagnoses the problem' },
    { id: 'code_fixer', label: 'Code Fixer', description: 'Generates a code patch' },
    { id: 'human_approval', label: 'Human Approval', description: 'Sign-off request via SNS' },
    { id: 'validator', label: 'Validator', description: 'Runs tests, opens a GitHub PR' },
];

const NODE_ORDER = NODES.map(n => n.id);

type StepStatus = 'pending' | 'active' | 'waiting' | 'completed';

export default function DecisionTree({ currentNode }: DecisionTreeProps) {
    const currentIndex = currentNode === 'complete' ? NODES.length : NODE_ORDER.indexOf(currentNode);

    const statusOf = (index: number, id: string): StepStatus => {
        if (currentIndex === -1 || index > currentIndex) return 'pending';
        if (index < currentIndex) return 'completed';
        return id === 'human_approval' ? 'waiting' : 'active';
    };

    return (
        <ol className="relative">
            {NODES.map((node, index) => {
                const status = statusOf(index, node.id);
                const isLast = index === NODES.length - 1;

                const marker = {
                    completed: 'bg-cyber-success/15 text-cyber-success ring-cyber-success/40',
                    active: 'bg-cyber-primary/15 text-cyber-primary ring-cyber-primary/50',
                    waiting: 'bg-cyber-warning/15 text-cyber-warning ring-cyber-warning/50',
                    pending: 'bg-cyber-dark text-cyber-subtle ring-cyber-border',
                }[status];

                return (
                    <li key={node.id} className="relative flex gap-3 pb-5 last:pb-0">
                        {!isLast && (
                            <span
                                className={`absolute left-[0.9375rem] top-8 bottom-0 w-px ${status === 'completed' ? 'bg-cyber-success/40' : 'bg-cyber-border'}`}
                                aria-hidden
                            />
                        )}
                        <span className={`relative z-10 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full ring-1 ${marker}`}>
                            {status === 'completed' && <Check className="h-4 w-4" />}
                            {status === 'active' && <Loader2 className="h-4 w-4 animate-spin" />}
                            {status === 'waiting' && <UserCheck className="h-4 w-4" />}
                            {status === 'pending' && <span className="text-xs font-medium tabular">{index + 1}</span>}
                        </span>
                        <div className="min-w-0 pt-1">
                            <div className="flex items-center gap-2">
                                <h3 className={`text-sm font-medium ${status === 'pending' ? 'text-cyber-muted' : 'text-cyber-text'}`}>
                                    {node.label}
                                </h3>
                                {status === 'active' && <span className="text-[11px] font-medium text-cyber-primary">Running</span>}
                                {status === 'waiting' && <span className="text-[11px] font-medium text-cyber-warning">Needs approval</span>}
                            </div>
                            <p className="mt-0.5 text-xs text-cyber-muted">{node.description}</p>
                        </div>
                    </li>
                );
            })}
        </ol>
    );
}
