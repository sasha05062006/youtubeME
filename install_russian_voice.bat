@echo off
setlocal
cd /d "%~dp0"
echo === YouTubeME Russian offline voice installer ===
where curl.exe >nul 2>nul
if errorlevel 1 (
  echo curl.exe is required. It is included with current Windows 10/11.
  exit /b 1
)
if not exist "tools\piper" mkdir "tools\piper"
if not exist "models" mkdir "models"
echo Downloading Piper for Windows (free, local speech engine)...
curl.exe -fL --retry 2 "https://github.com/rhasspy/piper/releases/latest/download/piper_windows_amd64.zip" -o "tools\piper\piper.zip"
if errorlevel 1 (
  echo Piper download failed. Download a compatible Windows Piper release manually and extract piper.exe to tools\piper\
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath 'tools\piper\piper.zip' -DestinationPath 'tools\piper\extract' -Force"
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$exe = Get-ChildItem 'tools\piper\extract' -Filter piper.exe -Recurse | Select-Object -First 1; if (-not $exe) { exit 1 }; Copy-Item (Join-Path $exe.DirectoryName '*') 'tools\piper' -Recurse -Force"
if not exist "tools\piper\piper.exe" (
  echo Could not find piper.exe in the downloaded archive.
  exit /b 1
)
echo Downloading Russian Irina voice model...
curl.exe -fL --retry 2 "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx?download=true" -o "models\ru_RU-irina-medium.onnx"
if errorlevel 1 exit /b 1
curl.exe -fL --retry 2 "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx.json?download=true" -o "models\ru_RU-irina-medium.onnx.json"
if errorlevel 1 exit /b 1
echo Downloading Russian Ruslan voice model...
curl.exe -fL --retry 2 "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx?download=true" -o "models\ru_RU-ruslan-medium.onnx"
if errorlevel 1 exit /b 1
curl.exe -fL --retry 2 "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx.json?download=true" -o "models\ru_RU-ruslan-medium.onnx.json"
if errorlevel 1 exit /b 1
del "tools\piper\piper.zip" >nul 2>nul
echo.
echo Voice setup finished. The voices run locally and do not require paid APIs.
echo Voice/model licenses belong to their respective authors; review them before publishing.
echo Run run.bat and select Irina or Ruslan.
endlocal
