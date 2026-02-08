'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Brain, Search, Wrench } from 'lucide-react';

interface Thought {
    id: string;
    agent: string;
    thought: string;
    timestamp: string;
}

interface ThoughtStreamProps {
    thoughts: Thought[];
}

const agentIcons: Record<string, React.ReactNode> = {
    'LogMonitor': <Search className="h-4 w-4" />,
    'Senior SRE': <Brain className="h-4 w-4" />,
    'Researcher': <Bot className="h-4 w-4" />,
    'CodeFixer': <Wrench className="h-4 w-4" />,
};

const agentColors: Record<string, string> = {
    'LogMonitor': 'text-cyber-accent border-cyber-accent/30 bg-cyber-accent/5',
    'Senior SRE': 'text-cyber-secondary border-cyber-secondary/30 bg-cyber-secondary/5',
    'Researcher': 'text-cyber-primary border-cyber-primary/30 bg-cyber-primary/5',
    'CodeFixer': 'text-cyber-success border-cyber-success/30 bg-cyber-success/5',
};

export default function ThoughtStream({ thoughts }: ThoughtStreamProps) {
    const formatTime = (timestamp: string) => {
        try {
            return new Date(timestamp).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            });
        } catch {
            return '--:--:--';
        }
    };

    return (
        <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
            <AnimatePresence>
                {thoughts.map((thought, index) => {
                    const color = agentColors[thought.agent] || 'text-cyber-muted border-cyber-muted/30';
                    const icon = agentIcons[thought.agent] || <Bot className="h-4 w-4" />;

                    return (
                        <motion.div
                            key={thought.id}
                            initial={{ opacity: 0, y: 20, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={{ delay: index * 0.05 }}
                            className={`p-4 rounded-lg border ${color}`}
                        >
                            {/* Header */}
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    {icon}
                                    <span className="font-display text-sm font-semibold">
                                        {thought.agent}
                                    </span>
                                </div>
                                <span className="text-xs opacity-50 font-mono">
                                    {formatTime(thought.timestamp)}
                                </span>
                            </div>

                            {/* Thought content */}
                            <div className="terminal-text opacity-90">
                                <span className="text-cyber-muted mr-2">&gt;</span>
                                {thought.thought}
                            </div>

                            {/* Typing indicator for latest thought */}
                            {index === thoughts.length - 1 && (
                                <motion.div
                                    className="flex gap-1 mt-2"
                                    animate={{ opacity: [0.3, 1, 0.3] }}
                                    transition={{ repeat: Infinity, duration: 1.5 }}
                                >
                                    <span className="w-2 h-2 bg-current rounded-full" />
                                    <span className="w-2 h-2 bg-current rounded-full" style={{ animationDelay: '0.2s' }} />
                                    <span className="w-2 h-2 bg-current rounded-full" style={{ animationDelay: '0.4s' }} />
                                </motion.div>
                            )}
                        </motion.div>
                    );
                })}
            </AnimatePresence>

            {thoughts.length === 0 && (
                <div className="text-center py-8 text-cyber-muted">
                    <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm">Waiting for agent activity...</p>
                </div>
            )}
        </div>
    );
}
