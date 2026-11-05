'use client';

import {
    Bell, Zap, Workflow, Brain, Search, Database, Archive, Mail, Network, Server, Globe,
    KeyRound, ShieldCheck, ArrowRight, UserCheck, GitPullRequest, Cloud,
} from 'lucide-react';

interface Service {
    id: string;
    name: string;
    icon: React.ReactNode;
    role: string;
    detail: string;
}

const SERVICES: Record<string, Service> = {
    cloudwatch: {
        id: 'cloudwatch', name: 'CloudWatch', icon: <Bell className="h-4 w-4" />, role: 'Metrics & alarms',
        detail: 'Monitors service metrics and fires an alarm when a threshold is breached. The entry point for the whole pipeline.',
    },
    lambda: {
        id: 'lambda', name: 'Lambda', icon: <Zap className="h-4 w-4" />, role: 'Alarm handler',
        detail: 'Triggered by the alarm. Validates and packages the event, then starts a Step Functions execution (~150 ms cold start).',
    },
    stepfunctions: {
        id: 'stepfunctions', name: 'Step Functions', icon: <Workflow className="h-4 w-4" />, role: 'Orchestration',
        detail: 'Runs the LangGraph agent pipeline as a state machine, one state per agent, with built-in retries and failure handling.',
    },
    bedrock: {
        id: 'bedrock', name: 'Bedrock', icon: <Brain className="h-4 w-4" />, role: 'Claude Haiku inference',
        detail: 'Root-cause analysis and code-fix generation with Claude Haiku 4.5. Roughly $0.001 per incident.',
    },
    pgvector: {
        id: 'pgvector', name: 'Aurora pgvector', icon: <Search className="h-4 w-4" />, role: 'Codebase RAG',
        detail: 'Stores 1,247 codebase chunks as embeddings. The Root Cause Analyst retrieves relevant code by semantic search.',
    },
    dynamodb: {
        id: 'dynamodb', name: 'DynamoDB', icon: <Database className="h-4 w-4" />, role: 'Incident records',
        detail: 'Incident metadata: root cause, proposed fix, confidence, resolution time, cost and model used. On-demand pricing.',
    },
    s3: {
        id: 's3', name: 'S3', icon: <Archive className="h-4 w-4" />, role: 'Artifacts',
        detail: 'Code diffs, fix artifacts and agent logs under a per-incident prefix. Objects expire after 90 days.',
    },
    sns: {
        id: 'sns', name: 'SNS', icon: <Mail className="h-4 w-4" />, role: 'Human approval',
        detail: 'Emails the approver when a fix is ready. The pipeline pauses here for up to an hour before the request expires.',
    },
    apigateway: {
        id: 'apigateway', name: 'API Gateway', icon: <Network className="h-4 w-4" />, role: 'REST API',
        detail: 'Routes /api/incidents and /api/pipeline/trigger to the backend with CORS and rate limiting.',
    },
    ec2: {
        id: 'ec2', name: 'EC2', icon: <Server className="h-4 w-4" />, role: 'FastAPI backend',
        detail: 'A t3.micro running the FastAPI backend in Docker. Serves the REST API and reads incidents from DynamoDB.',
    },
    cloudfront: {
        id: 'cloudfront', name: 'CloudFront', icon: <Cloud className="h-4 w-4" />, role: 'HTTPS edge',
        detail: 'Terminates HTTPS in front of the EC2 backend so the dashboard can call it without mixed-content errors.',
    },
    amplify: {
        id: 'amplify', name: 'Amplify', icon: <Globe className="h-4 w-4" />, role: 'Dashboard hosting',
        detail: 'Hosts this Next.js dashboard as a static export on a global CDN and proxies /backend/* to the API.',
    },
    iam: {
        id: 'iam', name: 'IAM', icon: <KeyRound className="h-4 w-4" />, role: 'Least privilege',
        detail: 'A scoped role per component. Lambda: Bedrock, DynamoDB, S3 and SNS. EC2: DynamoDB read-only.',
    },
    vpc: {
        id: 'vpc', name: 'VPC', icon: <ShieldCheck className="h-4 w-4" />, role: 'Network isolation',
        detail: 'Isolates EC2 and Aurora, with databases in private subnets and security groups limiting inbound ports.',
    },
};

const LAYERS: { label: string; description: string; services: string[] }[] = [
    { label: 'Trigger', description: 'Detect and start a run', services: ['cloudwatch', 'lambda', 'stepfunctions'] },
    { label: 'AI & retrieval', description: 'Diagnose and draft a fix', services: ['bedrock', 'pgvector'] },
    { label: 'Storage', description: 'Persist results', services: ['dynamodb', 's3'] },
    { label: 'Notification', description: 'Keep a human in the loop', services: ['sns'] },
    { label: 'Serving', description: 'API and dashboard', services: ['apigateway', 'ec2', 'cloudfront', 'amplify'] },
    { label: 'Security', description: 'Access and network', services: ['iam', 'vpc'] },
];

const FLOW = [
    { icon: <Bell className="h-4 w-4" />, title: 'Alarm fires', sub: 'CloudWatch → Lambda' },
    { icon: <Workflow className="h-4 w-4" />, title: 'Pipeline starts', sub: 'Step Functions' },
    { icon: <Brain className="h-4 w-4" />, title: 'Root cause + fix', sub: 'Bedrock + pgvector RAG' },
    { icon: <UserCheck className="h-4 w-4" />, title: 'Human approval', sub: 'SNS email' },
    { icon: <GitPullRequest className="h-4 w-4" />, title: 'Validate & PR', sub: 'Tests, GitHub PR' },
    { icon: <Database className="h-4 w-4" />, title: 'Record', sub: 'DynamoDB + S3' },
];

const COSTS = [
    { service: 'EC2 t3.micro (always on)', cost: '$8.50' },
    { service: 'DynamoDB (on-demand)', cost: '$0.25' },
    { service: 'Bedrock Claude Haiku', cost: '$0.10' },
    { service: 'S3 + Lambda', cost: '$0.10' },
    { service: 'Step Functions', cost: '$0.05' },
    { service: 'API Gateway', cost: '$0.05' },
    { service: 'Aurora pgvector (paused when idle)', cost: '$0.00' },
    { service: 'Amplify + CloudFront', cost: 'Free tier' },
];

function SectionTitle({ title, sub }: { title: string; sub?: string }) {
    return (
        <div className="mb-4">
            <h2 className="text-base font-semibold text-cyber-text">{title}</h2>
            {sub && <p className="mt-0.5 text-sm text-cyber-muted">{sub}</p>}
        </div>
    );
}

export default function ArchitectureTab() {
    const serviceCount = Object.keys(SERVICES).length;
    return (
        <div className="space-y-10">
            <header>
                <h1 className="text-2xl font-semibold tracking-tight text-cyber-text">Architecture</h1>
                <p className="mt-1 max-w-2xl text-sm text-cyber-muted">
                    {serviceCount} AWS services working together to take an incident from alarm to reviewed pull request.
                </p>
            </header>

            {/* Incident flow */}
            <section>
                <SectionTitle title="Incident flow" sub="What happens between a CloudWatch alarm and a merged fix." />
                <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
                    {FLOW.map((step, i) => (
                        <li key={step.title} className="relative">
                            <div className="cyber-card h-full p-4">
                                <div className="flex items-center justify-between">
                                    <span className={`flex h-8 w-8 items-center justify-center rounded-lg ring-1 ${step.title === 'Human approval'
                                        ? 'bg-cyber-warning/10 text-cyber-warning ring-cyber-warning/25'
                                        : 'bg-cyber-primary/10 text-cyber-primary ring-cyber-primary/20'}`}>
                                        {step.icon}
                                    </span>
                                    <span className="font-mono text-xs text-cyber-subtle">0{i + 1}</span>
                                </div>
                                <p className="mt-3 text-sm font-medium text-cyber-text">{step.title}</p>
                                <p className="mt-0.5 text-xs text-cyber-muted">{step.sub}</p>
                            </div>
                            {i < FLOW.length - 1 && (
                                <ArrowRight className="absolute -right-2.5 top-1/2 z-10 hidden h-4 w-4 -translate-y-1/2 text-cyber-subtle lg:block" aria-hidden />
                            )}
                        </li>
                    ))}
                </ol>
            </section>

            {/* Services by layer */}
            <section>
                <SectionTitle title="Services" sub="Grouped by the role they play in the system." />
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {LAYERS.map(layer => (
                        <div key={layer.label} className="cyber-card overflow-hidden">
                            <div className="flex items-baseline justify-between border-b border-cyber-border bg-white/[0.015] px-5 py-3">
                                <p className="text-sm font-semibold text-cyber-text">{layer.label}</p>
                                <p className="text-xs text-cyber-muted">{layer.description}</p>
                            </div>
                            <ul className="divide-y divide-cyber-border">
                                {layer.services.map(id => {
                                    const s = SERVICES[id];
                                    return (
                                        <li key={id} className="flex gap-3 px-5 py-4">
                                            <span className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-white/[0.04] text-cyber-muted ring-1 ring-cyber-border">
                                                {s.icon}
                                            </span>
                                            <div className="min-w-0">
                                                <p className="text-sm font-medium text-cyber-text">
                                                    {s.name} <span className="font-normal text-cyber-muted">· {s.role}</span>
                                                </p>
                                                <p className="mt-1 text-xs leading-relaxed text-cyber-muted">{s.detail}</p>
                                            </div>
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>
                    ))}
                </div>
            </section>

            {/* Cost */}
            <section>
                <SectionTitle title="Monthly cost" sub="Estimated for low-traffic demo usage." />
                <div className="cyber-card max-w-2xl overflow-hidden">
                    <table className="w-full text-sm">
                        <tbody className="divide-y divide-cyber-border">
                            {COSTS.map(({ service, cost }) => (
                                <tr key={service}>
                                    <td className="px-5 py-2.5 text-cyber-muted">{service}</td>
                                    <td className="px-5 py-2.5 text-right font-medium text-cyber-text tabular">{cost}</td>
                                </tr>
                            ))}
                        </tbody>
                        <tfoot>
                            <tr className="border-t border-cyber-border bg-white/[0.02]">
                                <td className="px-5 py-3 font-medium text-cyber-text">Total</td>
                                <td className="px-5 py-3 text-right font-semibold text-cyber-text tabular">≈ $9.10 / month</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
                <p className="mt-2 text-xs text-cyber-muted">Nearly all of the cost is the always-on EC2 instance; the AI pipeline itself costs cents.</p>
            </section>
        </div>
    );
}
