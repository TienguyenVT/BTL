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

// Profile
export const getProfile = (userId) => api.get('/profile', authHeader(userId));
export const updateProfile = (userId, data) => api.put('/profile', data, authHeader(userId));

// Devices
export const getDevices = (userId) => api.get('/devices', authHeader(userId));
export const addDevice = (userId, data) => api.post('/devices', data, authHeader(userId));
export const deleteDevice = (userId, id) => api.delete(`/devices/${id}`, authHeader(userId));

// Health (READ-ONLY)
export const getLatestHealth = (userId) => api.get('/health/latest', authHeader(userId));
export const getHealthHistory = (userId, hours) => api.get('/health/history', { params: { hours }, ...authHeader(userId) });
export const getRecentHealth = (userId, limit) => api.get('/health/recent', { params: { limit }, ...authHeader(userId) });

// Sessions
export const getLatestSession = () => api.get('/health/sessions/latest');
export const getLiveSession = () => api.get('/health/sessions/live');
export const getSessionById = (sessionId) => api.get(`/health/sessions/${sessionId}`);
export const getSessionsHistory = (hours) => api.get('/health/sessions/history', { params: { hours } });
export const getAllSessions = () => api.get('/health/sessions');

// Environment (realtime 1s)
export const getEnvironment = () => api.get('/health/environment');

// Diary
export const getDiaryNotes = (userId) => api.get('/diary-notes', authHeader(userId));
export const createDiaryNote = (userId, data) => api.post('/diary-notes', data, authHeader(userId));
export const updateDiaryNote = (userId, id, data) => api.put(`/diary-notes/${id}`, data, authHeader(userId));
export const deleteDiaryNote = (userId, id) => api.delete(`/diary-notes/${id}`, authHeader(userId));

// Alerts
export const getAlerts = (userId) => api.get('/alerts', authHeader(userId));
export const getAlertCount = (userId) => api.get('/alerts/count', authHeader(userId));
export const deleteAlert = (userId, id) => api.delete(`/alerts/${id}`, authHeader(userId));

export default api;