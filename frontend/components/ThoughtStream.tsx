'use client';

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Brain, Search, Wrench, PlayCircle } from 'lucide-react';

interface Thought {
    id: string;
    agent: string;
    thought: string;
    timestamp: string;
}

interface ThoughtStreamProps {
    thoughts: Thought[];
}

const AGENTS: Record<string, { icon: React.ReactNode; tone: string }> = {
    'LogMonitor': { icon: <Search className="h-3.5 w-3.5" />, tone: 'text-cyber-accent bg-cyber-accent/10 ring-cyber-accent/25' },
    'Senior SRE': { icon: <Brain className="h-3.5 w-3.5" />, tone: 'text-cyber-secondary bg-cyber-secondary/10 ring-cyber-secondary/25' },
    'Researcher': { icon: <Bot className="h-3.5 w-3.5" />, tone: 'text-cyber-primary bg-cyber-primary/10 ring-cyber-primary/25' },
    'CodeFixer': { icon: <Wrench className="h-3.5 w-3.5" />, tone: 'text-cyber-success bg-cyber-success/10 ring-cyber-success/25' },
};

const formatTime = (timestamp: string) => {
    try {
        return new Date(timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
        return '--:--:--';
    }
};

export default function ThoughtStream({ thoughts }: ThoughtStreamProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Keep the newest message in view as the pipeline progresses
    useEffect(() => {
        const el = scrollRef.current;
        if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    }, [thoughts.length]);

    if (thoughts.length === 0) {
        return (
            <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-cyber-border py-12 text-center">
                <PlayCircle className="mb-3 h-8 w-8 text-cyber-subtle" />
                <p className="text-sm font-medium text-cyber-text">No agent activity yet</p>
                <p className="mt-1 max-w-[16rem] text-xs text-cyber-muted">
                    Run the live demo to watch each agent reason through a real incident.
                </p>
            </div>
        );
    }

    return (
        <div ref={scrollRef} className="max-h-[26rem] overflow-y-auto pr-1">
            <ol className="relative space-y-0.5">
                <AnimatePresence initial={false}>
                    {thoughts.map((thought, index) => {
                        const agent = AGENTS[thought.agent] ?? { icon: <Bot className="h-3.5 w-3.5" />, tone: 'text-cyber-muted bg-white/5 ring-white/10' };
                        const isLatest = index === thoughts.length - 1;
                        return (
                            <motion.li
                                key={thought.id}
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.2 }}
                                className="relative flex gap-3 rounded-lg px-2 py-2 hover:bg-white/[0.02]"
                            >
                                {index < thoughts.length - 1 && (
                                    <span className="absolute left-[1.3rem] top-9 bottom-[-0.25rem] w-px bg-cyber-border" aria-hidden />
                                )}
                                <span className={`relative z-10 mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full ring-1 ${agent.tone}`}>
                                    {agent.icon}
                                </span>
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-baseline justify-between gap-2">
                                        <span className="text-xs font-semibold text-cyber-text">{thought.agent}</span>
                                        <span className="font-mono text-[11px] text-cyber-subtle tabular">{formatTime(thought.timestamp)}</span>
                                    </div>
                                    <p className={`mt-0.5 text-[13px] leading-relaxed ${isLatest ? 'text-cyber-text' : 'text-cyber-muted'}`}>
                                        {thought.thought}
                                    </p>
                                </div>
                            </motion.li>
                        );
                    })}
                </AnimatePresence>
            </ol>
        </div>
    );
}
