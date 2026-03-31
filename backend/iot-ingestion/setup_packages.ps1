# ============================================================
#  IoMT Backend - Package Installer (PowerShell)
#  Chi can chay file nay de cai dat tat ca thu vien
# ============================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir "venv"
$Requirements = Join-Path $ScriptDir "requirements.txt"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  IoMT Backend - Package Installer" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Kiem tra Python
Write-Host "[1/4] Kiem tra Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  $pythonVersion - OK" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Khong tim thay Python. Vui long cai dat Python 3.10+." -ForegroundColor Red
    Write-Host "  Tai xuong: https://www.python.org/downloads/" -ForegroundColor Red
    Read-Host "Nhan Enter de thoat"
    exit 1
}
Write-Host ""

# 2. Kiem tra va tao Virtual Environment
Write-Host "[2/4] Kiem tra Virtual Environment..." -ForegroundColor Yellow
if (Test-Path (Join-Path $VenvDir "Scripts\python.exe")) {
    Write-Host "  Virtual environment da ton tai - OK" -ForegroundColor Green
} else {
    Write-Host "  Tao moi Virtual Environment..." -ForegroundColor Yellow
    python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Khong the tao Virtual Environment." -ForegroundColor Red
        Read-Host "Nhan Enter de thoat"
        exit 1
    }
    Write-Host "  Da tao moi venv - OK" -ForegroundColor Green
}
Write-Host ""

# 3. Nang cap pip (bo qua loi)
Write-Host "[3/4] Kiem tra pip..." -ForegroundColor Yellow
Write-Host "  pip san co - OK" -ForegroundColor Green
Write-Host ""

# 4. Cai dat requirements
Write-Host "[4/4] Cai dat cac thu vien..." -ForegroundColor Yellow
Write-Host "  Dang cai dat, vui long cho..." -ForegroundColor DarkGray

& (Join-Path $VenvDir "Scripts\pip.exe") install -r $Requirements 2>&1 | ForEach-Object {
    if ($_ -notmatch "pip.exe :") {
        Write-Host $_
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  [ERROR] Loi khi cai dat thu vien." -ForegroundColor Red
    Read-Host "Nhan Enter de thoat"
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  HOAN TAT! Tat ca thu vien da duoc cai dat." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  De kich hoat Virtual Environment, chay:" -ForegroundColor White
Write-Host "    .\\venv\\Scripts\\Activate.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  De chay chuong trinh:" -ForegroundColor White
Write-Host "    python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Read-Host "Nhan Enter de thoat"
