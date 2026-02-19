@echo off
REM PharmaGuard Launcher
REM Ensure Python is installed and added to PATH

echo [INFO] Starting PharmaGuard...

cd backend
if not exist venv (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    pip install pysam 2>NUL || echo [WARN] skipping pysam on Windows, using pure-Python fallback
) else (
    call venv\Scripts\activate
)

REM Check for .env file
if not exist .env (
    echo [INFO] Creating .env config from example...
    copy ..\.env.example .env >NUL
)

echo [INFO] Launching server...
echo [INFO] Open http://localhost:8000 in your browser.
start http://localhost:8000
python -m uvicorn main:app --port 8000 --reload

pause
