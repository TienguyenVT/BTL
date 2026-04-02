import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClientInstance } from '@/lib/query-client';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import AppShell from './components/AppShell';
import DashboardPage from './pages/DashboardPage';
import HistoryPage from './pages/HistoryPage';
import DiaryPage from './pages/DiaryPage';
import ProfilePage from './pages/ProfilePage';
import DevicesPage from './pages/DevicesPage';
import AlertsPage from './pages/AlertsPage';

const AppRoutes = () => {
  const { isLoadingAuth } = useAuth();

  if (isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-800 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="diary" element={<DiaryPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="devices" element={<DevicesPage />} />
        <Route path="alerts" element={<AlertsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router>
          <AppRoutes />
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  );
}

export default App;
