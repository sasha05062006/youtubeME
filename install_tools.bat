@echo off
setlocal
echo === Install free 3D/video tools ===
where winget >nul 2>nul
if errorlevel 1 (
  echo Windows Package Manager (winget) was not found.
  echo Install Blender and FFmpeg manually using the links in README.md.
  exit /b 1
)
echo This installs Blender and FFmpeg from the Windows package catalog.
echo It may take several minutes and download hundreds of megabytes.
set "INSTALL_FAILED=0"
winget install --id BlenderFoundation.Blender -e --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo Blender installation did not complete. Install it manually.
  set "INSTALL_FAILED=1"
)
winget install --id Gyan.FFmpeg.Shared -e --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo FFmpeg installation did not complete. Install it manually.
  set "INSTALL_FAILED=1"
)
if "%INSTALL_FAILED%"=="1" (
  echo.
  echo At least one tool could not be installed. Fix it and rerun this script.
  endlocal & exit /b 1
)
echo.
echo Tool installer finished. Close this window and open a new terminal so PATH refreshes.
endlocal & exit /b 0
