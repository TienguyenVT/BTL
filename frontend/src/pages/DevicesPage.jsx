import { useState, useEffect } from 'react';
import { Plus, Trash2, Cpu, X } from 'lucide-react';
import { getDevice, getDevices, addDevice, deleteDevice } from '../services/api';
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

  // #region debug hypothesis A: 405 on GET /devices/{id} vs DELETE /devices/{id} route conflict
  const handleViewDevice = async (device) => {
    setSelectedDevice(device);
    setDeviceLoading(true);
    fetch('http://127.0.0.1:7549/ingest/f96dcb14-73cd-4ded-90d6-a411ef5d7a1c',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'f6248e'},body:JSON.stringify({sessionId:'f6248e',location:'DevicesPage.jsx:handleViewDevice',message:'Hypothesis A: attempting GET /devices/{id}',data:{deviceId:device.id,url:`/devices/${device.id}`},timestamp:Date.now()})}).catch(()=>{});
    try {
      const res = await getDevice(userId, device.id);
      fetch('http://127.0.0.1:7549/ingest/f96dcb14-73cd-4ded-90d6-a411ef5d7a1c',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'f6248e'},body:JSON.stringify({sessionId:'f6248e',location:'DevicesPage.jsx:handleViewDevice',message:'Hypothesis A: GET succeeded',data:{status:res.status,data:res.data},timestamp:Date.now()})}).catch(()=>{});
      setSelectedDevice(res.data);
    } catch (err) {
      fetch('http://127.0.0.1:7549/ingest/f96dcb14-73cd-4ded-90d6-a411ef5d7a1c',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'f6248e'},body:JSON.stringify({sessionId:'f6248e',location:'DevicesPage.jsx:handleViewDevice',message:'Hypothesis A: GET failed',data:{status:err.response?.status,statusText:err.response?.statusText,url:err.config?.url,method:err.config?.method},timestamp:Date.now()})}).catch(()=>{});
      setSelectedDevice(null);
    }
    setDeviceLoading(false);
  };
  // #endregion

  return (
    <div className="p-4 lg:p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Devices</h1>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors"
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
                  <p className="font-semibold text-slate-800">{device.name || 'Unnamed Device'}</p>
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
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Device Name (optional)</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => { setShowForm(false); setError(''); }} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="flex-1 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors">
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

      {/* Device Detail Modal */}
      {selectedDevice && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">Device Details</h2>
              <button onClick={() => setSelectedDevice(null)} className="p-1.5 hover:bg-slate-100 rounded-lg">
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
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Name</p>
                  <p className="font-semibold text-slate-800">{selectedDevice.name || 'Unnamed Device'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">MAC Address</p>
                  <p className="font-mono text-sm text-slate-700 bg-slate-50 px-3 py-2 rounded-lg">{selectedDevice.macAddress}</p>
                </div>
                {selectedDevice.createdAt && (
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Registered</p>
                    <p className="text-slate-700">{format(new Date(selectedDevice.createdAt), 'dd MMM yyyy, HH:mm')}</p>
                  </div>
                )}
                {selectedDevice.message && (
                  <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded-lg px-4 py-3">
                    {selectedDevice.message}
                  </div>
                )}
                <div className="pt-3 flex justify-end">
                  <button onClick={() => setSelectedDevice(null)} className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors">
                    Close
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