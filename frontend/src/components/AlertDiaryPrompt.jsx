import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, Thermometer, BookOpen, X, Send } from 'lucide-react';
import { getUnreadAlerts, markAlertRead, createDiaryNote } from '../services/api';
import { format } from 'date-fns';

const DISMISSED_KEY = 'alert_diary_dismissed';

function getDismissedIds() {
  try {
    return JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]');
  } catch {
    return [];
  }
}

function addDismissedId(id) {
  const ids = getDismissedIds();
  if (!ids.includes(id)) {
    ids.push(id);
    // Giữ tối đa 100 ID
    if (ids.length > 100) ids.shift();
    localStorage.setItem(DISMISSED_KEY, JSON.stringify(ids));
  }
}

export default function AlertDiaryPrompt() {
  const [alert, setAlert] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [activity, setActivity] = useState('');
  const [mood, setMood] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const userId = localStorage.getItem('backendUserId');

  const fetchUnread = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await getUnreadAlerts(userId);
      const alerts = res.data || [];
      const dismissed = getDismissedIds();
      // Tìm alert đầu tiên chưa bị dismiss
      const pending = alerts.find((a) => !dismissed.includes(a.id));
      if (pending && !alert) {
        setAlert(pending);
      }
    } catch {
      // silent fail
    }
  }, [userId, alert]);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, [fetchUnread]);

  const handleDismiss = async () => {
    if (alert) {
      addDismissedId(alert.id);
      try {
        await markAlertRead(userId, alert.id);
      } catch { }
    }
    setAlert(null);
    setShowForm(false);
    resetForm();
  };

  const handleOpenForm = () => {
    setShowForm(true);
  };

  const resetForm = () => {
    setActivity('');
    setMood('');
    setNote('');
  };

  const handleSubmit = async () => {
    if (!activity.trim()) return;
    setSaving(true);
    try {
      const title = alert.label === 'Stress'
        ? `Ghi chú Stress - ${format(new Date(alert.timestamp), 'HH:mm dd/MM')}`
        : `Ghi chú Fever - ${format(new Date(alert.timestamp), 'HH:mm dd/MM')}`;

      await createDiaryNote(userId, {
        title,
        content: note.trim() || `Hoat dong: ${activity}`,
        noteTimestamp: alert.timestamp,
        alertId: alert.id,
        activity: activity.trim(),
        mood: mood.trim() || null,
      });

      // Đánh dấu đã đọc
      addDismissedId(alert.id);
      try {
        await markAlertRead(userId, alert.id);
      } catch { }

      setAlert(null);
      setShowForm(false);
      resetForm();
    } catch (err) {
      console.error('Failed to create diary note:', err);
    }
    setSaving(false);
  };

  if (!alert) return null;

  const isStress = alert.label === 'Stress';
  const accentColor = isStress ? '#f59e0b' : '#ef4444';
  const bgColor = isStress ? '#fffbeb' : '#fef2f2';
  const Icon = isStress ? AlertTriangle : Thermometer;
  const timeStr = alert.timestamp
    ? format(new Date(alert.timestamp), 'HH:mm')
    : '--:--';

  const moodOptions = ['Binh thuong', 'Lo lang', 'Kho chiu', 'Me moi', 'Khong khoe'];

  return (
    <div className="fixed bottom-4 right-4 z-[9999] max-w-sm w-full animate-in slide-in-from-bottom-4" style={{ animation: 'slideUp 0.4s ease-out' }}>
      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div
        className="rounded-2xl shadow-2xl border overflow-hidden"
        style={{ borderColor: `${accentColor}40`, backgroundColor: '#fff' }}
      >
        {/* Header */}
        <div className="px-4 py-3 flex items-start gap-3" style={{ backgroundColor: bgColor }}>
          <div
            className="p-2 rounded-lg flex-shrink-0 mt-0.5"
            style={{ backgroundColor: `${accentColor}20` }}
          >
            <Icon size={18} style={{ color: accentColor }} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-800">
              {isStress ? 'Phat hien Stress' : 'Phat hien Sot'}
            </p>
            <p className="text-xs text-slate-600 mt-0.5">
              Chi so {isStress ? 'cang thang' : 'nhiet do'} tang vut luc{' '}
              <strong>{timeStr}</strong>.
            </p>
            {/* Health snapshot */}
            {(alert.bpm || alert.bodyTemp || alert.gsrAdc) && (
              <div className="flex gap-3 mt-2 text-xs">
                {alert.bpm != null && (
                  <span className="text-red-500 font-medium">BPM: {Math.round(alert.bpm)}</span>
                )}
                {alert.bodyTemp != null && (
                  <span className="text-orange-500 font-medium">Temp: {alert.bodyTemp.toFixed(1)}°C</span>
                )}
                {alert.gsrAdc != null && (
                  <span className="text-emerald-600 font-medium">GSR: {Math.round(alert.gsrAdc)}</span>
                )}
              </div>
            )}
          </div>
          <button
            onClick={handleDismiss}
            className="p-1 hover:bg-white/60 rounded-lg transition-colors flex-shrink-0"
          >
            <X size={16} className="text-slate-400" />
          </button>
        </div>

        {/* Body */}
        {!showForm ? (
          <div className="px-4 py-3 flex gap-2">
            <button
              onClick={handleOpenForm}
              className="flex-1 py-2 px-3 text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition-colors"
              style={{ backgroundColor: accentColor, color: '#fff' }}
            >
              <BookOpen size={14} />
              Ghi chu ngay
            </button>
            <button
              onClick={handleDismiss}
              className="py-2 px-4 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Bo qua
            </button>
          </div>
        ) : (
          <div className="px-4 py-3 space-y-3">
            {/* Activity */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                 Ban dang lam gi ? <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={activity}
                onChange={(e) => setActivity(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400"
                autoFocus
              />
            </div>

            {/* Mood chips */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Tam trang</label>
              <div className="flex flex-wrap gap-1.5">
                {moodOptions.map((m) => (
                  <button
                    key={m}
                    onClick={() => setMood(mood === m ? '' : m)}
                    className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${mood === m
                      ? 'border-amber-400 bg-amber-50 text-amber-700 font-medium'
                      : 'border-slate-200 text-slate-500 hover:border-slate-300'
                      }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {/* Note */}
            {/* <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Ghi chu them</label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Mo ta..."
                rows={2}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
              />
            </div> */}

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={handleSubmit}
                disabled={saving || !activity.trim()}
                className="flex-1 py-2 px-3 text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                style={{ backgroundColor: accentColor, color: '#fff' }}
              >
                <Send size={13} />
                {saving ? 'Dang luu...' : 'Luu ghi chu'}
              </button>
              <button
                onClick={handleDismiss}
                className="py-2 px-3 text-sm text-slate-500 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Huy
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
