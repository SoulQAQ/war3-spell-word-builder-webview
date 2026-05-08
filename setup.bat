@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0"
title WC3 Skill Text Generator - Setup

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_CFG=%VENV_DIR%\pyvenv.cfg"
set "REQUIREMENTS=requirements.txt"
set "SNAPSHOT_FILE=%VENV_DIR%\.requirements.snapshot"

echo ========================================
echo   WC3 Skill Text Generator - Setup
echo ========================================
echo.

:: 1. Check Python 3.13
echo [INFO] Checking Python 3.13...
py -3.13 -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.13 not found.
    echo [HINT] Please install Python 3.13 (Python 3.14 is not supported due to pythonnet compatibility).
    echo.
    pause
    exit /b 1
)

:: 2. Create virtual environment
if not exist "%VENV_PY%" (
    echo [INFO] Creating virtual environment with Python 3.13...
    py -3.13 -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Verify virtual environment version
set "VENV_VER="
if exist "%VENV_CFG%" (
    for /f "tokens=1,* delims==" %%A in (%VENV_CFG%) do (
        set "KEY=%%A"
        set "VAL=%%B"
        set "KEY=!KEY: =!"
        if /i "!KEY!"=="version" (
            set "VENV_VER=!VAL!"
            set "VENV_VER=!VENV_VER: =!"
        )
    )
)

echo %VENV_VER% | findstr /b "3.13." >nul
if errorlevel 1 (
    echo [WARN] Virtual environment version mismatch, recreating...
    rmdir /s /q "%VENV_DIR%"
    py -3.13 -m venv "%VENV_DIR%"
)

:: 4. Upgrade pip
echo [INFO] Upgrading pip...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel >nul 2>nul

:: 5. Install dependencies
if exist "%REQUIREMENTS%" (
    echo [INFO] Installing dependencies...
    "%VENV_PY%" -m pip install -r "%REQUIREMENTS%"
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    copy /y "%REQUIREMENTS%" "%SNAPSHOT_FILE%" >nul
) else (
    echo [ERROR] requirements.txt not found.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Environment setup complete.
exit /b 0
