# bagua 开发环境初始化（Windows PowerShell）
param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "已创建虚拟环境 venv" -ForegroundColor Green
}

& .\venv\Scripts\Activate.ps1

if ($Dev) {
    pip install -r requirements-dev.txt
    pip install -e .
    Write-Host "开发环境就绪。运行: make test  或  pytest tests/ -v" -ForegroundColor Green
} else {
    pip install -r requirements.txt
    Write-Host "依赖已安装。运行: python bagua.py" -ForegroundColor Green
}