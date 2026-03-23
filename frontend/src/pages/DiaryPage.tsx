import React, { useState, useEffect, useCallback } from 'react';
import { DiaryNote } from '../types';
import { getDiaryNotes, createDiaryNote, updateDiaryNote, deleteDiaryNote } from '../services/api';

/**
 * ============================================================
 * DiaryPage — Trang Sổ tay sức khỏe cá nhân
 * ============================================================
 *
 * LAYOUT:
 *   - Header: Tiêu đề + nút "Thêm ghi chú"
 *   - Empty State: Hiển thị khi chưa có ghi chú nào
 *   - Notes List: Danh sách các ghi chú
 *   - Modal: Form tạo / sửa ghi chú
 *
 * CAC CHUC NANG:
 *   - Xem danh sach ghi chú (mới nhất trước)
 *   - Thêm ghi chú mới
 *   - Sửa ghi chú
 *   - Xóa ghi chú (xác nhận trước khi xóa)
 *
 * API ENDPOINTS:
 *   - GET    /api/diary-notes           → Danh sách
 *   - POST   /api/diary-notes           → Tạo mới
 *   - PUT    /api/diary-notes/{id}      → Sửa
 *   - DELETE /api/diary-notes/{id}      → Xóa
 */

// ── Types ────────────────────────────────────────────────────────────────

type ModalMode = 'create' | 'edit' | null;

interface ModalState {
  mode: ModalMode;
  note: DiaryNote | null;
}

// ── Modal Component ─────────────────────────────────────────────────────

const DiaryModal: React.FC<{
  mode: ModalMode;
  note: DiaryNote | null;
  onClose: () => void;
  onSaved: () => void;
}> = ({ mode, note, onClose, onSaved }) => {
  const [title, setTitle] = useState(note?.title ?? '');
  const [content, setContent] = useState(note?.content ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form khi modal mở
  useEffect(() => {
    setTitle(note?.title ?? '');
    setContent(note?.content ?? '');
    setError(null);
  }, [note, mode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Vui lòng nhập tiêu đề');
      return;
    }
    if (!content.trim()) {
      setError('Vui lòng nhập nội dung');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      if (mode === 'create') {
        await createDiaryNote({ title: title.trim(), content: content.trim() });
      } else if (mode === 'edit' && note?.id) {
        await updateDiaryNote(note.id, { title: title.trim(), content: content.trim() });
      }
      onSaved();
    } catch (err: any) {
      setError(err.response?.data?.message ?? 'Đã xảy ra lỗi. Vui lòng thử lại.');
    } finally {
      setSaving(false);
    }
  };

  if (!mode) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg animate-modal-in">

        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
            {mode === 'create' ? 'Thêm ghi chú mới' : 'Sửa ghi chú'}
          </h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
          >
            ✕
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Tiêu đề */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Tiêu đề <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="VD: Hôm nay thi cuối kỳ"
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
              autoFocus
            />
          </div>

          {/* Nội dung */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Nội dung <span className="text-red-500">*</span>
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Mô tả chi tiết hoạt động hoặc cảm xúc của bạn hôm nay..."
              rows={5}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition resize-none"
            />
          </div>

          {/* Lỗi */}
          {error && (
            <div className="px-4 py-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition font-medium"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {saving ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Đang lưu...
                </>
              ) : (
                mode === 'create' ? 'Thêm ghi chú' : 'Lưu thay đổi'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ── Confirm Delete Modal ───────────────────────────────────────────────

const ConfirmDeleteModal: React.FC<{
  note: DiaryNote;
  onClose: () => void;
  onConfirmed: () => void;
}> = ({ note, onClose, onConfirmed }) => {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!note.id) return;
    setDeleting(true);
    try {
      await onConfirmed();
      onClose();
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-sm">
        <div className="p-6 text-center">
          <div className="w-14 h-14 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">🗑️</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-2">
            Xóa ghi chú?
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            Bạn có chắc muốn xóa ghi chú <strong>"{note.title}"</strong>? Hành động này không thể hoàn tác.
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={onClose}
              className="px-5 py-2.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition font-medium"
            >
              Hủy
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="px-5 py-2.5 rounded-lg bg-red-500 hover:bg-red-600 text-white font-medium transition disabled:opacity-60"
            >
              {deleting ? 'Đang xóa...' : 'Xóa'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── DiaryPage Component ─────────────────────────────────────────────────

const DiaryPage: React.FC = () => {
  const [notes, setNotes] = useState<DiaryNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState>({ mode: null, note: null });
  const [deleteTarget, setDeleteTarget] = useState<DiaryNote | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // userId giả lập (thay bằng userId từ auth/JWT thực tế)
  const userId = 'Nguyen_Van';

  // Fetch danh sách ghi chú
  const fetchNotes = useCallback(async () => {
    try {
      setError(null);
      const data = await getDiaryNotes();
      setNotes(data);
    } catch (err: any) {
      console.error('Lỗi tải ghi chú:', err);
      setError('Không thể tải danh sách ghi chú. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  // Lọc ghi chú theo từ khóa
  const filteredNotes = notes.filter((note) => {
    const query = searchQuery.toLowerCase();
    return (
      note.title.toLowerCase().includes(query) ||
      note.content.toLowerCase().includes(query)
    );
  });

  // Xử lý xóa
  const handleDelete = async () => {
    if (!deleteTarget?.id) return;
    try {
      await deleteDiaryNote(deleteTarget.id);
      setNotes((prev) => prev.filter((n) => n.id !== deleteTarget.id));
    } catch (err) {
      console.error('Lỗi xóa:', err);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">

      {/* ── HEADER ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-800 dark:text-white">
                📓 Sổ tay sức khỏe
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Ghi lại hoạt động để đối chiếu với biểu đồ stress
              </p>
            </div>
            <button
              onClick={() => setModal({ mode: 'create', note: null })}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium shadow-sm transition shrink-0"
            >
              <span className="text-lg">+</span>
              <span className="hidden sm:inline">Thêm ghi chú</span>
            </button>
          </div>

          {/* Search bar */}
          <div className="mt-3 relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm ghi chú..."
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition text-sm"
            />
          </div>
        </div>
      </header>

      {/* ── MAIN CONTENT ───────────────────────────────────────────── */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6">

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="text-center py-12">
            <p className="text-red-500 mb-4">{error}</p>
            <button
              onClick={fetchNotes}
              className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition"
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Empty state — chưa có ghi chú */}
        {!loading && !error && notes.length === 0 && (
          <div className="text-center py-16">
            <div className="w-20 h-20 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-4">
              <span className="text-4xl">📝</span>
            </div>
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Chưa có ghi chú nào
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-sm mx-auto">
              Bắt đầu ghi lại hoạt động và cảm xúc của bạn để theo dõi sức khỏe tốt hơn.
            </p>
            <button
              onClick={() => setModal({ mode: 'create', note: null })}
              className="px-5 py-2.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium shadow-sm transition"
            >
              + Thêm ghi chú đầu tiên
            </button>
          </div>
        )}

        {/* Empty state — có ghi chú nhưng không tìm thấy */}
        {!loading && !error && notes.length > 0 && filteredNotes.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400">
              Không tìm thấy ghi chú nào phù hợp với "{searchQuery}"
            </p>
          </div>
        )}

        {/* Danh sách ghi chú */}
        {!loading && !error && filteredNotes.length > 0 && (
          <div className="space-y-4">
            {filteredNotes.map((note) => (
              <div
                key={note.id}
                className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md hover:border-primary-200 dark:hover:border-primary-700 transition group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    {/* Tiêu đề */}
                    <h3 className="font-semibold text-gray-800 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition truncate">
                      {note.title}
                    </h3>
                    {/* Thời gian */}
                    <p className="text-xs text-gray-400 mt-1">
                      {note.createdAt
                        ? new Date(note.createdAt).toLocaleString('vi-VN', {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : '--'}
                    </p>
                    {/* Nội dung */}
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 line-clamp-3">
                      {note.content}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition">
                    <button
                      onClick={() => setModal({ mode: 'edit', note })}
                      className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition"
                      title="Sửa"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => setDeleteTarget(note)}
                      className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                      title="Xóa"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tổng số */}
        {!loading && !error && filteredNotes.length > 0 && (
          <p className="text-center text-sm text-gray-400 mt-6">
            {filteredNotes.length === notes.length
              ? `Tổng ${notes.length} ghi chú`
              : `${filteredNotes.length} / ${notes.length} ghi chú`}
          </p>
        )}
      </main>

      {/* ── MODALS ─────────────────────────────────────────────────── */}
      <DiaryModal
        mode={modal.mode}
        note={modal.note}
        onClose={() => setModal({ mode: null, note: null })}
        onSaved={() => {
          setModal({ mode: null, note: null });
          fetchNotes();
        }}
      />

      {deleteTarget && (
        <ConfirmDeleteModal
          note={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onConfirmed={handleDelete}
        />
      )}
    </div>
  );
};

export default DiaryPage;
