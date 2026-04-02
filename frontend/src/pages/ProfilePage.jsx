import { useState, useEffect } from 'react';
import { User, Save, CheckCircle } from 'lucide-react';
import { getProfile, updateProfile } from '../services/api';

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
  const userId = localStorage.getItem('backendUserId');
  const userName = localStorage.getItem('backendUserName') || 'User';

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await getProfile(userId);
        setProfile(res.data);
        setForm({
          age: res.data.age ?? '',
          height: res.data.height ?? '',
          weight: res.data.weight ?? '',
        });
      } catch {}
      setLoading(false);
    };
    fetch();
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
              <div className="w-14 h-14 bg-indigo-100 rounded-full flex items-center justify-center">
                <User size={26} className="text-indigo-600" />
              </div>
              <div>
                <p className="text-lg font-bold text-slate-800">{userName}</p>
                <p className="text-slate-500 text-sm">User ID: {userId?.slice(0, 12)}...</p>
              </div>
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

          {/* Edit Form */}
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
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="mt-4 flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {saved ? <CheckCircle size={16} /> : <Save size={16} />}
              {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}