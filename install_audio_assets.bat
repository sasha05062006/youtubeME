@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or newer first.
  exit /b 1
)
py -3 scripts\install_audio_assets.py %*
if errorlevel 1 (
  echo Some audio assets could not be installed. Check the messages above and try again.
  exit /b 1
)
echo Audio asset installation finished.
endlocal
