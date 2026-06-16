# 使用固定 token 启动仪表板
$env:GRAPH_DIR = "E:\project\Ecological_env"
$env:UNDERSTAND_ACCESS_TOKEN = "my-secret-token-12345"  # 固定 token

Write-Host "正在启动仪表板..." -ForegroundColor Green
Write-Host ""
Write-Host "固定 token: my-secret-token-12345" -ForegroundColor Yellow
Write-Host "访问 URL: http://127.0.0.1:5173/?token=my-secret-token-12345" -ForegroundColor Cyan
Write-Host ""

cd "C:\Users\86157\.claude\plugins\marketplaces\understand-anything\understand-anything-plugin\packages\dashboard"
pnpm run dev -- --host 127.0.0.1 --port 5173
