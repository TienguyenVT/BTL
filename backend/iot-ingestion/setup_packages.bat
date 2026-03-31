@echo off
:: ============================================================
::  IoMT Backend - Package Installer
::  Chi can chay file nay de cai dat tat ca thu vien
:: ============================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "REQUIREMENTS=%SCRIPT_DIR%requirements.txt"

echo ============================================================
echo   IoMT Backend - Package Installer
echo ============================================================
echo.

:: 1. Kiem tra Python
echo [1/4] Kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Khong tim thay Python. Vui long cai dat Python 3.10+.
    echo   Tai xuong: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo   !PY_VER! - OK
echo.

:: 2. Kiem tra va tao Virtual Environment
echo [2/4] Kiem tra Virtual Environment...
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo   Virtual environment da ton tai - OK
) else (
    echo   Tao moi Virtual Environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo   [ERROR] Khong the tao Virtual Environment.
        pause
        exit /b 1
    )
    echo   Da tao moi venv - OK
)
echo.

:: 3. Nang cap pip
echo [3/4] Nang cap pip...
call "%VENV_DIR%\Scripts\pip.exe" install --upgrade pip --quiet
if errorlevel 1 (
    echo   [WARNING] Khong the nang cap pip, tiep tuc...
) else (
    echo   pip da duoc nang cap - OK
)
echo.

:: 4. Cai dat requirements
echo [4/4] Cai dat cac thu vien tu requirements.txt...
echo   Dang cai dat, vui long cho...
echo.

call "%VENV_DIR%\Scripts\pip.exe" install -r "%REQUIREMENTS%"
if errorlevel 1 (
    echo.
    echo   [ERROR] Loi khi cai dat thu vien.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   HOAN TAT! Tat ca thu vien da duoc cai dat.
echo ============================================================
echo.
echo   De kich hoat Virtual Environment, chay:
echo   cd "%CD%"
echo   .\\venv\\Scripts\\Activate.ps1
echo.
echo   De chay chuong trinh:
echo   python main.py
echo.
echo ============================================================
pause
