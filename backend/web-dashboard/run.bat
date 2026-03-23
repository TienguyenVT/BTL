@echo off
chcp 65001 >nul
echo ========================================
echo   IoMT Dashboard - Backend Server
echo ========================================
echo.
echo DANG KHOI DONG...
echo.

cd /d "%~dp0"

set JAVA_HOME=C:\Program Files\Java\jdk-21.0.10
set PATH=%JAVA_HOME%\bin;C:\maven\apache-maven-3.9.9\bin;%PATH%

echo [1/2] Kiem tra Java...
java -version
echo.

echo [2/2] Khoi dong Spring Boot (port 8080)...
echo    Sau khi chay thanh cong, mo trinh duyet:
echo    http://localhost:8080/api/diary-notes
echo.
echo ========================================
echo.

mvn spring-boot:run

pause
