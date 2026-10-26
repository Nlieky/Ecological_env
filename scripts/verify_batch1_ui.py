"""Browser acceptance against live services or current code (--in-process).

In-process mode intercepts GET requests and calls the actual FastAPI app, using
the configured InfluxDB/database. Fault injection stays in this browser only.
"""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in-process', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'logs/batch1-verification'
    output.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    client = None
    if args.in_process:
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1600, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        if client:
            def current_api(route):
                url = urlsplit(route.request.url)
                assert route.request.method == 'GET', 'UI verification must not mutate data'
                response = client.get(url.path + ('?' + url.query if url.query else ''))
                route.fulfill(status=response.status_code, content_type='application/json', body=response.content)
            # Do not intercept Vite's /src/api/*.ts module requests.
            page.route('**/api/v1/**', current_api)
        page.goto('http://localhost:5173/metrics', wait_until='networkidle')
        expect(page.locator('.metrics')).to_contain_text('真实数据 · 历史数据')
        expect(page.locator('.metrics')).to_contain_text('monitoring-real')
        page.locator('input[type=date]').nth(0).fill('2026-07-14')
        page.locator('input[type=date]').nth(1).fill('2026-07-15')
        expect(page.locator('.metrics')).to_contain_text('2026-07-16 00:00')
        expect(page.locator('.stats')).to_be_visible()
        page.wait_for_timeout(1500)  # Allow ECharts' initial animation to settle.
        page.screenshot(path=str(output / 'metrics-real-history.png'), full_page=True)
        checks.append('metrics real/history + inclusive dates')
        page.locator('#metrics-plant').select_option(label='洗舱站污水排放口')
        expect(page.locator('.stats .stat').nth(0)).to_contain_text('—')
        expect(page.locator('.stats .stat').nth(1)).not_to_contain_text('—')
        checks.append('effluent-only plant shows missing influent, not zero')
        dashboard_pattern = '**/api/v1/plants/*/dashboard*'
        page.route(dashboard_pattern, lambda route: route.fulfill(status=500, content_type='application/json', body='{"detail":"verification offline"}'))
        page.get_by_role('button', name='1H', exact=True).click()
        expect(page.locator('.chart-wrap')).to_contain_text('Request failed')
        expect(page.locator('.chart-wrap')).not_to_contain_text('该时间窗口无数据')
        page.unroute(dashboard_pattern)
        page.get_by_role('button', name='24H', exact=True).click()
        expect(page.locator('.stats')).to_be_visible()
        checks.append('metric request failure distinct from empty; retry recovers')
        page.goto('http://localhost:5173/dashboard', wait_until='networkidle')
        expect(page.locator('body')).to_contain_text('历史数据')
        page.get_by_role('button', name='全部', exact=True).click()
        page.wait_for_load_state('networkidle')
        expect(page.locator('body')).not_to_contain_text('请求失败')
        expect(page.locator('.ptree .time').first).to_have_text('07-25 14:00')
        page.screenshot(path=str(output / 'dashboard-real-history.png'), full_page=True)
        checks.append('dashboard history context and all-hours query')
        page.goto('http://localhost:5173/agents/audit', wait_until='networkidle')
        expect(page.locator('.list .item').first).to_be_visible()
        expect(page.locator('.detail .msgs')).to_be_visible()
        expect(page.locator('.trace-cards')).to_contain_text('最近一轮')
        page.screenshot(path=str(output / 'audit-trace.png'), full_page=True)
        checks.append('audit conversation and latest-turn/session trace scope')
        page.route('**/api/v1/conversations?*', lambda route: route.fulfill(status=500, content_type='application/json', body='{}'))
        page.reload(wait_until='networkidle')
        expect(page.locator('.list')).to_contain_text('会话列表加载失败')
        expect(page.locator('.list')).not_to_contain_text('暂无会话记录')
        page.unroute('**/api/v1/conversations?*')
        page.get_by_role('button', name='重试', exact=True).click()
        expect(page.locator('.detail .msgs')).to_be_visible()
        checks.append('audit list failure is not empty; retry recovers')
        assert not errors, errors
        browser.close()
    if client:
        client.close()
    print(json.dumps({'mode': 'current-code-in-process' if args.in_process else 'running-services', 'checks': checks,
                      'page_errors': errors, 'screenshots': str(output)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
