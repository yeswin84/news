@echo off
cd /d "%~dp0"

set OLD_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  set OLD_PID=%%a
  goto :found_old_server
)

:found_old_server
if defined OLD_PID (
  echo Found an existing server on port 8000. Restarting it...
  taskkill /PID %OLD_PID% /F >nul 2>&1
  timeout /t 1 >nul
)

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example
    echo Put your real OPENAI_API_KEY into .env if you want automatic transcription.
    echo.
  )
)

if "%LESSON_JOURNAL_HOST%"=="" (
  set LESSON_JOURNAL_HOST=0.0.0.0
)

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"

echo Starting Lesson Journal App...
echo If the browser opens but the page is blank, wait 2-3 seconds and refresh once.
echo This server is also opened for devices on the same Wi-Fi.
echo.
python run.py

if errorlevel 1 (
  echo.
  echo The app stopped because of an error.
  pause
  exit /b %errorlevel%
)

echo.
echo Server stopped.
pause
