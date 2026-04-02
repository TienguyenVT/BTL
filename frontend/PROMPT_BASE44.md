# Base44 Prompt: IoMT Health Monitoring Dashboard — Frontend

**Target:** Generate a complete React TypeScript frontend for the IoMT (Internet of Medical Things) Health Monitoring System.
**Backend:** Spring Boot REST API running at `http://localhost:8080/api` (see full API spec below).
**Build this frontend FROM SCRATCH using base44. This prompt replaces the existing incomplete frontend.**

---

## 1. SYSTEM OVERVIEW

### 1.1 Project Name
**IoMT Health Monitor** — A real-time health monitoring dashboard for wearable IoT devices (ESP32 sensors).

### 1.2 Core Purpose
A web dashboard that:
- Displays real-time physiological data (heart rate, SpO2, body temperature, GSR, environment data) from ESP32 sensors.
- Allows users to manage their health diary.
- Shows AI-generated health alerts (stress detection, fever detection).
- Displays historical health data in charts.
- User registration and login.

### 1.3 System Architecture

```
ESP32 Sensors (DHT11 + MAX30102 + GSR)
    │
    │  HTTP / MQTT → Python IoT Ingestion (port 8000)
    ▼
MongoDB (iomt_health_monitor database)
    │
    ├── users              (auth accounts — collection "users")
    ├── profiles           (age, height, weight — collection "profiles")
    ├── devices            (ESP32 MAC registry — collection "devices")
    ├── diary_notes        (personal diary — collection "diary_notes")
    ├── alerts             (AI-generated alerts — collection "alerts")
    ├── realtime_health_data  (live sensor readings)
    └── final_result       (ML-processed data with label + confidence)
    │
    ▼
Spring Boot Backend API (port 8080)
    │
    ▼
React Frontend (port 5173)  ← GENERATE THIS WITH BASE44
```

### 1.4 Target Users
- End users (patients, health-conscious individuals) monitoring their vital signs.
- The dashboard should be mobile-first and accessible on desktop.

---

## 2. BACKEND API SPECIFICATION

**Base URL:** `http://localhost:8080/api`
**Auth Method:** Header `X-User-Id: <user_id>` (simulated auth; user_id comes from login response).
**Content-Type:** `application/json`
**CORS:** Allow `localhost:5173`, `localhost:5174`, `localhost:3000`

### 2.1 Authentication (`/api/auth`) — No auth header needed

#### POST `/api/auth/register`
Create a new user account.
```
Request:
{ "email": "string", "password": "string", "name": "string" }

Success 201:
{ "id": "string", "name": "string", "message": "Dang ky thanh cong" }

Error 400: { "message": "Email, password, name la bat buoc" }
Error 409: { "message": "Email da ton tai" }
```

#### POST `/api/auth/login`
```
Request:
{ "email": "string", "password": "string" }

Success 200:
{ "id": "string", "name": "string", "message": "Dang nhap thanh cong" }

Error 401: { "message": "Email khong ton tai" | "Mat khau khong dung" }
```

> **IMPORTANT:** After login, extract the `id` field and store it as the `userId`. Send this `userId` in the `X-User-Id` header for all subsequent API calls.

---

### 2.2 Profile (`/api/profile`) — Requires `X-User-Id` header

#### GET `/api/profile`
Get user profile. Creates default profile if none exists.
```
Success 200:
{
  "userId": "string",
  "age": 25 | null,
  "height": 170.0 | null,   // in cm
  "weight": 65.0 | null,    // in kg
  "bmi": 22.5 | null,       // calculated dynamically: weight / (height/100)^2
  "updatedAt": "2026-04-01T11:00:00Z" | null
}
```

#### PUT `/api/profile`
Update profile. Only non-null fields are updated.
```
Request:
{ "age": 26, "height": 172.0, "weight": 68.0 }

Success 200: (same format as GET response)
```

**BMI Reference:**
| BMI Range | Classification |
|---|---|
| < 18.5 | Underweight |
| 18.5 – 24.9 | Normal |
| 25 – 29.9 | Overweight |
| >= 30 | Obese |

---

### 2.3 Devices (`/api/devices`) — Requires `X-User-Id` header

#### POST `/api/devices`
Register a new ESP32 device.
```
Request:
{ "macAddress": "AA:BB:CC:DD:EE:FF", "name": "ESP32-Bedroom" }

Success 201:
{
  "id": "string",
  "macAddress": "AA:BB:CC:DD:EE:FF",
  "name": "ESP32-Bedroom",
  "createdAt": "2026-04-01T11:00:00Z",
  "message": "Them thiet bi thanh cong"
}

Error 400: { "message": "MAC Address la bat buoc" }
Error 409: { "message": "MAC Address da ton tai" }
```

#### GET `/api/devices`
List all registered devices.
```
Success 200: Array of:
[
  {
    "id": "string",
    "macAddress": "AA:BB:CC:DD:EE:FF",
    "name": "ESP32-Bedroom",
    "createdAt": "2026-04-01T11:00:00Z",
    "message": null
  }
]
```

#### DELETE `/api/devices/{id}`
Delete a device.
```
Success 204: (empty body)
Error 404: (empty body)
```

---

### 2.4 Health Data (`/api/health`) — Requires `X-User-Id` header
**Data source:** Collection `final_result` (written by the Python IoT Ingestion module). This frontend READS ONLY.
**NOTE:** The backend reads from `realtime_health_data` which mirrors `final_result` — both use the same field names.

#### GET `/api/health/latest`
Get the most recent health reading.
```
Success 200 — returns a HealthData object with these exact JSON field names:
{
  "id": "string",
  "userId": "string",          // mapped from user_id
  "deviceId": "string",        // mapped from device_id
  "timestamp": "string",      // ISO 8601 datetime
  "bpm": 95.0,                 // Heart rate — normal: 60–100 bpm
  "spo2": 99.0,                // Blood oxygen — normal: 95–100%
  "bodyTemp": 27.9,            // Body temperature °C (DHT11 sensor, raw value)
  "gsrAdc": 50.0,              // Galvanic Skin Response ADC value
  "extTempC": 28.5,            // Environment temperature °C (DHT11)
  "extHumidityPct": 65.0,      // Environment humidity % (DHT11)
  "label": "Normal",           // Classification: "Normal" | "Stress" | "Fever"
  "timeSlot": "morning"        // "morning" | "afternoon" | "evening" | "night"
}

Error: Returns null if no data exists.
```

#### GET `/api/health/history`
Get health data over a time range.
```
Query params:
  hours (integer, default: 24) — number of hours to look back

Success 200: Array of HealthData objects, sorted oldest → newest
```

#### GET `/api/health/recent`
Get the N most recent records.
```
Query params:
  limit (integer, default: 20)

Success 200: Array of HealthData objects, sorted newest → oldest
```

---

### 2.5 Diary Notes (`/api/diary-notes`) — Requires `X-User-Id` header

#### POST `/api/diary-notes`
Create a new diary entry.
```
Request:
{ "title": "string", "content": "string" }   // both fields required

Success 201:
{
  "id": "string",
  "title": "string",
  "content": "string",
  "createdAt": "2026-04-01T11:00:00Z"
}
```

#### GET `/api/diary-notes`
List all diary entries (newest first).
```
Success 200: Array of:
[
  {
    "id": "string",
    "title": "string",
    "content": "string",
    "createdAt": "2026-04-01T11:00:00Z"
  }
]
```

#### GET `/api/diary-notes/{id}`
Get a single diary entry.
```
Success 200: (same format as above)
Error 404: (empty body)
```

#### PUT `/api/diary-notes/{id}`
Update a diary entry. Only non-null fields are updated.
```
Request:
{ "title": "string", "content": "string" }   // both optional

Success 200: (updated entry)
Error 404: (empty body)
```

#### DELETE `/api/diary-notes/{id}`
Delete a diary entry.
```
Success 204: (empty body)
Error 404: (empty body)
```

---

### 2.6 Alerts (`/api/alerts`) — Requires `X-User-Id` header
**Alerts are auto-generated by the AI analysis system. Users can only READ and DELETE.**

#### GET `/api/alerts`
List all alerts (newest first).
```
Success 200: Array of:
[
  {
    "id": "string",
    "label": "Stress",     // "Stress" or "Fever"
    "message": "Muc do stress cao: BPM 95, GSR 820",
    "timestamp": "2026-04-01T10:30:00Z",
    "isRead": false
  }
]
```

#### GET `/api/alerts/count`
Get count of unread alerts.
```
Success 200:
{ "unreadCount": 3 }
```

#### DELETE `/api/alerts/{id}`
Delete an alert.
```
Success 204: (empty body)
Error 404: (empty body)
```

---

## 3. DATA MODELS (TypeScript Interfaces)

**IMPORTANT:** Backend JSON uses `camelCase` field names (mapped from MongoDB `snake_case`). Use these exact names — do NOT rename them. The `name` field in `Device` can be `null`.

```typescript
// ── Auth ──────────────────────────────────────────────────────────────────────
interface AuthResponse {
  id: string;
  name: string;
  message: string;
}

interface LoginRequest {
  email: string;
  password: string;
}

interface RegisterRequest extends LoginRequest {
  name: string;
}

// ── Health Data (from /api/health/*) ──────────────────────────────────────────
// This data is WRITTEN by the Python IoT Ingestion module.
// The frontend only READS it — never write to health collections.
interface HealthData {
  id: string;
  userId: string;       // backend maps from user_id
  deviceId: string;     // backend maps from device_id
  timestamp: string;     // ISO 8601 datetime
  bpm: number;         // Heart rate — normal: 60–100 bpm
  spo2: number;        // Blood oxygen — normal: 95–100%
  bodyTemp: number;   // Body temperature °C (DHT11 raw value)
  gsrAdc: number;     // Galvanic skin response ADC value
  extTempC: number;    // Environment temperature °C (DHT11)
  extHumidityPct: number; // Environment humidity % (DHT11)
  label: 'Normal' | 'Stress' | 'Fever';
  timeSlot: 'morning' | 'afternoon' | 'evening' | 'night';
}

// ── Profile ───────────────────────────────────────────────────────────────────
interface Profile {
  userId: string;
  age: number | null;
  height: number | null;  // in cm
  weight: number | null;  // in kg
  bmi: number | null;    // calculated: weight / (height/100)^2
  updatedAt: string | null;
}

// ── Device ────────────────────────────────────────────────────────────────────
interface Device {
  id: string;
  macAddress: string;   // ESP32 MAC address (unique)
  name: string | null;  // can be null
  createdAt: string;    // ISO 8601 datetime
  message?: string;     // only present in error responses
}

// ── Diary ──────────────────────────────────────────────────────────────────────
interface DiaryNote {
  id?: string;         // only present in responses
  title: string;
  content: string;
  createdAt?: string; // only present in responses
}

// ── Alert ──────────────────────────────────────────────────────────────────────
interface Alert {
  id: string;
  label: 'Stress' | 'Fever';
  message: string;
  timestamp: string;    // ISO 8601 datetime
  isRead: boolean;
}
```

---

## 4. FEATURE REQUIREMENTS

### 4.1 Pages / Screens

#### A. Login / Register Page (`/login`, `/register`)
- **Register:** Form with email, password, name fields. Show success/error messages.
- **Login:** Form with email, password. On success, store `userId` in `localStorage` and redirect to dashboard.
- **Switch between login and register** modes on the same page.
- Use a clean, modern card-based design with a health/medical theme.

#### B. Dashboard Page (`/dashboard`) — Main landing page after login
- **Vital Signs Cards (top section):** Display 4 large cards showing latest values:
  - Heart Rate (BPM) — color: red `#ef4444`
  - Blood Oxygen (SpO2 %) — color: blue `#3b82f6`
  - Body Temperature (°C) — color: orange `#f59e0b`
  - GSR (ADC value) — color: green `#10b981`
- Each card shows: current value, label, status indicator (Normal/Warning/Danger).
- **Health Status Banner:** Shows the current `label` (Normal/Stress/Fever) with appropriate color (green/orange/red).
- **Health Trend Chart:** A line chart (using Recharts) showing BPM and SpO2 over the last 24 hours.
- **Time Slot indicator:** Shows current time slot (morning/afternoon/evening/night).
- **Auto-refresh:** Reload latest data every 30 seconds.
- **Environment info:** Small cards showing external temperature and humidity.

#### C. Health History Page (`/history`)
- **Time Range Selector:** Buttons/tabs for 6h, 24h, 7 days options.
- **Multi-line Chart:** BPM, SpO2, body temperature over selected time range.
- **Data Table:** Scrollable table showing all readings in the selected period with timestamp.
- **Filter by label:** Toggle to show only abnormal readings (Stress/Fever).

#### D. Diary Page (`/diary`)
- **List View:** Cards showing diary entries (newest first), each with title, content preview, and timestamp.
- **Search Bar:** Filter diary entries by title or content.
- **Create Entry:** Modal or inline form with title and content fields.
- **Edit Entry:** Click on entry to edit title/content.
- **Delete Entry:** Delete button with confirmation.
- **Empty State:** Friendly message when no diary entries exist.

#### E. Profile Page (`/profile`)
- **Profile Info Card:** Shows name, age, height, weight, and calculated BMI.
- **Edit Form:** Input fields for age, height, weight. PUT only sends non-null values.
- **BMI Indicator:** Visual BMI scale/bar showing current BMI and classification.
- **Save button** with loading and success states.

#### F. Devices Page (`/devices`)
- **Device List:** Cards showing registered ESP32 devices with MAC address, name, and registration date.
- **Add Device Form:** Input for MAC address and optional name.
- **Delete Device:** With confirmation.
- **Empty State:** Guidance when no devices registered.

#### G. Alerts Page (`/alerts`)
- **Alert List:** Cards showing alerts with:
  - Icon/color based on type (Stress = orange bell, Fever = red thermometer)
  - Label ("Stress" or "Fever")
  - Message text
  - Timestamp
  - Unread indicator (bold/new badge)
- **Unread Count Badge:** Shown in the navigation sidebar.
- **Delete Alert:** Remove individual alerts.
- **Empty State:** Friendly message when no alerts exist.
- **Auto-refresh:** Poll for new alerts every 60 seconds.

### 4.2 Navigation
- **Sidebar navigation** (desktop) / **Bottom tab navigation** (mobile).
- Menu items: Dashboard, History, Diary, Profile, Devices, Alerts.
- Logout button in sidebar/header.
- Unread alert count badge on Alerts menu item.

### 4.3 Global Features
- **Loading states:** Skeleton loaders or spinner when fetching data.
- **Error handling:** Toast notifications or inline error messages on API failures.
- **Empty states:** Friendly illustrations/messages when no data.
- **Responsive design:** Mobile-first, works on phones and desktop.
- **Auth guard:** Redirect to `/login` if no `userId` in localStorage.

---

## 5. DESIGN GUIDELINES

### 5.1 Color Palette

```javascript
// Primary brand color
primary: {
  500: '#6366f1',  // Indigo
  600: '#4f46e5',
}

// Vital sign card colors
vital: {
  heart: '#ef4444',    // Heart rate / BPM — red
  oxygen: '#3b82f6',   // SpO2 — blue
  temp: '#f59e0b',     // Temperature — orange
  gsr: '#10b981',      // GSR — green
}

// Health status colors
status: {
  normal: '#22c55e',   // Green
  stress: '#f59e0b',   // Orange/Yellow
  fever: '#ef4444',    // Red
  neutral: '#6b7280',  // Gray
}

// Background colors
bg: {
  page: '#f8fafc',     // Light gray page bg
  card: '#ffffff',      // White cards
  sidebar: '#1e293b',  // Dark slate sidebar
  sidebarText: '#94a3b8',
}
```

### 5.2 Typography
- Use a clean sans-serif font (Inter or system-ui).
- Large display numbers for vital signs (36-48px bold).
- Body text: 14-16px.
- Section headers: 20-24px bold.

### 5.3 Layout
- **Sidebar:** 240px wide on desktop, hidden with hamburger menu on mobile.
- **Main content:** Fluid, max-width 1200px, centered.
- **Cards:** Rounded corners (8-12px), subtle shadow, white background.
- **Grid for vital cards:** 2x2 on mobile, 4 columns on desktop.

### 5.4 Icons
- Use Lucide React icons or Heroicons for consistency.
- Each vital sign should have a recognizable icon (heart for BPM, droplet for SpO2, thermometer for temp, wave for GSR).

### 5.5 Charts (using Recharts)
- Line charts with smooth curves.
- Use the vital sign colors for respective lines.
- Tooltips showing exact values and timestamps.
- Responsive containers.

---

## 6. TECHNICAL STACK (MUST USE)

### 6.1 Required Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "axios": "^1.6.7",
    "recharts": "^2.12.0",
    "lucide-react": "latest"
  },
  "devDependencies": {
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.3.3",
    "vite": "^5.1.0"
  }
}
```

### 6.2 API Service Layer
Create `src/services/api.ts` with all API calls using Axios.

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Helper: build auth headers
const authHeader = (userId: string) => ({ headers: { 'X-User-Id': userId } });

// ── Auth (no auth header needed) ─────────────────────────────────────────────
export const register = (data: RegisterRequest) =>
  api.post<AuthResponse>('/auth/register', data);

export const login = (data: LoginRequest) =>
  api.post<AuthResponse>('/auth/login', data);

// ── Profile ───────────────────────────────────────────────────────────────────
export const getProfile = (userId: string) =>
  api.get<Profile>('/profile', authHeader(userId));

// PUT sends only non-null fields (age/height/weight can be null to mean "clear")
export const updateProfile = (userId: string, data: Partial<Profile>) =>
  api.put<Profile>('/profile', data, authHeader(userId));

// ── Devices ───────────────────────────────────────────────────────────────────
export const getDevices = (userId: string) =>
  api.get<Device[]>('/devices', authHeader(userId));

export const addDevice = (userId: string, data: { macAddress: string; name?: string }) =>
  api.post<Device>('/devices', data, authHeader(userId));

export const deleteDevice = (userId: string, id: string) =>
  api.delete(`/devices/${id}`, authHeader(userId));

// ── Health ─────────────────────────────────────────────────────────────────────
// These are READ-ONLY — the Python IoT Ingestion module WRITES this data.
export const getLatestHealth = (userId: string) =>
  api.get<HealthData | null>('/health/latest', authHeader(userId));

export const getHealthHistory = (userId: string, hours: number) =>
  api.get<HealthData[]>('/health/history', { params: { hours }, ...authHeader(userId) });

export const getRecentHealth = (userId: string, limit: number) =>
  api.get<HealthData[]>('/health/recent', { params: { limit }, ...authHeader(userId) });

// ── Diary ─────────────────────────────────────────────────────────────────────
export const getDiaryNotes = (userId: string) =>
  api.get<DiaryNote[]>('/diary-notes', authHeader(userId));

export const createDiaryNote = (userId: string, data: { title: string; content: string }) =>
  api.post<DiaryNote>('/diary-notes', data, authHeader(userId));

export const updateDiaryNote = (userId: string, id: string, data: { title: string; content: string }) =>
  api.put<DiaryNote>(`/diary-notes/${id}`, data, authHeader(userId));

export const deleteDiaryNote = (userId: string, id: string) =>
  api.delete(`/diary-notes/${id}`, authHeader(userId));

// ── Alerts ────────────────────────────────────────────────────────────────────
// READ and DELETE only — alerts are auto-generated by the AI system.
export const getAlerts = (userId: string) =>
  api.get<Alert[]>('/alerts', authHeader(userId));

export const getAlertCount = (userId: string) =>
  api.get<{ unreadCount: number }>('/alerts/count', authHeader(userId));

export const deleteAlert = (userId: string, id: string) =>
  api.delete(`/alerts/${id}`, authHeader(userId));

export default api;
```

### 6.3 File Structure

```
src/
├── main.tsx                    # React entry
├── App.tsx                     # Router + Layout wrapper
├── index.css                   # Tailwind directives
├── types/
│   └── index.ts               # All TypeScript interfaces
├── services/
│   └── api.ts                  # Axios API service layer
├── hooks/
│   ├── useAuth.ts              # Auth hook (check userId in localStorage)
│   ├── useHealthData.ts        # Health data fetching + auto-refresh
│   └── useAlerts.ts            # Alerts fetching + unread count
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx         # Desktop sidebar
│   │   ├── BottomNav.tsx       # Mobile bottom nav
│   │   └── Layout.tsx          # Wraps all pages
│   ├── ui/
│   │   ├── VitalCard.tsx       # Reusable vital sign card
│   │   ├── AlertCard.tsx       # Reusable alert card
│   │   ├── LoadingSpinner.tsx  # Loading indicator
│   │   ├── Toast.tsx           # Error/success notifications
│   │   └── EmptyState.tsx      # Empty data placeholder
│   └── charts/
│       └── HealthLineChart.tsx  # Reusable health chart
└── pages/
    ├── LoginPage.tsx           # Login + Register
    ├── DashboardPage.tsx       # Main dashboard
    ├── HistoryPage.tsx         # Health history
    ├── DiaryPage.tsx          # Diary management
    ├── ProfilePage.tsx         # User profile
    ├── DevicesPage.tsx         # Device management
    └── AlertsPage.tsx          # Alerts view
```

### 6.4 Routing

```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Protected route wrapper
const RequireAuth = ({ children }) => {
  const userId = localStorage.getItem('userId');
  if (!userId) return <Navigate to="/login" replace />;
  return children;
};

<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/register" element={<LoginPage />} />
  <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
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
```

---

## 7. IMPORTANT NOTES FOR BASE44

### 7.1 Starting the Backend
The Spring Boot backend must be running before the frontend can work. Instructions for starting:

```powershell
# Using Maven (recommended for development — hot reload)
cd C:\Documents\BTL\backend\web-dashboard
mvn spring-boot:run

# OR build and run JAR
cd C:\Documents\BTL\backend\web-dashboard
mvn package
java -jar target/web-dashboard-1.0.0-SNAPSHOT.jar
```

Backend runs on: `http://localhost:8080`
Swagger UI (API documentation): `http://localhost:8080/swagger-ui.html`

### 7.2 Prerequisites
- **Java 17** must be installed
- **MongoDB** must be running at `mongodb://localhost:27017`
- **Python IoT Ingestion module** (backend/iot-ingestion) must be running to generate health data

### 7.3 Critical Implementation Notes

1. **Start from scratch.** The existing frontend at `C:\Documents\BTL\frontend` is incomplete and should be replaced entirely.

2. **Backend is already running.** The Spring Boot backend is live at `http://localhost:8080/api`. Do NOT build a mock backend — connect directly to it.

3. **Simulated auth.** Since there is no JWT, use `localStorage.setItem('userId', response.data.id)` after login and send `X-User-Id` header on every protected request.

4. **Proxy configuration.** Set up Vite proxy to forward `/api` requests to `http://localhost:8080/api` during development:
   ```typescript
   // vite.config.ts
   server: {
     proxy: {
       '/api': 'http://localhost:8080',
     },
   }
   ```

5. **Tailwind CSS.** Use Tailwind CSS with the color palette defined in section 5. No custom CSS files needed.

6. **Mobile-first.** Design for 375px width first, then scale up for desktop (1024px+).

7. **Health data is READ-ONLY.** The Python IoT Ingestion module writes health data to MongoDB. The frontend never writes to `realtime_health_data` or `final_result` collections.

8. **Handle empty/null states.** All API responses may return empty arrays or null values. Always handle these gracefully.

9. **Health labels** (`Normal`, `Stress`, `Fever`) must be displayed with the correct status colors (green, orange, red).

10. **Auto-refresh on Dashboard and Alerts pages** to simulate real-time monitoring without WebSockets.

11. **Default user fallback.** If no `X-User-Id` header is sent, the backend falls back to `demo_user`. This is useful for testing without login.
