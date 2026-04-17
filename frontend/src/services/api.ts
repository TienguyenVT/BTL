import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

const authHeader = (userId) => ({ headers: { 'X-User-Id': userId } });

// Auth
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);
export const getMe = (userId) => api.get('/auth/me', authHeader(userId));
export const updateUser = (userId, data) => {
  console.log('[DEBUG] updateUser called - userId:', userId, 'data:', data);
  return api.put('/auth', data, authHeader(userId));
};
export const deleteUser = (userId, password) => api.delete('/auth', { data: { password }, ...authHeader(userId) });

// Profile
export const getProfile = (userId) => api.get('/profile', authHeader(userId));
export const updateProfile = (userId, data) => api.put('/profile', data, authHeader(userId));

// Devices
export const getDevice = (userId, id) => api.get(`/devices/${id}`, authHeader(userId));
export const getDevices = (userId) => api.get('/devices', authHeader(userId));
export const addDevice = (userId, data) => api.post('/devices', data, authHeader(userId));
export const deleteDevice = (userId, id) => api.delete(`/devices/${id}`, authHeader(userId));
export const renameDevice = (userId, id, name) => api.patch(`/devices/${id}`, { name }, authHeader(userId));

// Health (READ-ONLY)
export const getLatestHealth = (userId) => api.get('/health/latest', authHeader(userId));
export const getHealthHistory = (userId, hours) => api.get('/health/history', { params: { hours }, ...authHeader(userId) });
export const getRecentHealth = (userId, limit) => api.get('/health/recent', { params: { limit }, ...authHeader(userId) });

// Sessions (Yeu cau X-User-Id header de loc theo device cua user)
export const getLatestSession = (userId) => api.get('/health/sessions/latest', authHeader(userId));
export const getLiveSession = (userId, deviceId) => {
  const params = deviceId ? { deviceId } : {};
  return api.get('/health/sessions/live', { params, ...authHeader(userId) });
};
export const getSessionById = (sessionId, userId) => api.get(`/health/sessions/${sessionId}`, authHeader(userId));
export const getSessionsHistory = (hours, userId, deviceId) => {
  const params = { hours };
  if (deviceId) params.deviceId = deviceId;
  return api.get('/health/sessions/history', { params, ...authHeader(userId) });
};
export const getAllSessions = (userId) => api.get('/health/sessions', authHeader(userId));

// Fever/Stress records from final_result (paginated) — for AlertsPage
export const getFeverStressRecords = (userId, page, size, deviceId) => {
  const params = { page, size };
  if (deviceId) params.deviceId = deviceId;
  return api.get('/health/sessions/fever-stress-records', { params, ...authHeader(userId) });
};

// Environment (realtime 1s)
export const getEnvironment = () => api.get('/health/environment');

// Diary
export const getDiaryNotes = (userId) => api.get('/diary-notes', authHeader(userId));
export const createDiaryNote = (userId, data) => api.post('/diary-notes', data, authHeader(userId));
export const updateDiaryNote = (userId, id, data) => api.put(`/diary-notes/${id}`, data, authHeader(userId));
export const deleteDiaryNote = (userId, id) => api.delete(`/diary-notes/${id}`, authHeader(userId));
export const getDiaryNotesByTimeRange = (userId, from, to) =>
  api.get('/diary-notes/by-time-range', { params: { from, to }, ...authHeader(userId) });

// Alerts
export const getAlerts = (userId) => api.get('/alerts', authHeader(userId));
export const getAlertCount = (userId) => api.get('/alerts/count', authHeader(userId));
export const deleteAlert = (userId, id) => api.delete(`/alerts/${id}`, authHeader(userId));
export const getUnreadAlerts = (userId) => api.get('/alerts/unread', authHeader(userId));
export const markAlertRead = (userId, id) => api.patch(`/alerts/${id}/read`, {}, authHeader(userId));

export default api;