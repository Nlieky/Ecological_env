# Understand Anything 仪表板启动脚本
$env:GRAPH_DIR = "E:\project\Ecological_env"
$DashboardDir = "C:\Users\86157\.claude\plugins\marketplaces\understand-anything\understand-anything-plugin\packages\dashboard"

Write-Host "启动 Understand Anything 仪表板..." -ForegroundColor Green
Write-Host "项目目录: $env:GRAPH_DIR" -ForegroundColor Cyan
Write-Host ""

Set-Location $DashboardDir
pnpm run dev -- --host 127.0.0.1 --port 5173
