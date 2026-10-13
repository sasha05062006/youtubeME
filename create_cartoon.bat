@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "scripts\create_cartoon.py" %*
) else (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python was not found. Run setup.bat first.
    exit /b 1
  )
  py -3 "scripts\create_cartoon.py" %*
)
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo Cartoon created. Check output\ready\
) else (
  echo Cartoon job failed. Read the error above and output\work\ logs.
)
exit /b %RC%
