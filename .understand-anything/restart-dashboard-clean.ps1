# 重启仪表板
\$env:GRAPH_DIR = "E:\project\Ecological_env"
\$env:UNDERSTAND_ACCESS_TOKEN = "test-token-12345"

Write-Host "正在启动仪表板..." -ForegroundColor Green
Write-Host "Token: test-token-12345" -ForegroundColor Yellow
Write-Host ""

cd "C:\Users\86157\.claude\plugins\marketplaces\understand-anything\understand-anything-plugin\packages\dashboard"
pnpm run dev -- --host 127.0.0.1 --port 5175
