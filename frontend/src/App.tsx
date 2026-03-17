import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';

/**
 * Root Component - Cấu hình routing cho ứng dụng.
 *
 * Routes:
 *   /dashboard  → Trang Dashboard chính
 *   /           → Redirect về /dashboard
 *
 * Có thể mở rộng thêm:
 *   /login      → Trang đăng nhập
 *   /history    → Trang xem lịch sử chi tiết
 *   /settings   → Trang cài đặt
 */
const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Trang Dashboard chính */}
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Redirect trang chủ về Dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* 404 - Trang không tồn tại */}
        <Route
          path="*"
          element={
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
              <div className="text-center">
                <h1 className="text-6xl font-bold text-gray-300">404</h1>
                <p className="text-gray-500 mt-2">Trang không tồn tại</p>
                <a
                  href="/dashboard"
                  className="mt-4 inline-block text-primary-500 hover:underline"
                >
                  ← Về Dashboard
                </a>
              </div>
            </div>
          }
        />
      </Routes>
    </Router>
  );
};

export default App;
