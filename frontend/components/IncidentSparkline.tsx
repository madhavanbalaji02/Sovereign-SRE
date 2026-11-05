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
    memory_anomaly: '#A78BFA',
    cpu_anomaly: '#6AA6FF',
    network_delay: '#F5B544',
    pod_failure: '#F2555A',
    disk_anomaly: '#38BDF8',
    io_anomaly: '#38BDF8',
};

export default function IncidentSparkline({ data, anomalyType, baseline, peak }: Props) {
    if (!data || data.length === 0) return null;

    const color = COLOR_MAP[anomalyType] ?? '#6AA6FF';
    const faultStart = data.findIndex(p => p.t >= 0);
    const faultEnd = data.findIndex(p => p.t >= 12);
    const recoveryPoint = data.findIndex(p => p.t >= 15 && p.v < (peak ?? 80) * 0.7);

    const faultStartT = faultStart >= 0 ? data[faultStart].t : 0;
    const faultEndT = faultEnd >= 0 ? data[faultEnd].t : 12;

    return (
        <ResponsiveContainer width="100%" height={120}>
            <LineChart data={data} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />

                {/* Red shaded anomaly window */}
                <ReferenceArea
                    x1={faultStartT}
                    x2={faultEndT}
                    fill="rgba(242,85,90,0.08)"
                    stroke="rgba(242,85,90,0.25)"
                    strokeWidth={1}
                />

                {/* Baseline reference line */}
                {baseline != null && (
                    <ReferenceLine
                        y={baseline}
                        stroke="rgba(61,214,140,0.45)"
                        strokeDasharray="4 4"
                        label={{ value: 'baseline', position: 'insideTopLeft', fontSize: 10, fill: '#3DD68C' }}
                    />
                )}

                <XAxis
                    dataKey="t"
                    tick={{ fontSize: 10, fill: '#5C667A' }} axisLine={{ stroke: '#232937' }} tickLine={false}
                    tickFormatter={v => `${v}m`}
                    interval={5}
                />
                <YAxis
                    tick={{ fontSize: 10, fill: '#5C667A' }} axisLine={{ stroke: '#232937' }} tickLine={false}
                    tickFormatter={v => `${v}%`}
                    domain={['auto', 'auto']}
                />
                <Tooltip
                    contentStyle={{
                        background: '#151922',
                        border: '1px solid #2E3546',
                        borderRadius: 8,
                        fontSize: 12,
                        color: '#E6E9EF',
                    }}
                    formatter={(v) => [`${Number(v).toFixed(1)}%`, anomalyType.replace('_', ' ')]}

                    labelFormatter={l => `t=${l}min`}
                />
                <Line
                    type="monotone"
                    dataKey="v"
                    stroke={color}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3, fill: color }}
                />
                {/* Green recovery dot */}
                {recoveryPoint >= 0 && (
                    <ReferenceLine
                        x={data[recoveryPoint].t}
                        stroke="rgba(61,214,140,0.6)"
                        strokeWidth={1}
                        strokeDasharray="3 3"
                        label={{ value: 'recovered', position: 'insideTopRight', fontSize: 10, fill: '#3DD68C' }}
                    />
                )}
            </LineChart>
        </ResponsiveContainer>
    );
}
