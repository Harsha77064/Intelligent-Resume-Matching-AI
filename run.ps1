# One-command run: builds the React app and serves everything from FastAPI.
#   .\run.ps1             -> http://localhost:8000
#   .\run.ps1 -Port 8001  -> http://localhost:8001 (if 8000 is busy)
param([int]$Port = 8000)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if (-not (Test-Path "$root\backend\.venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv "$root\backend\.venv"
    & "$root\backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & "$root\backend\.venv\Scripts\python.exe" -m pip install -r "$root\backend\requirements.txt" -r "$root\backend\requirements-embeddings.txt"
}
if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Installing frontend packages..."
    npm --prefix "$root\frontend" install
}
Write-Host "Building frontend..."
npm --prefix "$root\frontend" run build

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Port $Port is already used by another program. Try: .\run.ps1 -Port $($Port + 1)" -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "Starting MatchPoint..." -ForegroundColor Green
Write-Host "  Candidates: http://localhost:$Port/login"
Write-Host "  HR:         http://localhost:$Port/hr/login"
Write-Host "  Wait for 'Application startup complete', then open a link. Press Ctrl+C to stop."
& "$root\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --port $Port --app-dir "$root\backend"
