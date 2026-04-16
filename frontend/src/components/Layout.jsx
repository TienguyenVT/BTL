import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { LayoutDashboard, Clock, BookOpen, User, Cpu, Bell, LogOut, Menu, Heart } from 'lucide-react';
import { getAlertCount } from '../services/api';

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/history', icon: Clock, label: 'History' },
  { path: '/diary', icon: BookOpen, label: 'Diary' },
  { path: '/profile', icon: User, label: 'Profile' },
  { path: '/devices', icon: Cpu, label: 'Devices' },
  { path: '/alerts', icon: Bell, label: 'Alerts' },
];

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const userId = localStorage.getItem('backendUserId');
  const userName = localStorage.getItem('backendUserName') || 'User';

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const res = await getAlertCount(userId);
        setUnreadCount(res.data.unreadCount || 0);
      } catch {}
    };
    fetchCount();
    const interval = setInterval(fetchCount, 60000);
    return () => clearInterval(interval);
  }, [userId]);

  const handleLogout = () => {
    localStorage.removeItem('backendUserId');
    localStorage.removeItem('backendUserName');
    window.location.reload();
  };

  const SidebarContent = () => (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-200">
        <div className="w-8 h-8 bg-teal-500 rounded-lg flex items-center justify-center">
          <Heart size={16} className="text-white" />
        </div>
        <span className="text-slate-800 font-bold text-lg">IoMT Health</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ path, icon: Icon, label }) => {
          const active = location.pathname === path;
          return (
            <Link
              key={path}
              to={path}
              onClick={() => setSidebarOpen(false)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? 'bg-teal-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-teal-600'
              }`}
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === 'Alerts' && unreadCount > 0 && (
                <span className="ml-auto bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
      <div className="px-3 py-4 border-t border-slate-200">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-600 hover:bg-slate-100 hover:text-red-600 w-full transition-colors"
        >
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex w-60 bg-white flex-col flex-shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div className="fixed inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
          <aside className="relative w-60 bg-white flex flex-col z-50">
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <header className="lg:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-teal-500 rounded-lg flex items-center justify-center">
              <Heart size={14} className="text-white" />
            </div>
            <span className="font-bold text-slate-800">IoMT Health</span>
          </div>
          <button onClick={() => setSidebarOpen(true)} className="p-2 rounded-lg hover:bg-slate-100">
            <Menu size={20} />
          </button>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>

        {/* Mobile Bottom Nav */}
        <nav className="lg:hidden flex bg-white border-t border-slate-200">
          {navItems.map(({ path, icon: Icon, label }) => {
            const active = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                className={`flex-1 flex flex-col items-center py-2 text-xs relative ${
                  active ? 'text-teal-600' : 'text-slate-500'
                }`}
              >
                <Icon size={20} />
                <span className="mt-0.5 hidden sm:block">{label}</span>
                {label === 'Alerts' && unreadCount > 0 && (
                  <span className="absolute top-1 right-1/4 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center text-[10px]">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}