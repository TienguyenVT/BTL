import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import DiaryPage from './pages/DiaryPage';

/**
 * Root Component - Cấu hình routing cho ứng dụng.
 *
 * Routes:
 *   /dashboard  → Trang Dashboard chính
 *   /diary     → Trang Sổ tay sức khỏe
 *   /          → Redirect về /dashboard
 *
 * Layout có thể mở rộng sau bằng Sidebar/Navbar.
 */
const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Trang Dashboard chính */}
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Trang Sổ tay sức khỏe */}
        <Route path="/diary" element={<DiaryPage />} />

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
