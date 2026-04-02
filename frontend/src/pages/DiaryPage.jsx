
import { useState, useEffect } from 'react';
import { Plus, Search, Edit2, Trash2, X, BookOpen, Save } from 'lucide-react';
import { getDiaryNotes, createDiaryNote, updateDiaryNote, deleteDiaryNote } from '../services/api';
import { format } from 'date-fns';

export default function DiaryPage() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null); // null | { mode: 'create'|'edit', note?: DiaryNote }
  const [form, setForm] = useState({ title: '', content: '' });
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const userId = localStorage.getItem('backendUserId');

  const fetchNotes = async () => {
    try {
      const res = await getDiaryNotes(userId);
      setNotes(res.data || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchNotes(); }, []);

  const openCreate = () => { setForm({ title: '', content: '' }); setModal({ mode: 'create' }); };
  const openEdit = (note) => { setForm({ title: note.title, content: note.content }); setModal({ mode: 'edit', note }); };

  const handleSave = async () => {
    if (!form.title.trim() || !form.content.trim()) return;
    setSaving(true);
    try {
      if (modal.mode === 'create') {
        await createDiaryNote(userId, form);
      } else {
        await updateDiaryNote(userId, modal.note.id, form);
      }
      await fetchNotes();
      setModal(null);
    } catch {}
    setSaving(false);
  };

  const handleDelete = async (id) => {
    try {
      await deleteDiaryNote(userId, id);
      setNotes(notes.filter((n) => n.id !== id));
    } catch {}
    setDeleteConfirm(null);
  };

  const filtered = notes.filter(
    (n) =>
      n.title?.toLowerCase().includes(search.toLowerCase()) ||
      n.content?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-4 lg:p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl lg:text-2xl font-bold text-slate-800">Health Diary</h1>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus size={16} />
          New Entry
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-5">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search diary entries..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
        />
      </div>

      {/* Notes List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-28 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-500 font-medium">No diary entries yet</p>
          <p className="text-slate-400 text-sm mt-1">Click "New Entry" to start journaling your health.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((note) => (
            <div key={note.id} className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-slate-800 truncate">{note.title}</h3>
                  <p className="text-slate-500 text-sm mt-1 line-clamp-2">{note.content}</p>
                  {note.createdAt && (
                    <p className="text-xs text-slate-400 mt-2">
                      {format(new Date(note.createdAt), 'dd MMM yyyy, HH:mm')}
                    </p>
                  )}
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  <button onClick={() => openEdit(note)} className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-indigo-600 transition-colors">
                    <Edit2 size={15} />
                  </button>
                  <button onClick={() => setDeleteConfirm(note.id)} className="p-2 rounded-lg hover:bg-red-50 text-slate-500 hover:text-red-500 transition-colors">
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {modal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">{modal.mode === 'create' ? 'New Diary Entry' : 'Edit Entry'}</h2>
              <button onClick={() => setModal(null)} className="p-1.5 hover:bg-slate-100 rounded-lg">
                <X size={18} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Title</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="Entry title..."
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Content</label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm({ ...form, content: e.target.value })}
                  placeholder="Write your health notes here..."
                  rows={5}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>
            </div>
            <div className="flex gap-3 px-6 pb-6">
              <button onClick={() => setModal(null)} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.title.trim() || !form.content.trim()}
                className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <Save size={15} />
                {saving ? 'Saving...' : 'Save Entry'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="font-semibold text-slate-800 mb-2">Delete Entry?</h3>
            <p className="text-slate-500 text-sm mb-5">This action cannot be undone.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                Cancel
              </button>
              <button onClick={() => handleDelete(deleteConfirm)} className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 text-white text-sm font-medium rounded-lg transition-colors">
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}