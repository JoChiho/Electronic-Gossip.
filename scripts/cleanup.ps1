# bagua 项目目录清理脚本
# 用法：关闭 Cursor 后，在项目根目录执行  .\scripts\cleanup.ps1

$ErrorActionPreference = "Continue"
$Root = Split-Path $PSScriptRoot -Parent

Write-Host "清理目录: $Root" -ForegroundColor Cyan

# 1. 删除 Grok 会话产生的嵌套副本（如 2026-06-24-796199f3）
Get-ChildItem $Root -Directory -Force | Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}-' } | ForEach-Object {
    Write-Host "删除嵌套副本: $($_.Name)" -ForegroundColor Yellow
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $_.FullName) {
        Write-Host "  未能删除（目录被占用，请关闭 IDE 后重试）" -ForegroundColor Red
    } else {
        Write-Host "  已删除" -ForegroundColor Green
    }
}

# 2. 删除其他重复/无用目录
$RemoveDirs = @('mcps', 'terminals', 'bagua-2', '__pycache__', '.pytest_cache', 'dist', 'build')
foreach ($name in $RemoveDirs) {
    $path = Join-Path $Root $name
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "已删除: $name" -ForegroundColor Green
    }
}

# 3. 删除 egg-info 与递归 pycache（排除 venv）
Get-ChildItem $Root -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\venv\\' } |
    Where-Object { $_.Name -eq '__pycache__' -or $_.Name -like '*.egg-info' -or $_.Extension -eq '.pyc' } |
    ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "已删除: $($_.FullName.Replace($Root, '.'))" -ForegroundColor DarkGray
    }

# 4. 再次扫描残留
Write-Host "`n--- 扫描结果 ---" -ForegroundColor Cyan
$remaining = @()
Get-ChildItem $Root -Directory -Force | Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}-' } | ForEach-Object { $remaining += $_.Name }
@('mcps', 'bagua-2', '__pycache__', '.pytest_cache') | ForEach-Object {
    if (Test-Path (Join-Path $Root $_)) { $remaining += $_ }
}

if ($remaining.Count -eq 0) {
    Write-Host "清理完成，无已知冗余目录。" -ForegroundColor Green
} else {
    Write-Host "以下项目仍存在，请关闭占用进程后重试：" -ForegroundColor Yellow
    $remaining | ForEach-Object { Write-Host "  - $_" }
}

Write-Host "`n保留目录（正常）：bagua/ tests/ docs/ scripts/ venv/ .github/" -ForegroundColor DarkGray