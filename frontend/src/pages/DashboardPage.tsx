import { useState, useEffect, useCallback } from 'react';
import { Activity, Droplet, Thermometer, RefreshCw, WifiOff, Clock, Cpu, ChevronDown, AlertTriangle, X } from 'lucide-react';
import SessionChart from '../components/SessionChart';
import { getLiveSession, getEnvironment, getDevices, getUnreadAlerts, markAlertRead } from '../services/api';
import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';

const labelColors = { Normal: '#22c55e', Stress: '#f59e0b', Fever: '#ef4444' };

const STORAGE_KEY_SELECTED_DEVICE = 'dashboard_selected_device_id';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [envData, setEnvData] = useState({ extTempC: null, extHumidityPct: null, timestamp: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [tick, setTick] = useState(0);
  const [hasDevices, setHasDevices] = useState(null);
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(() => localStorage.getItem(STORAGE_KEY_SELECTED_DEVICE) || '');
  const userId = localStorage.getItem('backendUserId');
  const [alerts, setAlerts] = useState([]);
  const [alertDismissed, setAlertDismissed] = useState(false);

  // Check if user has registered devices
  useEffect(() => {
    const checkDevices = async () => {
      if (!userId) {
        setHasDevices(false);
        setDevices([]);
        return;
      }
      try {
        const res = await getDevices(userId);
        const deviceList = res.data || [];
        setDevices(deviceList);
        setHasDevices(deviceList.length > 0);
        // Nếu device đã chọn trước đó không còn trong danh sách → reset
        if (deviceList.length > 0 && !deviceList.find(d => d.id === selectedDeviceId)) {
          setSelectedDeviceId('');
          localStorage.removeItem(STORAGE_KEY_SELECTED_DEVICE);
        }
      } catch {
        setHasDevices(false);
        setDevices([]);
      }
    };
    checkDevices();
  }, [userId]);

  // Poll live session every 1 second (direct final_result query, no rebuild dependency)
  const fetchSession = useCallback(async () => {
    if (!userId || hasDevices === false) {
      setLoading(false);
      return;
    }
    try {
      setError(null);
      const res = await getLiveSession(userId, selectedDeviceId || null);
      setSession(res.status === 204 ? null : res.data);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError(err.response?.data?.message || err.message || 'Failed to load session');
    } finally {
      setLoading(false);
      setLastUpdated(new Date());
      setTick(t => t + 1);
    }
  }, [userId, hasDevices, selectedDeviceId]);

  // Poll environment every 1 second (from datalake_raw)
  const fetchEnv = async () => {
    try {
      const res = await getEnvironment();
      setEnvData(res.data || {});
    } catch (err) {
      console.error('Failed to load env:', err);
    }
  };

  // Poll alerts every 5 seconds
  const fetchAlerts = useCallback(async () => {
    if (!userId || alertDismissed) return;
    try {
      const res = await getUnreadAlerts(userId);
      setAlerts(res.data || []);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    }
  }, [userId, alertDismissed]);

  const dismissAlert = async (alertId) => {
    try {
      await markAlertRead(userId, alertId);
      setAlerts(prev => prev.filter(a => a.id !== alertId));
      if (alerts.length <= 1) setAlertDismissed(true);
    } catch (err) {
      console.error('Failed to dismiss alert:', err);
    }
  };

  useEffect(() => {
    if (hasDevices === false) return;
    fetchSession();
    fetchEnv();
    fetchAlerts();
    // Poll every 1 second using /live endpoint (direct final_result query)
    const sessionInterval = setInterval(fetchSession, 1000);
    const envInterval = setInterval(fetchEnv, 1000);
    const alertInterval = setInterval(fetchAlerts, 5000);
    return () => { clearInterval(sessionInterval); clearInterval(envInterval); clearInterval(alertInterval); };
  }, [hasDevices, userId, selectedDeviceId, fetchSession]);

  const handleDeviceChange = (e) => {
    const deviceId = e.target.value;
    setSelectedDeviceId(deviceId);
    if (deviceId) {
      localStorage.setItem(STORAGE_KEY_SELECTED_DEVICE, deviceId);
    } else {
      localStorage.removeItem(STORAGE_KEY_SELECTED_DEVICE);
    }
    setSession(null);
  };

  const records = session?.records || [];
  const latestRecord = records.length > 0 ? records[records.length - 1] : null;
  const label = latestRecord?.label || session?.label || 'Khong co du lieu';
  const labelColor = labelColors[label] || '#6b7280';
  const hasData = !!latestRecord || records.length > 0;

  // Loading state while checking devices
  if (hasDevices === null) {
    return (
      <div className="p-4 lg:p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-center py-20">
          <div className="text-slate-500">Đang tải...</div>
        </div>
      </div>
    );
  }

  // User has no devices - show prompt
  if (!hasDevices) {
    return (
      <div className="p-4 lg:p-6 max-w-3xl mx-auto text-center py-20">
        <Cpu size={48} className="mx-auto text-slate-300 mb-4" />
        <h2 className="text-xl font-semibold text-slate-700 mb-2">
         Ban chua dang ky thiet bị
        </h2>
        <button
          onClick={() => navigate('/devices')}
          className="px-6 py-3 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg transition-colors"
        >
          Them thiet bi
        </button>
      </div>
    );
  }


  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Trang chu</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {lastUpdated
              ? `Cap nhat ${format(lastUpdated, 'HH:mm:ss')}`
              : loading ? 'Dang tai...' : 'Chua co du lieu'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Device selector */}
          {devices.length > 0 && (
            <div className="relative">
              <select
                value={selectedDeviceId}
                onChange={handleDeviceChange}
                className="appearance-none pl-3 pr-8 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-500 cursor-pointer min-w-[160px]"
              >
                <option value="">Tất cả thiết bị</option>
                {devices.map(d => (
                  <option key={d.id} value={d.id}>
                    {d.name || d.macAddress || d.id}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          )}
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
            Tai lai
          </button>
        </div>
      </div>

      {/* Health Status Banner */}
      <div
        className="rounded-xl p-4 flex items-center justify-between"
        style={{ backgroundColor: `${labelColor}15`, borderLeft: `4px solid ${labelColor}` }}
      >
        <div>
          <p className="text-sm text-slate-600">Tinh trang suc khoe</p>
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
              <p className="text-xs text-slate-500">Nhiet do</p>
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
            <p className="text-xs text-red-600 mt-1">Kiem tra lai BE</p>
          </div>
        </div>
      )}

      {/* Stress / Fever Alert Banner */}
      {alerts.length > 0 && alerts.slice(0, 1).map(alert => (
        <div
          key={alert.id}
          className="rounded-xl p-4 border-l-4 flex items-start justify-between gap-3"
          style={{
            backgroundColor: alert.label === 'Fever' ? '#fef2f2' : '#fffbeb',
            borderColor: alert.label === 'Fever' ? '#ef4444' : '#f59e0b',
          }}
        >
          <div className="flex items-start gap-3">
            <AlertTriangle
              size={20}
              className="flex-shrink-0 mt-0.5"
              style={{ color: alert.label === 'Fever' ? '#ef4444' : '#f59e0b' }}
            />
            <div>
              <p className="text-sm font-semibold" style={{ color: alert.label === 'Fever' ? '#dc2626' : '#d97706' }}>
                Cảnh báo {alert.label === 'Fever' ? 'Sốt' : 'Stress'}
              </p>
              <p className="text-sm text-slate-600 mt-0.5">{alert.message}</p>
              {alert.timestamp && (
                <p className="text-xs text-slate-400 mt-1">
                  {format(new Date(alert.timestamp), 'HH:mm:ss')}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => dismissAlert(alert.id)}
            className="flex-shrink-0 p-1 rounded hover:bg-black/5 transition-colors"
            title="Đóng"
          >
            <X size={16} className="text-slate-400 hover:text-slate-600" />
          </button>
        </div>
      ))}

      {/* No data placeholder */}
      {!hasData && !loading && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-12 text-center">
          <Activity size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-600 font-medium">Khong co du lieu</p>
          <p className="text-slate-400 text-sm mt-1">Khoi dong ESP32 de bat dau phien do moi.</p>
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
            <h3 className="font-semibold text-slate-700 mb-3 text-sm">Moi truong</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Thermometer size={13} className="text-orange-400" /> Nhiet do phong
                </span>
                <span className="font-medium text-slate-700">
                  {envData.extTempC != null ? `${envData.extTempC.toFixed(1)} °C` : '--'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Droplet size={13} className="text-blue-400" /> Do am
                </span>
                <span className="font-medium text-slate-700">
                  {envData.extHumidityPct != null ? `${envData.extHumidityPct.toFixed(1)} %` : '--'}
                </span>
              </div>
            </div>
          </div>

          {/* Session Info */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            <h3 className="font-semibold text-slate-700 mb-3 text-sm">Phien do</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Bat dau</span>
                <span className="font-medium text-slate-700">{format(new Date(session.startTime), 'HH:mm:ss')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Ket thuc</span>
                <span className="font-medium text-slate-700">{format(new Date(session.endTime), 'HH:mm:ss')}</span>
              </div>
            </div>
          </div>

          {/* Session Stats */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            <h3 className="font-semibold text-slate-700 mb-3 text-sm">Thong ke phien</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Diem du lieu</span>
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
            <h3 className="font-semibold text-slate-700 mb-3 text-sm">Gia tri moi nhat</h3>
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
