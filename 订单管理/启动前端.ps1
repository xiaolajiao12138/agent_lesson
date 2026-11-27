$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot 'frontend')
try {
    if (-not (Test-Path -LiteralPath 'node_modules')) {
        & npm.cmd install
        if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败' }
    }
    & npm.cmd run dev
} finally { Pop-Location }
