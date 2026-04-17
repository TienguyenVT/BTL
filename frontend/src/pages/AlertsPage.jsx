import { useState, useEffect, useCallback } from 'react';
import { Bell, Thermometer, RefreshCw, Activity, Zap, BookOpen, Cpu, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { getFeverStressRecords, getDevices, createDiaryNote } from '../services/api';
import { format } from 'date-fns';

const labelConfig = {
  Stress: { color: '#f59e0b', bg: '#fef3c7', icon: Zap },
  Fever: { color: '#ef4444', bg: '#fee2e2', icon: Thermometer },
};

const PAGE_SIZE = 20;

export default function AlertsPage() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [devices, setDevices] = useState([]);
  const [macToName, setMacToName] = useState({});
  const [selectedDeviceId, setSelectedDeviceId] = useState(
    () => localStorage.getItem('alerts_selected_device_id') || ''
  );
  const [diaryModal, setDiaryModal] = useState(null);
  const [diaryForm, setDiaryForm] = useState({ activity: '', mood: '', note: '' });
  const [savingDiary, setSavingDiary] = useState(false);
  const userId = localStorage.getItem('backendUserId');

  // Load devices once
  useEffect(() => {
    if (!userId) return;
    getDevices(userId).then(res => {
      const list = res.data || [];
      setDevices(list);
      const map = {};
      list.forEach(d => {
        if (d.macAddress) map[d.macAddress.toLowerCase()] = d.name || d.macAddress;
      });
      setMacToName(map);
    }).catch(() => {});
  }, [userId]);

  const fetchRecords = useCallback(async (pageNum) => {
    setLoading(true);
    try {
      const res = await getFeverStressRecords(userId, pageNum, PAGE_SIZE, selectedDeviceId || null);
      const data = res.data;
      setRecords(data.records || []);
      setTotalCount(data.totalCount || 0);
      setTotalPages(data.totalPages || 0);
      setPage(pageNum);
    } catch {}
    setLoading(false);
  }, [userId, selectedDeviceId]);

  useEffect(() => {
    fetchRecords(0);
  }, [fetchRecords]);

  const handleDeviceChange = (deviceId) => {
    setSelectedDeviceId(deviceId);
    if (deviceId) {
      localStorage.setItem('alerts_selected_device_id', deviceId);
    } else {
      localStorage.removeItem('alerts_selected_device_id');
    }
  };

  const openDiaryModal = (record) => {
    setDiaryForm({ activity: '', mood: '', note: '' });
    setDiaryModal(record);
  };

  const handleSaveDiary = async () => {
    if (!diaryForm.activity.trim()) return;
    setSavingDiary(true);
    try {
      const title = diaryModal.label === 'Stress'
        ? `Ghi chú Stress - ${format(new Date(diaryModal.timestamp), 'HH:mm dd/MM')}`
        : `Ghi chú Fever - ${format(new Date(diaryModal.timestamp), 'HH:mm dd/MM')}`;

      await createDiaryNote(userId, {
        title,
        content: diaryForm.note.trim() || `Hoạt động: ${diaryForm.activity}`,
        noteTimestamp: diaryModal.timestamp,
        activity: diaryForm.activity.trim(),
        mood: diaryForm.mood.trim() || null,
      });

      setDiaryModal(null);
    } catch (err) {
      console.error('Failed to save diary:', err);
    }
    setSavingDiary(false);
  };

  const moodOptions = ['Binh thuong', 'Lo lang', 'Kho chiu', 'Me moi', 'Khong khoe'];

  return (
    <div className="p-4 lg:p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Canh bao suc khoe</h1>
          {totalCount > 0 && (
            <span className="bg-red-50 text-red-600 text-xs font-medium px-2.5 py-1 rounded-full border border-red-100">
              {totalCount} bản ghi
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {devices.length > 0 && (
            <div className="relative">
              <select
                value={selectedDeviceId}
                onChange={(e) => handleDeviceChange(e.target.value)}
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
          <button
            onClick={() => fetchRecords(page)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
          >
            <RefreshCw size={14} />
            Tai lai
          </button>
        </div>
      </div>  

      {/* Loading skeleton */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
      ) : records.length === 0 ? (
        <div className="text-center py-20">
          <Bell size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-500 font-medium">Không có bản ghi Stress/Fever</p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {records.map((record) => {
              const config = labelConfig[record.label] || { color: '#6b7280', bg: '#f3f4f6', icon: Bell };
              const Icon = config.icon;
              const deviceLabel = record.macAddress ? (macToName[record.macAddress.toLowerCase()] || record.macAddress) : null;

              return (
                <div
                  key={record.id ?? `${record.timestamp}-${record.macAddress}-${record.label}`}
                  className="bg-white rounded-xl border shadow-sm overflow-hidden"
                  style={{ borderLeft: `4px solid ${config.color}` }}
                >
                  <div className="flex items-start gap-4 p-5">
                    {/* Icon */}
                    <div className="p-2.5 rounded-lg flex-shrink-0" style={{ backgroundColor: config.bg }}>
                      <Icon size={20} style={{ color: config.color }} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-semibold text-sm" style={{ color: config.color }}>
                          {record.label === 'Fever' ? 'Sốt' : 'Stress'}
                        </span>
                        {record.confidence != null && (
                          <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">
                            {(record.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                        {deviceLabel && (
                          <span className="flex items-center gap-1 text-xs text-slate-400">
                            <Cpu size={11} />{deviceLabel}
                          </span>
                        )}
                      </div>

                      <p className="text-slate-700 text-sm mb-1">
                        {record.label === 'Fever'
                          ? `Nhiệt độ cơ thể: ${record.bodyTemp?.toFixed(1)}°C`
                          : `GSR: ${record.gsrAdc != null ? Math.round(record.gsrAdc) : '--'} | BPM: ${record.bpm != null ? Math.round(record.bpm) : '--'}`
                        }
                      </p>

                      <div className="flex items-center gap-4 text-xs text-slate-400">
                        {record.timestamp && (
                          <span>{format(new Date(record.timestamp), 'dd MMM yyyy, HH:mm:ss')}</span>
                        )}
                        {record.bpm != null && (
                          <span className="text-red-400 font-medium">BPM: {Math.round(record.bpm)}</span>
                        )}
                        {record.spo2 != null && (
                          <span className="text-blue-400 font-medium">SpO2: {record.spo2.toFixed(1)}%</span>
                        )}
                        {record.bodyTemp != null && (
                          <span className="text-orange-400 font-medium">Nhiet do: {record.bodyTemp.toFixed(1)}°C</span>
                        )}
                        {record.gsrAdc != null && (
                          <span className="text-emerald-400 font-medium">GSR: {Math.round(record.gsrAdc)}</span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex-shrink-0">
                      <button
                        onClick={() => openDiaryModal(record)}
                        className="p-2 rounded-lg hover:bg-teal-50 text-slate-400 hover:text-teal-600 transition-colors flex items-center gap-1.5 text-sm"
                        title="Ghi chu vao Diary"
                      >
                        <BookOpen size={15} />
                        <span className="hidden sm:inline">Ghi chú</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => fetchRecords(page - 1)}
                disabled={page === 0}
                className="flex items-center gap-1 px-3 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={15} />
                Truoc
              </button>

              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                  let pageNum = i;
                  if (totalPages > 7) {
                    if (page < 4) pageNum = i;
                    else if (page > totalPages - 4) pageNum = totalPages - 7 + i;
                    else pageNum = page - 3 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => fetchRecords(pageNum)}
                      className={`w-9 h-9 text-sm rounded-lg transition-colors ${
                        pageNum === page
                          ? 'bg-teal-600 text-white font-medium'
                          : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {pageNum + 1}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => fetchRecords(page + 1)}
                disabled={page >= totalPages - 1}
                className="flex items-center gap-1 px-3 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Sau
                <ChevronRight size={15} />
              </button>

              <span className="text-xs text-slate-400 ml-2">
                Trang {page + 1} / {totalPages}
              </span>
            </div>
          )}
        </>
      )}

      {/* Diary from Record Modal */}
      {diaryModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">
                Ghi chu cho ban ghi {diaryModal.label}
              </h2>
              <button onClick={() => setDiaryModal(null)} className="p-1.5 hover:bg-slate-100 rounded-lg">
                ✕
              </button>
            </div>
            <div className="px-6 py-4">
              {/* Record info */}
              <div
                className="p-3 rounded-lg mb-4 text-sm"
                style={{
                  backgroundColor: (labelConfig[diaryModal.label]?.bg || '#f3f4f6'),
                  color: (labelConfig[diaryModal.label]?.color || '#6b7280'),
                }}
              >
                <p className="font-medium">
                  {diaryModal.label === 'Fever'
                    ? `Nhiệt độ: ${diaryModal.bodyTemp?.toFixed(1)}°C`
                    : `BPM: ${diaryModal.bpm != null ? Math.round(diaryModal.bpm) : '--'}, GSR: ${diaryModal.gsrAdc != null ? Math.round(diaryModal.gsrAdc) : '--'}`
                  }
                </p>
                <p className="text-xs mt-1 opacity-75">
                  {diaryModal.timestamp ? format(new Date(diaryModal.timestamp), 'dd MMM yyyy, HH:mm:ss') : '--'}
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Ban dang lam gi luc do? <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={diaryForm.activity}
                    onChange={(e) => setDiaryForm({ ...diaryForm, activity: e.target.value })}
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    autoFocus
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Tam trang</label>
                  <div className="flex flex-wrap gap-2">
                    {moodOptions.map((m) => (
                      <button
                        key={m}
                        onClick={() => setDiaryForm({ ...diaryForm, mood: diaryForm.mood === m ? '' : m })}
                        className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
                          diaryForm.mood === m
                            ? 'border-teal-400 bg-teal-50 text-teal-700 font-medium'
                            : 'border-slate-200 text-slate-500 hover:border-slate-300'
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Ghi chu them</label>
                  <textarea
                    value={diaryForm.note}
                    onChange={(e) => setDiaryForm({ ...diaryForm, note: e.target.value })}
                    placeholder=" tiet hon ve tinh huong..."
                    rows={3}
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none"
                  />
                </div>
              </div>
            </div>
            <div className="flex gap-3 px-6 pb-6">
              <button onClick={() => setDiaryModal(null)} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                Huy
              </button>
              <button
                onClick={handleSaveDiary}
                disabled={savingDiary || !diaryForm.activity.trim()}
                className="flex-1 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <BookOpen size={15} />
                {savingDiary ? 'Dang luu...' : 'Luu vao Nhat ky'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
