@echo off
REM NAMLink PBPK mAb Tutorial - HTTP MCP Server launcher (Windows)
REM
REM Double-click this file or run it from any terminal.
REM The server starts on http://localhost:8000 and the browser opens automatically.
REM Press Ctrl+C in this window to stop.

setlocal

REM Resolve repo root (one level above this script's directory)
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
for %%i in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fi"

set "PBPK_REPO_PATH=%REPO_ROOT%"
set "PORT=8000"
set "HOST=127.0.0.1"

echo.
echo  NAMLink PBPK mAb Tutorial -- HTTP MCP Server
echo  =============================================
echo  Repository : %REPO_ROOT%
echo.
echo  Starting server...
echo.

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found on PATH.
    echo  Install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check dependencies
python -c "import fastmcp, fastapi, uvicorn, httpx2, mcp_types" >nul 2>&1
if errorlevel 1 (
    echo  Installing server dependencies...
    echo.
    python -m pip install -r "%SCRIPT_DIR%requirements_http.txt"
    if errorlevel 1 (
        echo.
        echo  ERROR: pip install failed. Run manually:
        echo    python -m pip install -r mcp\requirements_http.txt
        pause
        exit /b 1
    )
)

echo  Swagger UI  : http://localhost:%PORT%/docs
echo  MCP endpoint: http://localhost:%PORT%/mcp
echo.

REM Open the browser once the server answers (up to 30 s)
start "" /b powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){try{Invoke-WebRequest -UseBasicParsing http://127.0.0.1:%PORT%/openapi.json | Out-Null; Start-Process http://localhost:%PORT%/docs; break}catch{Start-Sleep -Milliseconds 500}}"

REM Start server (blocks until Ctrl+C)
python "%SCRIPT_DIR%server_http.py"

endlocal
