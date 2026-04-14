import { useState, useEffect } from 'react';
import { Bell, Thermometer, Trash2, RefreshCw } from 'lucide-react';
import { getAlerts, deleteAlert } from '../services/api';
import { format } from 'date-fns';

const labelConfig = {
  Stress: { color: '#f59e0b', bg: '#fef3c7', icon: Bell },
  Fever: { color: '#ef4444', bg: '#fee2e2', icon: Thermometer },
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const userId = localStorage.getItem('backendUserId');

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const res = await getAlerts(userId);
      setAlerts(res.data || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id) => {
    try {
      await deleteAlert(userId, id);
      setAlerts(alerts.filter((a) => a.id !== id));
    } catch {}
    setDeleteConfirm(null);
  };

  const unreadCount = alerts.filter((a) => !a.isRead).length;

  return (
    <div className="p-4 lg:p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Alerts</h1>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-xs font-bold px-2.5 py-1 rounded-full">
              {unreadCount} new
            </span>
          )}
        </div>
        <button onClick={fetchAlerts} className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16">
          <Bell size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-500 font-medium">No alerts</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const config = labelConfig[alert.label] || { color: '#6b7280', bg: '#f3f4f6', icon: Bell };
            const Icon = config.icon;
            return (
              <div
                key={alert.id}
                className={`bg-white rounded-xl border shadow-sm p-5 flex items-start gap-4 ${
                  !alert.isRead ? 'border-l-4' : 'border-slate-100'
                }`}
                style={!alert.isRead ? { borderLeftColor: config.color } : {}}
              >
                <div className="p-2.5 rounded-lg flex-shrink-0" style={{ backgroundColor: config.bg }}>
                  <Icon size={20} style={{ color: config.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-sm" style={{ color: config.color }}>{alert.label}</span>
                    {!alert.isRead && (
                      <span className="text-xs bg-red-100 text-red-600 font-medium px-2 py-0.5 rounded-full">New</span>
                    )}
                  </div>
                  <p className="text-slate-700 text-sm">{alert.message}</p>
                  <p className="text-slate-400 text-xs mt-1.5">
                    {alert.timestamp ? format(new Date(alert.timestamp), 'dd MMM yyyy, HH:mm') : '--'}
                  </p>
                </div>
                <button
                  onClick={() => setDeleteConfirm(alert.id)}
                  className="p-2 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors flex-shrink-0"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Delete Confirm */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="font-semibold text-slate-800 mb-2">Delete Alert?</h3>
            <p className="text-slate-500 text-sm mb-5">This alert will be permanently removed.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 text-white text-sm font-medium rounded-lg transition-colors">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}