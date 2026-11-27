$ErrorActionPreference = 'Stop'
$backendDir = Join-Path $PSScriptRoot 'backend'
$pythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw '请先进入 backend，执行 python -m venv .venv，再用 .venv\Scripts\python.exe -m pip install -r requirements-dev.txt 安装依赖。'
}
Push-Location $backendDir
try {
    & $pythonExe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --reload
} finally { Pop-Location }
