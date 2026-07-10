@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   AI-CRM-HCP - Starting Project
echo ============================================
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js first.
    pause
    exit /b 1
)

if not exist "backend\.venv\Scripts\uvicorn.exe" (
    echo [ERROR] Backend virtualenv not found.
    echo Run setup first:
    echo   cd backend
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        popd
        pause
        exit /b 1
    )
    popd
)

sc query postgresql-x64-17 | find "RUNNING" >nul
if errorlevel 1 (
    echo [WARN] PostgreSQL service may not be running.
    echo Start PostgreSQL from Services if backend fails to connect.
) else (
    echo [OK] PostgreSQL service is running.
)

echo.
echo Stopping any existing servers on ports 8001 and 5173 ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /I "PID:"') do (
  wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /I "uvicorn app.main:app" >nul && taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Starting backend on http://localhost:8001 ...
start "AI-CRM Backend" cmd /k "cd /d ""%~dp0backend"" && .\.venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8001"

timeout /t 4 /nobreak >nul 2>nul
if errorlevel 1 ping 127.0.0.1 -n 5 >nul

echo Starting frontend on http://localhost:5173 ...
start "AI-CRM Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- --host 0.0.0.0"

timeout /t 6 /nobreak >nul 2>nul
if errorlevel 1 ping 127.0.0.1 -n 7 >nul
start "" "http://localhost:5173"

echo.
echo ============================================
echo   Project started
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8001
echo   API Docs: http://localhost:8001/docs
echo ============================================
echo.
echo Two terminal windows were opened for backend and frontend.
echo Close those windows to stop the servers.
echo.
pause
