import { useState, useEffect } from 'react';
import { Plus, Trash2, Cpu, X } from 'lucide-react';
import { getDevices, addDevice, deleteDevice } from '../services/api';
import { format } from 'date-fns';

export default function DevicesPage() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ macAddress: '', name: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
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
      setError(err.response?.data?.message || 'Failed to add device');
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

  return (
    <div className="p-4 lg:p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Devices</h1>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus size={16} />
          Add Device
        </button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
      ) : devices.length === 0 ? (
        <div className="text-center py-16">
          <Cpu size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-500 font-medium">No devices registered</p>
          <p className="text-slate-400 text-sm mt-1">Add an ESP32 device to start monitoring.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {devices.map((device) => (
            <div key={device.id} className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Cpu size={20} className="text-indigo-600" />
                </div>
                <div>
                  <p className="font-semibold text-slate-800">{device.name || 'Unnamed Device'}</p>
                  <p className="text-sm text-slate-500 font-mono">{device.macAddress}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Registered {device.createdAt ? format(new Date(device.createdAt), 'dd MMM yyyy') : '--'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDeleteConfirm(device.id)}
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
              <h2 className="font-semibold text-slate-800">Register New Device</h2>
              <button onClick={() => { setShowForm(false); setError(''); }} className="p-1.5 hover:bg-slate-100 rounded-lg">
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleAdd} className="p-6 space-y-4">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>
              )}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">MAC Address *</label>
                <input
                  type="text"
                  required
                  value={form.macAddress}
                  onChange={(e) => setForm({ ...form, macAddress: e.target.value })}
                  placeholder="AA:BB:CC:DD:EE:FF"
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Device Name (optional)</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. ESP32-Bedroom"
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => { setShowForm(false); setError(''); }} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors">
                  {saving ? 'Adding...' : 'Add Device'}
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
            <h3 className="font-semibold text-slate-800 mb-2">Remove Device?</h3>
            <p className="text-slate-500 text-sm mb-5">This will unregister the device from your account.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 text-white text-sm font-medium rounded-lg transition-colors">Remove</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}