@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run setup.bat
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\generate.py" %*
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo Finished. Check output\ready\
) else (
  echo Generation failed. Read the error above and output\quarantine\ if a QA report exists.
)
exit /b %RC%
