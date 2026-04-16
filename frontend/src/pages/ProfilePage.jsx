import { useState, useEffect } from 'react';
import { User, Save, CheckCircle, Pencil, Trash2, X, AlertTriangle } from 'lucide-react';
import { getProfile, updateProfile, getMe, updateUser, deleteUser } from '../services/api';

const getBmiClass = (bmi) => {
  if (!bmi) return { label: '--', color: '#6b7280', pct: 0 };
  if (bmi < 18.5) return { label: 'Underweight', color: '#3b82f6', pct: 20 };
  if (bmi < 25) return { label: 'Normal', color: '#22c55e', pct: 45 };
  if (bmi < 30) return { label: 'Overweight', color: '#f59e0b', pct: 68 };
  return { label: 'Obese', color: '#ef4444', pct: 88 };
};

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ age: '', height: '', weight: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Account edit state
  const [account, setAccount] = useState(null);
  const [editAccountOpen, setEditAccountOpen] = useState(false);
  const [accountForm, setAccountForm] = useState({ name: '', password: '' });
  const [accountSaving, setAccountSaving] = useState(false);
  const [accountSaved, setAccountSaved] = useState(false);
  const [accountError, setAccountError] = useState('');

  // Delete account state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteForm, setDeleteForm] = useState({ password: '' });
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const userId = localStorage.getItem('backendUserId');

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [profileRes, accountRes] = await Promise.all([
          getProfile(userId),
          getMe(userId),
        ]);
        setProfile(profileRes.data);
        setForm({
          age: profileRes.data.age ?? '',
          height: profileRes.data.height ?? '',
          weight: profileRes.data.weight ?? '',
        });
        setAccount(accountRes.data);
        setAccountForm({
          name: accountRes.data.name ?? '',
          password: '',
        });
      } catch {}
      setLoading(false);
    };
    fetchAll();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    const payload = {};
    if (form.age !== '') payload.age = Number(form.age);
    if (form.height !== '') payload.height = Number(form.height);
    if (form.weight !== '') payload.weight = Number(form.weight);
    try {
      const res = await updateProfile(userId, payload);
      setProfile(res.data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
    setSaving(false);
  };

  const handleAccountSave = async () => {
    setAccountError('');
    if (!accountForm.password) {
      setAccountError('Vui long nhap mat khau hien tai de xac nhan');
      return;
    }
    setAccountSaving(true);
    try {
      const res = await updateUser(userId, {
        name: accountForm.name,
        password: accountForm.password,
      });
      setAccount(res.data);
      localStorage.setItem('backendUserName', res.data.name);
      setAccountSaved(true);
      setAccountForm({ ...accountForm, password: '' });
      setTimeout(() => {
        setAccountSaved(false);
        setEditAccountOpen(false);
      }, 1500);
    } catch (err) {
      setAccountError(err.response?.data?.message || 'Cap nhat that bai');
    }
    setAccountSaving(false);
  };

  const handleDeleteAccount = async () => {
    setDeleteError('');
    if (!deleteForm.password) {
      setDeleteError('Vui long nhap mat khau de xac nhan');
      return;
    }
    setDeleting(true);
    try {
      await deleteUser(userId, deleteForm.password);
      localStorage.removeItem('backendUserId');
      localStorage.removeItem('backendUserName');
      window.location.reload();
    } catch (err) {
      setDeleteError(err.response?.data?.message || 'Xoa tai khoan that bai');
    }
    setDeleting(false);
  };

  const bmi = profile?.bmi;
  const bmiInfo = getBmiClass(bmi);

  return (
    <div className="p-4 lg:p-6 max-w-2xl mx-auto">
      <h1 className="text-xl lg:text-2xl font-bold text-slate-800 mb-6">Profile</h1>

      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
      ) : (
        <div className="space-y-5">
          {/* User Info Card */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-teal-100 rounded-full flex items-center justify-center">
                <User size={26} className="text-teal-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-lg font-bold text-slate-800 truncate">{account?.name || 'User'}</p>
                <p className="text-slate-500 text-sm truncate">{account?.email || ''}</p>
                <p className="text-slate-400 text-xs">ID: {userId?.slice(0, 12)}...</p>
              </div>
              <button
                onClick={() => setEditAccountOpen(true)}
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-teal-600 transition-colors"
                title="Edit account"
              >
                <Pencil size={18} />
              </button>
            </div>
          </div>

          {/* BMI Card */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-semibold text-slate-700">BMI Index</h2>
              <span className="text-2xl font-bold" style={{ color: bmiInfo.color }}>
                {bmi ? bmi.toFixed(1) : '--'}
              </span>
            </div>
            <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden mb-2">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${bmiInfo.pct}%`, backgroundColor: bmiInfo.color }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              <span>Underweight</span>
              <span>Normal</span>
              <span>Overweight</span>
              <span>Obese</span>
            </div>
            <p className="text-sm mt-2 font-medium" style={{ color: bmiInfo.color }}>{bmiInfo.label}</p>
          </div>

          {/* Edit Health Form */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6">
            <h2 className="font-semibold text-slate-700 mb-4">Update Health Info</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Age (years)</label>
                <input
                  type="number"
                  min="1" max="120"
                  value={form.age}
                  onChange={(e) => setForm({ ...form, age: e.target.value })}
                  placeholder="e.g. 25"
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Height (cm)</label>
                <input
                  type="number"
                  min="50" max="250"
                  value={form.height}
                  onChange={(e) => setForm({ ...form, height: e.target.value })}
                  placeholder="e.g. 170"
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Weight (kg)</label>
                <input
                  type="number"
                  min="10" max="300"
                  value={form.weight}
                  onChange={(e) => setForm({ ...form, weight: e.target.value })}
                  placeholder="e.g. 65"
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="mt-4 flex items-center gap-2 px-5 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {saved ? <CheckCircle size={16} /> : <Save size={16} />}
              {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
            </button>
          </div>

          {/* Danger Zone */}
          <div className="bg-white rounded-xl border border-red-200 shadow-sm p-6">
            <h2 className="font-semibold text-red-600 mb-1">Danger Zone</h2>
            <p className="text-slate-500 text-sm mb-4">Once you delete your account, there is no going back.</p>
            <button
              onClick={() => setDeleteOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-red-50 hover:bg-red-100 border border-red-300 text-red-700 text-sm font-medium rounded-lg transition-colors"
            >
              <Trash2 size={16} />
              Delete Account
            </button>
          </div>
        </div>
      )}

      {/* Edit Account Modal */}
      {editAccountOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/50" onClick={() => setEditAccountOpen(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6 z-10">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-800">Edit Account</h3>
              <button onClick={() => setEditAccountOpen(false)} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600">
                <X size={18} />
              </button>
            </div>

            {accountError && (
              <div className="mb-3 flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-2.5 text-sm">
                <AlertTriangle size={15} className="flex-shrink-0" />
                {accountError}
              </div>
            )}
            {accountSaved && (
              <div className="mb-3 flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-2.5 text-sm">
                <CheckCircle size={15} className="flex-shrink-0" />
                Account updated successfully!
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Full Name</label>
                <input
                  type="text"
                  value={accountForm.name}
                  onChange={(e) => setAccountForm({ ...accountForm, name: e.target.value })}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Current Password <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  value={accountForm.password}
                  onChange={(e) => setAccountForm({ ...accountForm, password: e.target.value })}
                  placeholder="Enter current password to confirm"
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button
                onClick={() => setEditAccountOpen(false)}
                className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAccountSave}
                disabled={accountSaving}
                className="flex-1 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {accountSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Account Modal */}
      {deleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/50" onClick={() => setDeleteOpen(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6 z-10">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <Trash2 size={20} className="text-red-600" />
              </div>
              <h3 className="text-lg font-bold text-slate-800">Delete Account</h3>
            </div>

            <p className="text-slate-600 text-sm mb-4">
              This action is permanent and cannot be undone. All your data including health records,
              diary notes, and alerts will be permanently removed.
            </p>

            {deleteError && (
              <div className="mb-3 flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-2.5 text-sm">
                <AlertTriangle size={15} className="flex-shrink-0" />
                {deleteError}
              </div>
            )}

            <div className="mb-5">
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Enter your password to confirm
              </label>
              <input
                type="password"
                value={deleteForm.password}
                onChange={(e) => setDeleteForm({ password: e.target.value })}
                placeholder="Your password"
                className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setDeleteOpen(false)}
                className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleting}
                className="flex-1 py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {deleting ? 'Deleting...' : 'Yes, Delete My Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
