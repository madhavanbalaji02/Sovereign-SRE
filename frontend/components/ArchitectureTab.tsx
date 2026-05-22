'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

interface Service {
    id: string;
    name: string;
    icon: string;
    category: string;
    color: string;
    tooltip: string;
}

const SERVICES: Service[] = [
    {
        id: 'cloudwatch',
        name: 'CloudWatch',
        icon: '📊',
        category: 'trigger',
        color: 'border-cyber-warning text-cyber-warning',
        tooltip: 'Amazon CloudWatch — Monitors metrics and fires alarms when thresholds are breached. The entry point for the entire Sovereign-SRE pipeline.',
    },
    {
        id: 'lambda',
        name: 'AWS Lambda',
        icon: '⚡',
        category: 'trigger',
        color: 'border-cyber-accent text-cyber-accent',
        tooltip: 'AWS Lambda — Stateless function triggered by CloudWatch alarms. Validates the event, packages it, and starts a Step Functions execution. Cold start: ~150ms.',
    },
    {
        id: 'stepfunctions',
        name: 'Step Functions',
        icon: '🔄',
        category: 'trigger',
        color: 'border-cyber-primary text-cyber-primary',
        tooltip: 'AWS Step Functions — Orchestrates the multi-step LangGraph agent pipeline. Each agent is a state in the state machine. Handles retries and failures automatically.',
    },
    {
        id: 'bedrock',
        name: 'Amazon Bedrock',
        icon: '🧠',
        category: 'ai',
        color: 'border-cyber-secondary text-cyber-secondary',
        tooltip: 'Amazon Bedrock (Claude Haiku) — Powers AI-driven root cause analysis and code fix generation. Model: us.anthropic.claude-haiku-4-5-20251001-v1:0. Cost: ~$0.001 per incident.',
    },
    {
        id: 'pgvector',
        name: 'Aurora pgvector',
        icon: '🔍',
        category: 'ai',
        color: 'border-cyber-secondary text-cyber-secondary',
        tooltip: 'Amazon Aurora (pgvector) — Stores 1,247 codebase chunks as vector embeddings. The Root Cause Analyst agent queries this for relevant code context via semantic search.',
    },
    {
        id: 's3',
        name: 'Amazon S3',
        icon: '🪣',
        category: 'storage',
        color: 'border-cyber-warning text-cyber-warning',
        tooltip: 'Amazon S3 — Stores code diffs, fix artifacts, and agent execution logs. Each incident gets a dedicated prefix. Lifecycle policy expires objects after 90 days.',
    },
    {
        id: 'dynamodb',
        name: 'DynamoDB',
        icon: '💾',
        category: 'storage',
        color: 'border-cyber-warning text-cyber-warning',
        tooltip: 'Amazon DynamoDB — Stores incident records with full metadata: root cause, proposed fix, confidence score, resolution time, cost, and Bedrock model used. On-demand pricing.',
    },
    {
        id: 'sns',
        name: 'Amazon SNS',
        icon: '📧',
        category: 'notify',
        color: 'border-cyber-error text-cyber-error',
        tooltip: 'Amazon SNS — Sends human approval email when a fix is ready. The pipeline pauses at this step, waiting up to 1 hour for approval before auto-expiring.',
    },
    {
        id: 'apigateway',
        name: 'API Gateway',
        icon: '🚪',
        category: 'infra',
        color: 'border-cyber-primary text-cyber-primary',
        tooltip: 'Amazon API Gateway — REST API fronting the EC2 backend. Handles CORS, rate limiting, and routes /api/incidents and /api/pipeline/trigger endpoints.',
    },
    {
        id: 'ec2',
        name: 'Amazon EC2',
        icon: '🖥️',
        category: 'infra',
        color: 'border-cyber-primary text-cyber-primary',
        tooltip: 'Amazon EC2 (t3.micro) — Runs the FastAPI backend server in Docker. Serves the REST API, polls DynamoDB, and streams agent thoughts. ~$8/month.',
    },
    {
        id: 'amplify',
        name: 'AWS Amplify',
        icon: '🌐',
        category: 'infra',
        color: 'border-cyber-success text-cyber-success',
        tooltip: 'AWS Amplify — Hosts the Next.js static dashboard. Auto-deploys on GitHub push via GitHub Actions. CDN-served globally. Free tier covers this project.',
    },
    {
        id: 'iam',
        name: 'AWS IAM',
        icon: '🔐',
        category: 'security',
        color: 'border-cyber-muted text-cyber-muted',
        tooltip: 'AWS IAM — Least-privilege roles for each component. Lambda role: Bedrock+DynamoDB+S3+SNS. EC2 role: DynamoDB read-only. No wildcard permissions anywhere.',
    },
    {
        id: 'vpc',
        name: 'Amazon VPC',
        icon: '🛡️',
        category: 'security',
        color: 'border-cyber-muted text-cyber-muted',
        tooltip: 'Amazon VPC — Network isolation for EC2 and Aurora. Private subnets for databases. Security groups restrict inbound to port 8000 from API Gateway only.',
    },
];

const LAYER_CONFIG: { id: string; label: string; services: string[]; arrow?: boolean }[] = [
    { id: 'trigger', label: 'Trigger Layer', services: ['cloudwatch', 'lambda', 'stepfunctions'], arrow: true },
    { id: 'ai', label: 'AI & RAG Layer', services: ['bedrock', 'pgvector'], arrow: true },
    { id: 'storage', label: 'Storage Layer', services: ['dynamodb', 's3'], arrow: true },
    { id: 'notify', label: 'Notification Layer', services: ['sns'], arrow: true },
    { id: 'infra', label: 'Infrastructure', services: ['apigateway', 'ec2', 'amplify'], arrow: false },
    { id: 'security', label: 'Security & Networking', services: ['iam', 'vpc'], arrow: false },
];

function ServiceBox({ service, onClick }: { service: Service; onClick: () => void }) {
    return (
        <motion.button
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.97 }}
            onClick={onClick}
            className={`cyber-card border ${service.color} p-4 text-left transition-all hover:shadow-lg cursor-pointer min-w-[140px]`}
        >
            <div className="text-2xl mb-2">{service.icon}</div>
            <div className={`font-display text-xs font-bold ${service.color.split(' ')[1]}`}>{service.name}</div>
            <div className="text-cyber-muted text-xs mt-1 opacity-60">Click for details</div>
        </motion.button>
    );
}

export default function ArchitectureTab() {
    const [selected, setSelected] = useState<Service | null>(null);

    const getServiceById = (id: string) => SERVICES.find(s => s.id === id)!;

    return (
        <div className="relative">
            <div className="mb-6">
                <h2 className="font-display text-xl text-cyber-primary text-glow-cyan mb-1">AWS Architecture</h2>
                <p className="text-sm text-cyber-muted">
                    13 AWS services working together to deliver autonomous incident resolution. Click any service for details.
                </p>
            </div>

            <div className="space-y-6">
                {LAYER_CONFIG.map((layer, li) => (
                    <div key={layer.id}>
                        <div className="flex items-center gap-3 mb-3">
                            <div className="h-px flex-grow bg-cyber-muted/20" />
                            <span className="text-xs font-display text-cyber-muted tracking-widest uppercase px-2">{layer.label}</span>
                            <div className="h-px flex-grow bg-cyber-muted/20" />
                        </div>
                        <div className="flex flex-wrap gap-4">
                            {layer.services.map((sid, i) => {
                                const svc = getServiceById(sid);
                                return (
                                    <div key={sid} className="flex items-center gap-3">
                                        <ServiceBox service={svc} onClick={() => setSelected(svc)} />
                                        {i < layer.services.length - 1 && (
                                            <span className="text-cyber-primary text-xl font-bold opacity-60">→</span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                        {layer.arrow && li < LAYER_CONFIG.length - 1 && (
                            <div className="flex justify-center mt-4">
                                <div className="flex flex-col items-center gap-0.5">
                                    <div className="w-px h-6 bg-cyber-primary/40" />
                                    <div className="w-0 h-0 border-l-4 border-r-4 border-t-8 border-l-transparent border-r-transparent border-t-cyber-primary/40" />
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Cost summary */}
            <div className="mt-8 cyber-card border border-cyber-success/30 p-4">
                <h3 className="font-display text-sm text-cyber-success mb-3">Monthly Cost Breakdown</h3>
                <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                    {[
                        { service: 'EC2 t3.micro', cost: '~$8.50' },
                        { service: 'Bedrock Claude Haiku', cost: '~$0.10' },
                        { service: 'DynamoDB (on-demand)', cost: '~$0.25' },
                        { service: 'Step Functions', cost: '~$0.05' },
                        { service: 'S3 + Lambda', cost: '~$0.10' },
                        { service: 'Aurora pgvector', cost: '~$0.00*' },
                        { service: 'Amplify', cost: 'Free tier' },
                        { service: 'API Gateway', cost: '~$0.05' },
                    ].map(({ service, cost }) => (
                        <div key={service} className="flex justify-between bg-cyber-dark/50 rounded px-3 py-2">
                            <span className="text-cyber-muted">{service}</span>
                            <span className="text-cyber-success font-bold">{cost}</span>
                        </div>
                    ))}
                </div>
                <p className="text-cyber-muted text-xs mt-3">* Aurora paused when idle. Total: ~$1/month for low-traffic demo usage.</p>
            </div>

            {/* Tooltip modal */}
            <AnimatePresence>
                {selected && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-6"
                        onClick={() => setSelected(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="cyber-card border border-cyber-primary/50 p-6 max-w-md w-full"
                            onClick={e => e.stopPropagation()}
                        >
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <span className="text-3xl">{selected.icon}</span>
                                    <h3 className={`font-display text-lg font-bold ${selected.color.split(' ')[1]}`}>{selected.name}</h3>
                                </div>
                                <button onClick={() => setSelected(null)} className="text-cyber-muted hover:text-cyber-primary transition-colors">
                                    <X className="h-5 w-5" />
                                </button>
                            </div>
                            <p className="text-sm text-gray-300 leading-relaxed">{selected.tooltip}</p>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
