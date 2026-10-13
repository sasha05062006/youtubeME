@echo off
setlocal
cd /d "%~dp0"
title YouTubeME - first-time setup
echo ============================================================
echo YouTubeME - first-time setup
echo This installs free tools and offline Russian voices.
echo It may download several hundred MB and take a while.
echo No paid API key or local language-model server is required.
echo ============================================================
echo.
choice /C YN /M "Continue with installation"
if errorlevel 2 exit /b 0

echo.
echo [1/3] Installing Blender and FFmpeg...
call "%~dp0install_tools.bat"
if errorlevel 1 (
  echo.
  echo Tool installation was not completed. Read the message above,
  echo install the missing tools, then run FIRST_RUN.bat again.
  pause
  exit /b 1
)

echo.
echo [2/3] Setting up Python...
call "%~dp0setup.bat"
if errorlevel 1 (
  echo Python setup failed. Install Python 3.11 or newer and try again.
  pause
  exit /b 1
)

echo.
echo [3/3] Installing the offline Russian voices...
call "%~dp0install_russian_voice.bat"
if errorlevel 1 (
  echo Voice installation failed. Check your internet connection and rerun
  echo install_russian_voice.bat after fixing the problem.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo First-time setup finished.
echo IMPORTANT: close this window and open a new terminal so the
echo updated PATH can be detected.
echo Then double-click create_cartoon.bat to make a cartoon.
echo A separate local LLM server is NOT required for default mode.
echo ============================================================
pause
endlocal
