# 重启仪表板以获取新的 token
Write-Host "正在停止旧的仪表板进程..." -ForegroundColor Yellow
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*vite*" } | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "正在启动仪表板..." -ForegroundColor Green
Write-Host "请在下方输出中查找包含 '🔑 Dashboard URL' 的行" -ForegroundColor Cyan
Write-Host "复制完整的 URL（包含 ?token= 参数）到浏览器中访问" -ForegroundColor Cyan
Write-Host ""

$env:GRAPH_DIR = "E:\project\Ecological_env"
$DashboardDir = "C:\Users\86157\.claude\plugins\marketplaces\understand-anything\understand-anything-plugin\packages\dashboard"

Set-Location $DashboardDir
pnpm run dev -- --host 127.0.0.1 --port 5173
