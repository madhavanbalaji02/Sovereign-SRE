'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, AlertTriangle, Info, ChevronDown } from 'lucide-react';
import { useState } from 'react';

interface LogEntry {
    level: string;
    message: string;
    timestamp: string;
}

interface LogViewerProps {
    logs: LogEntry[];
}

export default function LogViewer({ logs }: LogViewerProps) {
    const [isExpanded, setIsExpanded] = useState(true);
    const [filter, setFilter] = useState<string | null>(null);

    const getLevelIcon = (level: string) => {
        switch (level.toUpperCase()) {
            case 'ERROR':
                return <AlertCircle className="h-4 w-4 text-cyber-error" />;
            case 'WARNING':
                return <AlertTriangle className="h-4 w-4 text-cyber-warning" />;
            default:
                return <Info className="h-4 w-4 text-cyber-primary" />;
        }
    };

    const getLevelColor = (level: string) => {
        switch (level.toUpperCase()) {
            case 'ERROR':
                return 'text-cyber-error';
            case 'WARNING':
                return 'text-cyber-warning';
            default:
                return 'text-cyber-primary';
        }
    };

    const formatTime = (timestamp: string) => {
        try {
            return new Date(timestamp).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                fractionalSecondDigits: 3,
            });
        } catch {
            return '--:--:--.---';
        }
    };

    const filteredLogs = filter
        ? logs.filter(log => log.level.toUpperCase() === filter)
        : logs;

    return (
        <div>
            {/* Controls */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex gap-2">
                    <button
                        onClick={() => setFilter(null)}
                        className={`px-3 py-1 text-xs rounded border transition-all ${filter === null
                                ? 'border-cyber-primary text-cyber-primary bg-cyber-primary/10'
                                : 'border-cyber-muted text-cyber-muted hover:border-cyber-primary/50'
                            }`}
                    >
                        ALL
                    </button>
                    <button
                        onClick={() => setFilter('ERROR')}
                        className={`px-3 py-1 text-xs rounded border transition-all ${filter === 'ERROR'
                                ? 'border-cyber-error text-cyber-error bg-cyber-error/10'
                                : 'border-cyber-muted text-cyber-muted hover:border-cyber-error/50'
                            }`}
                    >
                        ERROR
                    </button>
                    <button
                        onClick={() => setFilter('WARNING')}
                        className={`px-3 py-1 text-xs rounded border transition-all ${filter === 'WARNING'
                                ? 'border-cyber-warning text-cyber-warning bg-cyber-warning/10'
                                : 'border-cyber-muted text-cyber-muted hover:border-cyber-warning/50'
                            }`}
                    >
                        WARNING
                    </button>
                    <button
                        onClick={() => setFilter('INFO')}
                        className={`px-3 py-1 text-xs rounded border transition-all ${filter === 'INFO'
                                ? 'border-cyber-primary text-cyber-primary bg-cyber-primary/10'
                                : 'border-cyber-muted text-cyber-muted hover:border-cyber-primary/50'
                            }`}
                    >
                        INFO
                    </button>
                </div>

                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="flex items-center gap-1 text-cyber-muted hover:text-cyber-primary transition-colors"
                >
                    <span className="text-xs">{isExpanded ? 'Collapse' : 'Expand'}</span>
                    <ChevronDown className={`h-4 w-4 transition-transform ${isExpanded ? '' : '-rotate-90'}`} />
                </button>
            </div>

            {/* Log entries */}
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-cyber-black/50 rounded-lg border border-cyber-muted/20 overflow-hidden"
                    >
                        <div className="max-h-48 overflow-y-auto p-4 font-mono text-sm">
                            {filteredLogs.map((log, index) => (
                                <motion.div
                                    key={index}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.03 }}
                                    className="flex items-start gap-3 py-1 hover:bg-cyber-dark/30 px-2 -mx-2 rounded"
                                >
                                    <span className="text-cyber-muted text-xs min-w-[90px]">
                                        {formatTime(log.timestamp)}
                                    </span>
                                    <span className="flex-shrink-0">
                                        {getLevelIcon(log.level)}
                                    </span>
                                    <span className={`min-w-[60px] text-xs font-semibold ${getLevelColor(log.level)}`}>
                                        [{log.level}]
                                    </span>
                                    <span className="text-gray-300">{log.message}</span>
                                </motion.div>
                            ))}

                            {filteredLogs.length === 0 && (
                                <div className="text-center py-4 text-cyber-muted">
                                    No logs to display
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
