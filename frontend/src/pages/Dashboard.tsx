import React, { useState, useEffect } from 'react';
import VitalCard from '../components/dashboard/VitalCard';
import HealthChart from '../components/dashboard/HealthChart';
import { HealthData } from '../types';
import { getLatestHealthData, getHealthHistory } from '../services/api';

/**
 * Dashboard Page - Trang giám sát sức khỏe chính.
 *
 * Layout Responsive (Mobile-first với Tailwind CSS):
 *   - Mobile  (< 640px):  1 cột
 *   - Tablet  (sm: 640px): 2 cột
 *   - Desktop (lg: 1024px): 3 cột (hoặc 4 cột cho VitalCards)
 *
 * Sections:
 *   1. Header: Tiêu đề + trạng thái user
 *   2. Vital Cards: 4 card hiển thị BPM, SpO2, Body Temp, GSR
 *   3. Charts: 2 biểu đồ lịch sử (BPM + SpO2)
 *   4. Status Badge: Nhãn trạng thái sức khỏe hiện tại
 */
const Dashboard: React.FC = () => {
  // ── State ─────────────────────────────────────────────────────────────
  const [latestData, setLatestData] = useState<HealthData | null>(null);
  const [historyData, setHistoryData] = useState<HealthData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // TODO: Thay bằng userId thực tế từ authentication
  const userId = 'Nguyen_Van';

  // ── Fetch Data ────────────────────────────────────────────────────────
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Gọi đồng thời 2 API
        const [latest, history] = await Promise.all([
          getLatestHealthData(userId),
          getHealthHistory(userId, 24), // 24 giờ
        ]);

        setLatestData(latest);
        setHistoryData(history);
      } catch (err) {
        console.error('Lỗi tải dữ liệu:', err);
        setError('Không thể kết nối server. Vui lòng thử lại.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Auto-refresh mỗi 30 giây (realtime dashboard)
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [userId]);

  // ── Loading State ─────────────────────────────────────────────────────
  if (loading && !latestData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-500">Đang tải dữ liệu...</p>
        </div>
      </div>
    );
  }

  // ── Error State ───────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="card text-center max-w-md">
          <p className="text-red-500 text-lg mb-2">⚠️ {error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6 lg:p-8">

      {/* ═══════════════════════════════════════════════════════════════
          HEADER
          ═══════════════════════════════════════════════════════════════ */}
      <header className="mb-6 sm:mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 dark:text-white">
              🏥 IoMT Dashboard
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Giám sát sức khỏe thời gian thực
            </p>
          </div>

          {/* Trạng thái sức khỏe hiện tại */}
          {latestData && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">Trạng thái:</span>
              <span
                className={
                  latestData.label === 'Normal' ? 'badge-normal' :
                  latestData.label === 'Stress' ? 'badge-stress' :
                  'badge-fever'
                }
              >
                {latestData.label === 'Normal' ? '✓ Bình thường' :
                 latestData.label === 'Stress' ? '⚡ Căng thẳng' :
                 '🌡 Sốt'}
              </span>
            </div>
          )}
        </div>
      </header>

      {/* ═══════════════════════════════════════════════════════════════
          VITAL CARDS - Responsive Grid
          Mobile: 1 cột | Tablet: 2 cột | Desktop: 4 cột
          ═══════════════════════════════════════════════════════════════ */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
        <VitalCard
          title="Nhịp tim"
          value={latestData?.bpm ?? 0}
          unit="BPM"
          icon="❤️"
          color="text-vital-heart"
          minNormal={60}
          maxNormal={100}
        />
        <VitalCard
          title="SpO2"
          value={latestData?.spo2 ?? 0}
          unit="%"
          icon="🫁"
          color="text-vital-oxygen"
          minNormal={95}
          maxNormal={100}
        />
        <VitalCard
          title="Nhiệt độ cơ thể"
          value={latestData?.bodyTemp ?? 0}
          unit="°C"
          icon="🌡️"
          color="text-vital-temp"
          minNormal={36.1}
          maxNormal={37.2}
        />
        <VitalCard
          title="Điện trở da"
          value={latestData?.gsrAdc ?? 0}
          unit="ADC"
          icon="⚡"
          color="text-vital-gsr"
          minNormal={1500}
          maxNormal={3000}
        />
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          CHARTS - Responsive Grid
          Mobile: 1 cột (stack) | Desktop: 2 cột (side by side)
          ═══════════════════════════════════════════════════════════════ */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-6 sm:mb-8">
        <HealthChart
          data={historyData}
          dataKey="bpm"
          title="📈 Lịch sử nhịp tim (24h)"
          color="#ef4444"
        />
        <HealthChart
          data={historyData}
          dataKey="spo2"
          title="📈 Lịch sử SpO2 (24h)"
          color="#3b82f6"
        />
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          ENVIRONMENT SECTION
          Mobile: 1 cột | Tablet+: 3 cột
          ═══════════════════════════════════════════════════════════════ */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
        <div className="card text-center">
          <p className="text-sm text-gray-500">🌡 Nhiệt độ ngoài</p>
          <p className="text-2xl font-bold text-orange-500 mt-1">
            {latestData?.extTempC?.toFixed(1) ?? '--'} °C
          </p>
        </div>
        <div className="card text-center">
          <p className="text-sm text-gray-500">💧 Độ ẩm</p>
          <p className="text-2xl font-bold text-blue-500 mt-1">
            {latestData?.extHumidityPct?.toFixed(1) ?? '--'} %
          </p>
        </div>
        <div className="card text-center">
          <p className="text-sm text-gray-500">📡 Thiết bị</p>
          <p className="text-2xl font-bold text-indigo-500 mt-1">
            {latestData?.deviceId ?? '--'}
          </p>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          FOOTER
          ═══════════════════════════════════════════════════════════════ */}
      <footer className="mt-8 text-center text-xs text-gray-400 dark:text-gray-600">
        <p>Cập nhật lần cuối: {latestData?.timestamp
          ? new Date(latestData.timestamp).toLocaleString('vi-VN')
          : '--'
        }</p>
        <p className="mt-1">IoMT Health Monitor © 2026 • Auto-refresh mỗi 30 giây</p>
      </footer>
    </div>
  );
};

export default Dashboard;
