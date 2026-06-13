@echo off
REM Offline STT Pipeline - Installation Script (Windows)
REM This script installs the application and its dependencies.

echo ======================================================
echo     Offline STT Pipeline - Windows Installer
echo ======================================================
echo.

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python 3.10+ is required but not found.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%
echo.

REM Set install directory
set INSTALL_DIR=%LOCALAPPDATA%\offline-stt-pipeline
set VENV_DIR=%INSTALL_DIR%\venv

echo Installing to: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Create virtual environment
echo Creating virtual environment...
python -m venv "%VENV_DIR%"

REM Activate venv
call "%VENV_DIR%\Scripts\activate.bat"

REM Upgrade pip
echo Upgrading pip...
pip install --upgrade pip --quiet

REM Install the package
echo Installing Offline STT Pipeline...
set SCRIPT_DIR=%~dp0..
pip install -e "%SCRIPT_DIR%" --quiet

echo.
echo Installation complete!
echo.
echo To start the server:
echo   "%VENV_DIR%\Scripts\activate.bat"
echo   offline-stt
echo.
echo Or run directly:
echo   "%VENV_DIR%\Scripts\python.exe" -m src.main
echo.

REM Create a launcher batch file
set LAUNCHER=%INSTALL_DIR%\offline-stt.bat
(
echo @echo off
echo call "%VENV_DIR%\Scripts\activate.bat"
echo python -m src.main %%*
) > "%LAUNCHER%"

echo Launcher created at: %LAUNCHER%
echo.
echo Quick start:
echo   1. Run: offline-stt
echo   2. Open: http://localhost:8000
echo   3. Download a model from the UI
echo.
pause
