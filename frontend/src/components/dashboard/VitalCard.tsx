import React from 'react';
import { VitalCardProps } from '../../types';

/**
 * VitalCard Component - Hiển thị một chỉ số sức khỏe realtime.
 *
 * Features:
 *   - Hiển thị giá trị hiện tại với icon và đơn vị
 *   - Đổi màu theo trạng thái (bình thường / bất thường)
 *   - Responsive: co giãn theo grid layout cha
 *   - Micro-animation khi hover
 */
const VitalCard: React.FC<VitalCardProps> = ({
  title,
  value,
  unit,
  icon,
  color,
  minNormal,
  maxNormal,
}) => {
  // Kiểm tra giá trị có nằm trong ngưỡng bình thường
  const isNormal = value >= minNormal && value <= maxNormal;

  return (
    <div className="card group cursor-default">
      {/* ── Header: Icon + Title ──────────────────────────────── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {title}
          </h3>
        </div>

        {/* Indicator dot: xanh = bình thường, đỏ = bất thường */}
        <span
          className={`w-2.5 h-2.5 rounded-full transition-colors ${
            isNormal ? 'bg-green-400' : 'bg-red-400 animate-pulse'
          }`}
        />
      </div>

      {/* ── Value Display ─────────────────────────────────────── */}
      <div className="flex items-baseline gap-1">
        <span className={`text-3xl sm:text-4xl font-bold ${color}`}>
          {value.toFixed(1)}
        </span>
        <span className="text-sm text-gray-400 dark:text-gray-500 ml-1">
          {unit}
        </span>
      </div>

      {/* ── Normal Range Info ─────────────────────────────────── */}
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
        Bình thường: {minNormal} – {maxNormal} {unit}
      </p>

      {/* ── Status Bar ────────────────────────────────────────── */}
      <div className="mt-3 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isNormal ? 'bg-green-400' : 'bg-red-400'
          }`}
          style={{
            width: `${Math.min(((value - minNormal) / (maxNormal - minNormal)) * 100, 100)}%`,
          }}
        />
      </div>
    </div>
  );
};

export default VitalCard;
