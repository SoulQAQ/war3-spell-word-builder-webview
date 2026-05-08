@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0"
title WC3 Skill Text Generator - Build

set "VENV_PY=.venv\Scripts\python.exe"
set "MAIN_SCRIPT=script\gui.py"
set "APP_NAME=WC3 Skill Text Generator"

echo ========================================
echo   WC3 Skill Text Generator - Build
echo ========================================
echo.

:: 1. Run setup to ensure environment is ready
echo [INFO] Checking environment...
call setup.bat
if errorlevel 1 (
    echo [ERROR] Setup failed.
    pause
    exit /b 1
)

:: 2. Install PyInstaller
echo [INFO] Installing PyInstaller...
"%VENV_PY%" -m pip install pyinstaller >nul 2>nul

:: 3. Clean old files
if exist "build" (
    echo [INFO] Cleaning build directory...
    rmdir /s /q "build"
)
if exist "dist" (
    echo [INFO] Cleaning dist directory...
    rmdir /s /q "dist"
)

:: 4. Build
echo [INFO] Building executable...
"%VENV_PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "WC3 Skill Text Generator" ^
  --add-data "webui;webui" ^
  --add-data "config;config" ^
  --add-data "app.ico;." ^
  --icon "app.ico" ^
  "%MAIN_SCRIPT%"

if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Build complete: dist\WC3 Skill Text Generator.exe
pause
