/** @type {import('tailwindcss').Config} */
export default {
  // Scan tất cả file React/TypeScript để purge CSS không dùng
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Custom color palette cho IoMT Dashboard
      colors: {
        primary: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          500: '#6366f1',   // Indigo chính
          600: '#4f46e5',
          700: '#4338ca',
        },
        vital: {
          heart:   '#ef4444',  // Đỏ - Nhịp tim
          oxygen:  '#3b82f6',  // Xanh dương - SpO2
          temp:    '#f59e0b',  // Cam - Nhiệt độ
          gsr:     '#10b981',  // Xanh lá - GSR
        },
        status: {
          normal:  '#22c55e',  // Xanh lá - Bình thường
          stress:  '#f59e0b',  // Cam - Căng thẳng
          fever:   '#ef4444',  // Đỏ - Sốt
        }
      },
      // Font family
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
