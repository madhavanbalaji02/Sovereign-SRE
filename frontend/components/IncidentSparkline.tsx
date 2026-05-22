'use client';

import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    ReferenceLine, ReferenceArea, ResponsiveContainer,
} from 'recharts';

interface SparkPoint {
    t: number;
    v: number;
}

interface Props {
    data: SparkPoint[];
    anomalyType: string;
    baseline?: number;
    peak?: number;
}

const COLOR_MAP: Record<string, string> = {
    memory_anomaly: '#ff00ff',
    cpu_anomaly: '#ff4444',
    network_delay: '#ffaa00',
    pod_failure: '#ff6600',
    disk_anomaly: '#aa44ff',
    io_anomaly: '#44aaff',
};

export default function IncidentSparkline({ data, anomalyType, baseline, peak }: Props) {
    if (!data || data.length === 0) return null;

    const color = COLOR_MAP[anomalyType] ?? '#00ffff';
    const faultStart = data.findIndex(p => p.t >= 0);
    const faultEnd = data.findIndex(p => p.t >= 12);
    const recoveryPoint = data.findIndex(p => p.t >= 15 && p.v < (peak ?? 80) * 0.7);

    const faultStartT = faultStart >= 0 ? data[faultStart].t : 0;
    const faultEndT = faultEnd >= 0 ? data[faultEnd].t : 12;

    return (
        <ResponsiveContainer width="100%" height={90}>
            <LineChart data={data} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />

                {/* Red shaded anomaly window */}
                <ReferenceArea
                    x1={faultStartT}
                    x2={faultEndT}
                    fill="rgba(255,50,50,0.12)"
                    stroke="rgba(255,50,50,0.3)"
                    strokeWidth={1}
                />

                {/* Baseline reference line */}
                {baseline != null && (
                    <ReferenceLine
                        y={baseline}
                        stroke="rgba(0,255,136,0.4)"
                        strokeDasharray="4 4"
                        label={{ value: 'base', position: 'insideTopLeft', fontSize: 8, fill: '#00ff88' }}
                    />
                )}

                <XAxis
                    dataKey="t"
                    tick={{ fontSize: 8, fill: '#666' }}
                    tickFormatter={v => `${v}m`}
                    interval={5}
                />
                <YAxis
                    tick={{ fontSize: 8, fill: '#666' }}
                    tickFormatter={v => `${v}%`}
                    domain={['auto', 'auto']}
                />
                <Tooltip
                    contentStyle={{
                        background: '#0a0a0f',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 4,
                        fontSize: 10,
                        color: '#ccc',
                    }}
                    formatter={(v) => [`${Number(v).toFixed(1)}%`, anomalyType.replace('_', ' ')]}

                    labelFormatter={l => `t=${l}min`}
                />
                <Line
                    type="monotone"
                    dataKey="v"
                    stroke={color}
                    strokeWidth={1.5}
                    dot={false}
                    activeDot={{ r: 3, fill: color }}
                />
                {/* Green recovery dot */}
                {recoveryPoint >= 0 && (
                    <ReferenceLine
                        x={data[recoveryPoint].t}
                        stroke="rgba(0,255,136,0.6)"
                        strokeWidth={2}
                        label={{ value: '✓', position: 'top', fontSize: 10, fill: '#00ff88' }}
                    />
                )}
            </LineChart>
        </ResponsiveContainer>
    );
}
