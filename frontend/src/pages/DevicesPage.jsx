import { useState, useEffect } from 'react';
import { Plus, Trash2, Cpu, X, Pencil, Check } from 'lucide-react';
import { getDevice, getDevices, addDevice, deleteDevice, renameDevice } from '../services/api';
import { format } from 'date-fns';

export default function DevicesPage() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ macAddress: '', name: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceLoading, setDeviceLoading] = useState(false);

  // Rename state
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [renameError, setRenameError] = useState('');

  const userId = localStorage.getItem('backendUserId');

  const fetchDevices = async () => {
    try {
      const res = await getDevices(userId);
      setDevices(res.data || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchDevices(); }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await addDevice(userId, { macAddress: form.macAddress, name: form.name || undefined });
      await fetchDevices();
      setShowForm(false);
      setForm({ macAddress: '', name: '' });
    } catch (err) {
      setError(err.response?.data?.message || 'Them thiet bi that bai');
    }
    setSaving(false);
  };

  const handleDelete = async (id) => {
    try {
      await deleteDevice(userId, id);
      setDevices(devices.filter((d) => d.id !== id));
    } catch {}
    setDeleteConfirm(null);
  };

  const handleViewDevice = async (device) => {
    setSelectedDevice(device);
    setDeviceLoading(true);
    setIsEditing(false);
    setRenameError('');
    try {
      const res = await getDevice(userId, device.id);
      setSelectedDevice(res.data);
    } catch {
      setSelectedDevice(null);
    }
    setDeviceLoading(false);
  };

  const handleStartEdit = () => {
    setEditName(selectedDevice?.name || '');
    setIsEditing(true);
    setRenameError('');
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setRenameError('');
  };

  const handleSaveRename = async () => {
    if (!editName.trim()) {
      setRenameError('Ten thiet bi khong duoc de trong');
      return;
    }
    setRenaming(true);
    setRenameError('');
    try {
      const res = await renameDevice(userId, selectedDevice.id, editName.trim());
      // Update selectedDevice
      setSelectedDevice({ ...selectedDevice, name: editName.trim() });
      // Update the devices list
      setDevices(devices.map(d => d.id === selectedDevice.id ? { ...d, name: editName.trim() } : d));
      setIsEditing(false);
    } catch (err) {
      setRenameError(err.response?.data?.message || 'Doi ten that bai');
    }
    setRenaming(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveRename();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  return (
    <div className="p-4 lg:p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Thiet bi</h1>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus size={16} />
          Them thiet bi
        </button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
      ) : devices.length === 0 ? (
        <div className="text-center py-16">
          <Cpu size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-500 font-medium">Chua co thiet bi nao duoc dang ky</p>
          </div>
      ) : (
        <div className="space-y-3">
          {devices.map((device) => (
            <div
              key={device.id}
              onClick={() => handleViewDevice(device)}
              className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 flex items-center justify-between cursor-pointer hover:border-teal-300 hover:shadow-md transition-all"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-teal-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Cpu size={20} className="text-teal-600" />
                </div>
                <div>
                  <p className="font-semibold text-slate-800">{device.name || 'Thiet bi chua co ten'}</p>
                  <p className="text-sm text-slate-500 font-mono">{device.macAddress}</p>
                </div>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); setDeleteConfirm(device.id); }}
                className="p-2 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add Device Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">Dang ky thiet bi moi</h2>
              <button onClick={() => { setShowForm(false); setError(''); }} className="p-1.5 hover:bg-slate-100 rounded-lg">
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleAdd} className="p-6 space-y-4">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>
              )}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Dia chi MAC *</label>
                <input
                  type="text"
                  required
                  value={form.macAddress}
                  onChange={(e) => setForm({ ...form, macAddress: e.target.value })}
                  placeholder="AA:BB:CC:DD:EE:FF"
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Ten thiet bi (tuy chon)</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => { setShowForm(false); setError(''); }} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                  Huy
                </button>
                <button type="submit" disabled={saving} className="flex-1 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors">
                  {saving ? 'Dang them...' : 'Them thiet bi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="font-semibold text-slate-800 mb-2">Xoa thiet bi?</h3>
            <p className="text-slate-500 text-sm mb-5">Thiet bi se bi huy dang ky khoi tai khoan cua ban.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">Huy</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 text-white text-sm font-medium rounded-lg transition-colors">Xoa</button>
            </div>
          </div>
        </div>
      )}

      {/* Device Detail Modal */}
      {selectedDevice && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">Chi tiet thiet bi</h2>
              <button onClick={() => { setSelectedDevice(null); setIsEditing(false); }} className="p-1.5 hover:bg-slate-100 rounded-lg">
                <X size={18} />
              </button>
            </div>
            {deviceLoading ? (
              <div className="flex justify-center py-10">
                <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-center mb-4">
                  <div className="w-16 h-16 bg-teal-50 rounded-2xl flex items-center justify-center">
                    <Cpu size={32} className="text-teal-600" />
                  </div>
                </div>

                {/* Name field — editable */}
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Name</p>
                  {isEditing ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          onKeyDown={handleKeyDown}
                          autoFocus
                          className="flex-1 px-3 py-2 border border-teal-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-teal-50/30"
                          placeholder="Nhap ten thiet bi"
                        />
                        <button
                          onClick={handleSaveRename}
                          disabled={renaming}
                          className="p-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white disabled:opacity-50 transition-colors"
                          title="Luu"
                        >
                          <Check size={16} />
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-500 transition-colors"
                          title="Huy"
                        >
                          <X size={16} />
                        </button>
                      </div>
                      {renameError && (
                        <p className="text-xs text-red-500">{renameError}</p>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center justify-between group">
                      <p className="font-semibold text-slate-800">{selectedDevice.name || 'Thiet bi chua co ten'}</p>
                      <button
                        onClick={handleStartEdit}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-teal-50 opacity-0 group-hover:opacity-100 transition-all"
                        title="Doi ten"
                      >
                        <Pencil size={14} />
                      </button>
                    </div>
                  )}
                </div>

                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Dia chi MAC</p>
                  <p className="font-mono text-sm text-slate-700 bg-slate-50 px-3 py-2 rounded-lg">{selectedDevice.macAddress}</p>
                </div>
                {selectedDevice.createdAt && (
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Da dang ky</p>
                    <p className="text-slate-700">{format(new Date(selectedDevice.createdAt), 'dd MMM yyyy, HH:mm')}</p>
                  </div>
                )}
                {selectedDevice.message && (
                  <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded-lg px-4 py-3">
                    {selectedDevice.message}
                  </div>
                )}
                <div className="pt-3 flex justify-end">
                  <button onClick={() => { setSelectedDevice(null); setIsEditing(false); }} className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors">
                    Dong
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}