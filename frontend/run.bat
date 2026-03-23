@echo off
chcp 65001 >nul
echo ========================================
echo   IoMT Dashboard - Frontend (Vite)
echo ========================================
echo.
echo DANG KHOI DONG...
echo.

cd /d "%~dp0"

echo [1/2] Kiem tra Node...
node --version
npm --version
echo.

echo [2/2] Khoi dong Vite dev server (port 5173)...
echo    Sau khi chay thanh cong, mo trinh duyet:
echo    http://localhost:5173/diary
echo.
echo ========================================
echo.

npm run dev

pause
