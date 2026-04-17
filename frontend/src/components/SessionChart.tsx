import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import { Activity } from 'lucide-react';

interface Record {
  timestamp: string | number;
  ingestedAt?: string | number;
  bpm: number | null;
  spo2: number | null;
  bodyTemp: number | null;
  gsrAdc: number | null;
}

interface SessionChartProps {
  records: Record[];
  height?: number;
}

const SIGNAL_CONFIG = {
  BPM: {
    key: 'BPM',
    label: 'Nhip tim',
    unit: 'BPM',
    color: '#ef4444',
    domain: [40, 130] as [number, number],
  },
  SpO2: {
    key: 'SpO2',
    label: 'Nong do oxy',
    unit: '%',
    color: '#3b82f6',
    domain: [90, 102] as [number, number],
  },
  BodyTemp: {
    key: 'BodyTemp',
    label: 'Nhiet do co the',
    unit: '°C',
    color: '#f59e0b',
    domain: [35, 42] as [number, number],
  },
  GSR: {
    key: 'GSR',
    label: 'Dien da',
    unit: '',
    color: '#10b981',
    domain: [0, 1200] as [number, number],
  },
} as const;

type SignalKey = keyof typeof SIGNAL_CONFIG;

function SignalChart({
  records,
  signal,
  height,
}: {
  records: Record[];
  signal: SignalKey;
  height: number;
}) {
  const config = SIGNAL_CONFIG[signal];
  const chartData = records.map((r) => {
    const valMap: Record<SignalKey, number | null> = {
      BPM: r.bpm,
      SpO2: r.spo2,
      BodyTemp: r.bodyTemp,
      GSR: r.gsrAdc,
    };
    // ingestedAt = server time (preferred), timestamp = ESP32 device time (fallback)
    const tsSource = r.ingestedAt ?? r.timestamp ?? Date.now();
    return {
      time: format(new Date(tsSource), 'HH:mm:ss'),
      [config.key]: valMap[signal],
    };
  });

  const last = chartData.length > 0 ? chartData[chartData.length - 1][config.key] : null;

  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-semibold text-slate-700">{config.label}</span>
        {last != null ? (
          <span className="text-lg font-bold" style={{ color: config.color }}>
            {last.toFixed(signal === 'BPM' || signal === 'GSR' ? 0 : 1)}{config.unit}
          </span>
        ) : (
          <span className="text-lg text-slate-300">--{config.unit}</span>
        )}
      </div>
      {chartData.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center text-slate-400 text-xs gap-1"
          style={{ height: height - 50 }}
        >
          <Activity size={20} className="text-slate-300" />
          Chua co du lieu
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={height - 50}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#94a3b8" interval="preserveStartEnd" />
            <YAxis
              domain={config.domain}
              tick={{ fontSize: 10 }}
              stroke="#94a3b8"
              width={40}
            />
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(value) => [`${value}${config.unit}`, config.label]}
            />
            <Line
              type="monotone"
              dataKey={config.key}
              stroke={config.color}
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default function SessionChart({ records, height = 220 }: SessionChartProps) {
  const signals: SignalKey[] = ['BPM', 'SpO2', 'BodyTemp', 'GSR'];

  return (
    <div className="grid grid-cols-2 gap-4">
      {signals.map((signal) => (
        <SignalChart
          key={signal}
          records={records}
          signal={signal}
          height={height}
        />
      ))}
    </div>
  );
}
