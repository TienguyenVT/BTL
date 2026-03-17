import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { HealthChartProps, HealthData } from '../../types';

/**
 * HealthChart Component - Biểu đồ lịch sử chỉ số sức khỏe.
 *
 * Sử dụng Recharts LineChart:
 *   - Responsive container tự co giãn theo parent
 *   - Trục X: timestamp (format giờ:phút)
 *   - Trục Y: giá trị chỉ số
 *   - Tooltip hiển thị chi tiết khi hover
 */
const HealthChart: React.FC<HealthChartProps> = ({ data, dataKey, title, color }) => {
  /**
   * Format timestamp cho trục X.
   * Chỉ hiển thị giờ:phút để tiết kiệm không gian.
   */
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="card">
      {/* ── Chart Title ───────────────────────────────────────── */}
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">
        {title}
      </h3>

      {/* ── Chart Container ───────────────────────────────────── */}
      {/* Responsive: chiều cao cố định, chiều rộng co giãn theo parent */}
      <div className="w-full h-48 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            {/* Grid nền */}
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />

            {/* Trục X: Thời gian */}
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTime}
              tick={{ fontSize: 11 }}
              stroke="#9ca3af"
            />

            {/* Trục Y: Giá trị */}
            <YAxis
              tick={{ fontSize: 11 }}
              stroke="#9ca3af"
              width={40}
            />

            {/* Tooltip khi hover */}
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: 'none',
                borderRadius: '0.5rem',
                color: '#f3f4f6',
                fontSize: '0.75rem',
              }}
              labelFormatter={formatTime}
            />

            {/* Đường line chính */}
            <Line
              type="monotone"
              dataKey={dataKey as string}
              stroke={color}
              strokeWidth={2}
              dot={false}              // Ẩn dot để gọn hơn
              activeDot={{ r: 4 }}     // Dot chỉ hiện khi hover
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default HealthChart;
