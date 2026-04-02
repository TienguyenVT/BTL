import { useState, useEffect } from 'react';
import { Activity, Droplet, Thermometer, RefreshCw, WifiOff, Clock } from 'lucide-react';
import SessionChart from '../components/SessionChart';
import { getLiveSession, getEnvironment } from '../services/api';
import { format } from 'date-fns';

const labelColors = { Normal: '#22c55e', Stress: '#f59e0b', Fever: '#ef4444' };

export default function DashboardPage() {
  const [session, setSession] = useState(null);
  const [envData, setEnvData] = useState({ extTempC: null, extHumidityPct: null, timestamp: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [tick, setTick] = useState(0);

  // Poll live session every 1 second (direct final_result query, no rebuild dependency)
  const fetchSession = async () => {
    try {
      setError(null);
      const res = await getLiveSession();
      setSession(res.status === 204 ? null : res.data);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError(err.response?.data?.message || err.message || 'Failed to load session');
    } finally {
      setLoading(false);
      setLastUpdated(new Date());
      setTick(t => t + 1);
    }
  };

  // Poll environment every 1 second (from datalake_raw)
  const fetchEnv = async () => {
    try {
      const res = await getEnvironment();
      setEnvData(res.data || {});
    } catch (err) {
      console.error('Failed to load env:', err);
    }
  };

  useEffect(() => {
    fetchSession();
    fetchEnv();
    // Poll every 1 second using /live endpoint (direct final_result query)
    const sessionInterval = setInterval(fetchSession, 1000);
    const envInterval = setInterval(fetchEnv, 1000);
    return () => { clearInterval(sessionInterval); clearInterval(envInterval); };
  }, []);

  const records = session?.records || [];
  const latestRecord = records.length > 0 ? records[records.length - 1] : null;
  const label = latestRecord?.label || session?.label || 'No Data';
  const labelColor = labelColors[label] || '#6b7280';
  const hasData = !!latestRecord || records.length > 0;

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {lastUpdated
              ? `Cập nhật ${format(lastUpdated, 'HH:mm:ss')}`
              : loading ? 'Đang tải...' : 'Chưa có dữ liệu'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Session badge */}
          {session && (
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
              style={{
                backgroundColor: session.active ? '#f0fdf4' : '#f8fafc',
                color: session.active ? '#16a34a' : '#64748b',
                border: `1px solid ${session.active ? '#bbf7d0' : '#e2e8f0'}`,
              }}
            >
              {session.active ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                  </span>
                  Đang đo · {records.length} điểm
                </>
              ) : (
                <>
                  <Clock size={11} />
                  Đã kết thúc · {records.length} điểm
                </>
              )}
            </div>
          )}
          {/* Label badge */}
          {session?.label && (
            <span
              className="px-3 py-1.5 rounded-full text-xs font-semibold"
              style={{ backgroundColor: `${labelColor}20`, color: labelColor }}
            >
              {session.label}
            </span>
          )}
          <button
            onClick={fetchSession}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* Health Status Banner */}
      <div
        className="rounded-xl p-4 flex items-center justify-between"
        style={{ backgroundColor: `${labelColor}15`, borderLeft: `4px solid ${labelColor}` }}
      >
        <div>
          <p className="text-sm text-slate-600">Tình trạng sức khỏe</p>
          <p className="text-lg font-bold" style={{ color: labelColor }}>{label}</p>
        </div>
        <div className="flex items-center gap-6 text-right">
          {latestRecord?.bpm != null && (
            <div>
              <p className="text-xs text-slate-500">BPM</p>
              <p className="text-sm font-bold text-red-500">{latestRecord.bpm.toFixed(0)}</p>
            </div>
          )}
          {latestRecord?.spo2 != null && (
            <div>
              <p className="text-xs text-slate-500">SpO2</p>
              <p className="text-sm font-bold text-blue-500">{latestRecord.spo2.toFixed(1)}%</p>
            </div>
          )}
          {latestRecord?.bodyTemp != null && (
            <div>
              <p className="text-xs text-slate-500">Nhiệt độ</p>
              <p className="text-sm font-bold text-orange-500">{latestRecord.bodyTemp.toFixed(1)}°C</p>
            </div>
          )}
          {latestRecord?.gsrAdc != null && (
            <div>
              <p className="text-xs text-slate-500">GSR</p>
              <p className="text-sm font-bold text-emerald-500">{latestRecord.gsrAdc.toFixed(0)}</p>
            </div>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-xl p-4 bg-red-50 border border-red-200 flex items-start gap-3">
          <WifiOff size={20} className="text-red-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-800">{error}</p>
            <p className="text-xs text-red-600 mt-1">Đảm bảo backend đang chạy và MongoDB đã kết nối.</p>
          </div>
        </div>
      )}

      {/* No data placeholder */}
      {!hasData && !loading && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-12 text-center">
          <Activity size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-600 font-medium">Không có dữ liệu</p>
          <p className="text-slate-400 text-sm mt-1">Khởi động ESP32 để bắt đầu phiên đo mới.</p>
        </div>
      )}

      {/* 2x2 Chart Grid */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4">
          {[0, 1, 2, 3].map(i => (
            <div key={i} className="h-52 animate-pulse bg-slate-100 rounded-xl" />
          ))}
        </div>
      ) : (
        <SessionChart records={records} height={240} />
      )}

      {/* Environment + Session Info */}
      {session && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Environment (realtime 1s from datalake_raw) */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            <h3 className="font-semibold text-slate-700 mb-3 text-sm">Môi trường</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Thermometer size={13} className="text-orange-400" /> Nhiệt độ phòng
                </span>
                <span className="font-medium text-slate-700">
                  {envData.extTempC != null ? `${envData.extTempC.toFixed(1)} °C` : '--'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Droplet size={13} className="text-blue-400" /> Độ ẩm
                </span>
                <span className="font-medium text-slate-700">
                  {envData.extHumidityPct != null ? `${envData.extHumidityPct.toFixed(1)} %` : '--'}
                </span>
              </div>
            </div>
          </div>

          {/* Session Info */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            <h3 className="font-semibold text-slate-700 mb-3 text-sm">Phiên đo</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Bắt đầu</span>
                <span className="font-medium text-slate-700">{format(new Date(session.startTime), 'HH:mm:ss')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Kết thúc</span>
                <span className="font-medium text-slate-700">{format(new Date(session.endTime), 'HH:mm:ss')}</span>
              </div>
            </div>
          </div>

          {/* Session Stats */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            <h3 className="font-semibold text-slate-700 mb-3 text-sm">Thống kê phiên</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Điểm dữ liệu</span>
                <span className="font-medium text-slate-700">{session.recordCount}</span>
              </div>
              {session.avgBpm != null && (
                <div className="flex justify-between">
                  <span className="text-slate-500">AVG BPM</span>
                  <span className="font-medium text-red-500">{session.avgBpm.toFixed(0)}</span>
                </div>
              )}
              {session.avgSpo2 != null && (
                <div className="flex justify-between">
                  <span className="text-slate-500">AVG SpO2</span>
                  <span className="font-medium text-blue-500">{session.avgSpo2.toFixed(1)}%</span>
                </div>
              )}
            </div>
          </div>

          {/* Raw Values */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            <h3 className="font-semibold text-slate-700 mb-3 text-sm">Giá trị mới nhất</h3>
            <div className="space-y-2 text-sm">
              {latestRecord?.confidence != null && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Confidence</span>
                  <span className="font-medium text-slate-700">{(latestRecord.confidence * 100).toFixed(0)}%</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-500">Timestamp</span>
                <span className="font-medium text-slate-700 text-xs">
                  {latestRecord?.timestamp
                    ? format(new Date(latestRecord.timestamp), 'HH:mm:ss')
                    : '--'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
