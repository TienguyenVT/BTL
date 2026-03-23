/**
 * API Service - Gọi Backend RESTful API bằng Axios.
 * Tập trung quản lý tất cả API calls tại một nơi.
 *
 * Base URL trỏ tới Spring Boot backend (port 8080).
 * Vite proxy đã được cấu hình trong vite.config.ts.
 */

import axios from 'axios';
import { HealthData } from '../types';

// ── Axios Instance ──────────────────────────────────────────────────────
const api = axios.create({
  baseURL: '/api',              // Proxy qua Vite → http://localhost:8080/api
  timeout: 10000,               // Timeout 10 giây
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Interceptor: Log lỗi ────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API] Lỗi:', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

// ── API Functions ───────────────────────────────────────────────────────

/**
 * Lấy dữ liệu sức khỏe mới nhất của user.
 * Endpoint: GET /api/health/latest?userId=xxx
 */
export const getLatestHealthData = async (userId: string): Promise<HealthData | null> => {
  try {
    const response = await api.get<HealthData>('/health/latest', {
      params: { userId },
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 204) {
      return null; // Không có dữ liệu
    }
    throw error;
  }
};

/**
 * Lấy lịch sử dữ liệu theo khoảng thời gian.
 * Endpoint: GET /api/health/history?userId=xxx&hours=24
 */
export const getHealthHistory = async (
  userId: string,
  hours: number = 24
): Promise<HealthData[]> => {
  const response = await api.get<HealthData[]>('/health/history', {
    params: { userId, hours },
  });
  return response.data;
};

/**
 * Lấy N bản ghi gần nhất.
 * Endpoint: GET /api/health/recent?userId=xxx&limit=20
 */
export const getRecentHealthData = async (
  userId: string,
  limit: number = 20
): Promise<HealthData[]> => {
  const response = await api.get<HealthData[]>('/health/recent', {
    params: { userId, limit },
  });
  return response.data;
};

// ═══════════════════════════════════════════════════════════════════════
// DIARY — Sổ tay sức khỏe cá nhân
// ═══════════════════════════════════════════════════════════════════════

import { DiaryNote } from '../types';

/**
 * Lấy danh sách ghi chú.
 * Endpoint: GET /api/diary-notes
 * Header:   Authorization: Bearer <token>
 */
export const getDiaryNotes = async (): Promise<DiaryNote[]> => {
  const response = await api.get<DiaryNote[]>('/diary-notes');
  return response.data;
};

/**
 * Tạo ghi chú mới.
 * Endpoint: POST /api/diary-notes
 */
export const createDiaryNote = async (data: { title: string; content: string }): Promise<DiaryNote> => {
  const response = await api.post<DiaryNote>('/diary-notes', data);
  return response.data;
};

/**
 * Cập nhật ghi chú.
 * Endpoint: PUT /api/diary-notes/{id}
 */
export const updateDiaryNote = async (
  id: string,
  data: { title: string; content: string }
): Promise<DiaryNote> => {
  const response = await api.put<DiaryNote>(`/diary-notes/${id}`, data);
  return response.data;
};

/**
 * Xóa ghi chú.
 * Endpoint: DELETE /api/diary-notes/{id}
 */
export const deleteDiaryNote = async (id: string): Promise<void> => {
  await api.delete(`/diary-notes/${id}`);
};

export default api;
