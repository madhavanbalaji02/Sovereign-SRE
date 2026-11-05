'use client';

import { AlertTriangle, CheckCircle2, GitPullRequest, Bug, Loader2, Circle, FileCode2 } from 'lucide-react';

interface StatusPanelProps {
    status: 'idle' | 'running' | 'waiting_approval' | 'completed' | 'failed';
    issuesDetected: number;
    fixesProposed: number;
    prCreated: boolean;
}

const STATUS = {
    idle: { label: 'Idle', tone: 'text-cyber-muted bg-white/5 ring-white/10', icon: <Circle className="h-3.5 w-3.5" /> },
    running: { label: 'Pipeline running', tone: 'text-cyber-primary bg-cyber-primary/10 ring-cyber-primary/30', icon: <Loader2 className="h-3.5 w-3.5 animate-spin" /> },
    waiting_approval: { label: 'Awaiting approval', tone: 'text-cyber-warning bg-cyber-warning/10 ring-cyber-warning/30', icon: <AlertTriangle className="h-3.5 w-3.5" /> },
    completed: { label: 'Completed', tone: 'text-cyber-success bg-cyber-success/10 ring-cyber-success/30', icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
    failed: { label: 'Failed', tone: 'text-cyber-error bg-cyber-error/10 ring-cyber-error/30', icon: <Bug className="h-3.5 w-3.5" /> },
} as const;

function Row({ icon, label, value, valueClass }: { icon: React.ReactNode; label: string; value: string; valueClass?: string }) {
    return (
        <div className="flex items-center justify-between py-2.5">
            <div className="flex items-center gap-2 text-sm text-cyber-muted">
                <span className="text-cyber-subtle">{icon}</span>
                {label}
            </div>
            <span className={`text-sm font-semibold tabular ${valueClass ?? 'text-cyber-text'}`}>{value}</span>
        </div>
    );
}

export default function StatusPanel({ status, issuesDetected, fixesProposed, prCreated }: StatusPanelProps) {
    const s = STATUS[status];
    return (
        <div>
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium uppercase tracking-wide ring-1 ${s.tone}`}>
                {s.icon}
                {s.label}
            </span>
            <div className="mt-3 divide-y divide-cyber-border">
                <Row icon={<Bug className="h-4 w-4" />} label="Issues detected" value={String(issuesDetected)} valueClass={issuesDetected > 0 ? 'text-cyber-error' : undefined} />
                <Row icon={<FileCode2 className="h-4 w-4" />} label="Fixes proposed" value={String(fixesProposed)} />
                <Row icon={<GitPullRequest className="h-4 w-4" />} label="PR created" value={prCreated ? 'Yes' : 'No'} valueClass={prCreated ? 'text-cyber-success' : 'text-cyber-muted'} />
            </div>
        </div>
    );
}
