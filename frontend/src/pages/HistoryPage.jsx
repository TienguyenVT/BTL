import { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getSessionsHistory, getSessionById } from '../services/api';
import { format, startOfDay } from 'date-fns';
import { Activity, WifiOff, Calendar, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import { toast } from 'sonner';
import SessionChart from '../components/SessionChart';

const RANGES = [
  { label: '6h', hours: 6 },
  { label: '24h', hours: 24 },
  { label: '7d', hours: 168 },
  { label: '30d', hours: 720 },
];

const labelColors = { Normal: '#22c55e', Stress: '#f59e0b', Fever: '#ef4444' };

export default function HistoryPage() {
  const [range, setRange] = useState(168);
  const [sessions, setSessions] = useState([]);
  const [sessionDetail, setSessionDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSessions, setExpandedSessions] = useState(new Set());

  useEffect(() => {
    const fetchSessions = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getSessionsHistory(range);
        setSessions(res.data || []);
      } catch (err) {
        setError(err.response?.data?.message || err.message || 'Failed to load sessions');
        toast.error('Failed to load health history');
      }
      setLoading(false);
    };
    fetchSessions();
  }, [range]);

  const toggleSession = async (sessionId) => {
    const isCurrentlyExpanded = expandedSessions.has(sessionId);

    if (isCurrentlyExpanded) {
      setExpandedSessions((prev) => {
        const next = new Set(prev);
        next.delete(sessionId);
        return next;
      });
      setSessionDetail((prevDetail) =>
        prevDetail?.sessionId === sessionId ? null : prevDetail
      );
    } else {
      setExpandedSessions((prev) => new Set(prev).add(sessionId));
      if (!sessionDetail || sessionDetail.sessionId !== sessionId) {
        setLoadingDetail(true);
        try {
          const res = await getSessionById(sessionId);
          setSessionDetail(res.data);
        } catch (err) {
          toast.error('Failed to load session details');
        } finally {
          setLoadingDetail(false);
        }
      }
    }
  };

  // Group sessions by day
  const sessionsByDay = useMemo(() => {
    const grouped = {};
    for (const session of sessions) {
      const date = startOfDay(new Date(session.startTime));
      const dayKey = format(date, 'yyyy-MM-dd');
      if (!grouped[dayKey]) {
        grouped[dayKey] = { date, sessions: [] };
      }
      grouped[dayKey].sessions.push(session);
    }
    return Object.values(grouped).sort((a, b) => b.date - a.date);
  }, [sessions]);

  // Chart data: all records from expanded sessions or first 3 sessions
  const chartSessions = useMemo(() => {
    const ids = Array.from(expandedSessions).slice(0, 3);
    if (ids.length === 0) {
      return sessions.slice(0, 3);
    }
    return sessions.filter((s) => ids.includes(s.sessionId));
  }, [sessions, expandedSessions]);

  const currentDetail = sessionDetail;

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Health History</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {sessions.length > 0
              ? `${sessions.length} phiên đo · ${sessions.reduce((a, s) => a + s.recordCount, 0)} bản ghi`
              : 'Không có dữ liệu'}
          </p>
        </div>
        <div className="flex gap-2">
          {RANGES.map((r) => (
            <button
              key={r.hours}
              onClick={() => setRange(r.hours)}
              className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                range === r.hours
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 rounded-xl p-4 bg-red-50 border border-red-200 flex items-start gap-3">
          <WifiOff size={20} className="text-red-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-800">{error}</p>
            <p className="text-xs text-red-600 mt-1">Đảm bảo backend đang chạy.</p>
          </div>
        </div>
      )}

      {/* Sessions Timeline */}
      {!loading && sessions.length > 0 && (
        <div className="mb-6 bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
            <Calendar size={16} className="text-slate-500" />
            <h2 className="font-semibold text-slate-700">Phiên đo</h2>
            <span className="text-xs text-slate-400 ml-1">({sessions.length})</span>
          </div>

          <div className="divide-y divide-slate-50">
            {sessionsByDay.map(({ date, sessions: daySessions }) => (
              <div key={format(date, 'yyyy-MM-dd')}>
                {/* Day header */}
                <div className="px-5 py-2 bg-slate-50 flex items-center gap-2">
                  <Calendar size={13} className="text-slate-400" />
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    {format(date, 'EEEE, dd/MM/yyyy')}
                  </span>
                  <span className="text-xs text-slate-400 ml-1">({daySessions.length} phiên)</span>
                </div>

                {/* Sessions for this day */}
                {daySessions.map((session) => {
                  const isExpanded = expandedSessions.has(session.sessionId);
                  return (
                    <div key={session.sessionId}>
                      <button
                        onClick={() => toggleSession(session.sessionId)}
                        className="w-full px-5 py-3 flex items-center justify-between hover:bg-slate-50/50 transition-colors text-left"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <Clock size={14} className="text-slate-400 flex-shrink-0" />
                          <span className="text-sm text-slate-600 font-mono">
                            {format(new Date(session.startTime), 'HH:mm')} –{' '}
                            {format(new Date(session.endTime), 'HH:mm')}
                          </span>
                          {session.label && (
                            <span
                              className="px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0"
                              style={{
                                backgroundColor: `${labelColors[session.label] || '#6b7280'}20`,
                                color: labelColors[session.label] || '#6b7280',
                              }}
                            >
                              {session.label}
                            </span>
                          )}
                          {session.active && (
                            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-600 flex-shrink-0">
                              Đang đo
                            </span>
                          )}
                          <span className="text-xs text-slate-400 flex-shrink-0">
                            {session.recordCount} điểm
                          </span>
                        </div>

                        <div className="flex items-center gap-4 flex-shrink-0">
                          {session.avgBpm != null && (
                            <span className="text-xs text-red-500">AVG {session.avgBpm.toFixed(0)} BPM</span>
                          )}
                          {session.avgSpo2 != null && (
                            <span className="text-xs text-blue-500">AVG {session.avgSpo2.toFixed(1)}%</span>
                          )}
                          {isExpanded ? (
                            <ChevronUp size={14} className="text-slate-400" />
                          ) : (
                            <ChevronDown size={14} className="text-slate-400" />
                          )}
                        </div>
                      </button>

                      {/* Expanded: chart + table */}
                      {isExpanded && (
                        <div className="px-5 pb-4">
                          {loadingDetail && currentDetail?.sessionId !== session.sessionId ? (
                            <div className="h-40 flex items-center justify-center text-slate-400 text-sm">
                              Đang tải chi tiết...
                            </div>
                          ) : currentDetail?.sessionId === session.sessionId ? (
                            <div className="space-y-3">
                              {/* Mini chart */}
                              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                                <SessionChart records={currentDetail.records || []} height={160} />
                              </div>
                              {/* Table */}
                              <div className="rounded-lg border border-slate-100 overflow-hidden">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="bg-slate-100 text-slate-500">
                                      <th className="text-left px-3 py-2 font-medium">Thời gian</th>
                                      <th className="text-left px-3 py-2 font-medium">BPM</th>
                                      <th className="text-left px-3 py-2 font-medium">SpO2 %</th>
                                      <th className="text-left px-3 py-2 font-medium">Nhiệt độ °C</th>
                                      <th className="text-left px-3 py-2 font-medium">GSR</th>
                                      <th className="text-left px-3 py-2 font-medium">Nhãn</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-50">
                                    {currentDetail.records?.map((r, idx) => (
                                      <tr key={r.id || idx} className="hover:bg-slate-50/50">
                                        <td className="px-3 py-2 text-slate-500 font-mono">
                                          {r.timestamp
                                            ? format(new Date(r.timestamp), 'HH:mm:ss')
                                            : r.ingestedAt
                                            ? format(new Date(r.ingestedAt), 'HH:mm:ss')
                                            : '--'}
                                        </td>
                                        <td className="px-3 py-2 font-medium text-red-600">
                                          {r.bpm != null ? r.bpm.toFixed(0) : '--'}
                                        </td>
                                        <td className="px-3 py-2 font-medium text-blue-600">
                                          {r.spo2 != null ? r.spo2.toFixed(1) : '--'}
                                        </td>
                                        <td className="px-3 py-2 font-medium text-orange-600">
                                          {r.bodyTemp != null ? r.bodyTemp.toFixed(1) : '--'}
                                        </td>
                                        <td className="px-3 py-2 font-medium text-green-600">
                                          {r.gsrAdc != null ? r.gsrAdc.toFixed(0) : '--'}
                                        </td>
                                        <td className="px-3 py-2">
                                          {r.label ? (
                                            <span
                                              className="px-1.5 py-0.5 rounded text-xs font-medium"
                                              style={{
                                                backgroundColor: `${labelColors[r.label] || '#6b7280'}20`,
                                                color: labelColors[r.label] || '#6b7280',
                                              }}
                                            >
                                              {r.label}
                                            </span>
                                          ) : '--'}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          ) : (
                            <div className="h-12 flex items-center justify-center text-slate-400 text-xs">
                              Không có chi tiết
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && sessions.length === 0 && (
        <div className="mb-6 rounded-xl border border-slate-200 bg-slate-50 p-8 text-center">
          <Activity size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-600 font-medium">Không có dữ liệu lịch sử</p>
          <p className="text-slate-400 text-sm mt-1">
            Dữ liệu sẽ xuất hiện ở đây sau khi bạn sử dụng hệ thống cảm biến.
          </p>
        </div>
      )}

      {/* Aggregated chart */}
      {sessions.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 mb-6">
          <h2 className="font-semibold text-slate-700 mb-4">Xu hướng trung bình theo phiên</h2>
          {loading ? (
            <div className="h-64 animate-pulse bg-slate-100 rounded-lg" />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart
                data={sessions.map((s) => ({
                  time: format(new Date(s.startTime), range > 24 ? 'MM/dd HH:mm' : 'HH:mm'),
                  BPM: s.avgBpm ?? 0,
                  SpO2: s.avgSpo2 ?? 0,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="BPM" stroke="#ef4444" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="SpO2" stroke="#3b82f6" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      )}
    </div>
  );
}
