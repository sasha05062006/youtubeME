@echo off
setlocal
cd /d "%~dp0"
echo === YouTubeME setup ===
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" was not found. Install Python 3.11+ and enable PATH.
  exit /b 1
)
py -3.11 -m venv .venv
if errorlevel 1 py -3 -m venv .venv
if errorlevel 1 (
  echo Could not create a virtual environment.
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -c "import sys; print('Python ready:', sys.version)"
echo.
echo Setup complete. Install Blender and FFmpeg if they are not already on PATH.
echo See README.md for details.
endlocal
