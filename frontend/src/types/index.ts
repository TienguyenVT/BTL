/**
 * TypeScript Interfaces/Types cho dữ liệu sức khỏe IoMT.
 * Đồng bộ với HealthDataResponse DTO từ Java Backend.
 */

/** Dữ liệu sức khỏe từ API */
export interface HealthData {
  deviceId: string;
  userId: string;
  timestamp: string;        // ISO 8601 format

  // Chỉ số sinh lý (Body Sensors)
  bpm: number;              // Nhịp tim (beats per minute)
  spo2: number;             // Độ bão hòa oxy (%)
  bodyTemp: number;         // Nhiệt độ cơ thể (°C)
  gsrAdc: number;           // Điện trở da (ADC value)

  // Chỉ số môi trường (Environmental Sensors)
  extTempC: number;         // Nhiệt độ ngoài (°C)
  extHumidityPct: number;   // Độ ẩm (%)

  // Phân loại
  label: HealthLabel;       // Normal | Stress | Fever
  timeSlot: string;         // Morning | Afternoon | Evening
}

/** Nhãn trạng thái sức khỏe */
export type HealthLabel = 'Normal' | 'Stress' | 'Fever';

/** Props cho VitalCard component */
export interface VitalCardProps {
  title: string;            // Tên chỉ số (VD: "Nhịp tim")
  value: number;            // Giá trị hiện tại
  unit: string;             // Đơn vị (VD: "BPM", "%", "°C")
  icon: string;             // Emoji icon
  color: string;            // Tailwind color class
  minNormal: number;        // Ngưỡng bình thường - min
  maxNormal: number;        // Ngưỡng bình thường - max
}

/** Props cho HealthChart component */
export interface HealthChartProps {
  data: HealthData[];       // Dữ liệu lịch sử
  dataKey: keyof HealthData; // Trường dữ liệu hiển thị
  title: string;            // Tiêu đề biểu đồ
  color: string;            // Màu đường line
}

/** ─────────────────────────────────────────────────────────────
 * DIARY — Sổ tay sức khỏe cá nhân
 *───────────────────────────────────────────────────────────── */

/** Ghi chú sức khỏe cá nhân */
export interface DiaryNote {
  id?: string;
  title: string;
  content: string;
  createdAt?: string;
}

/** DTO gửi lên API (create/update) */
export interface DiaryDto {
  id?: string;
  title: string;
  content: string;
  createdAt?: string;
}

/** Props cho modal thêm/sửa ghi chú */
export interface DiaryModalProps {
  mode: 'create' | 'edit';
  note?: DiaryNote;
  onClose: () => void;
  onSaved: () => void;
}
