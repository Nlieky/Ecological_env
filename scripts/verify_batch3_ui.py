"""Read-only desktop acceptance for the third batch of UI improvements."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ['/chat', '/agents/audit', '/agents/knowledge', '/agents/config', '/dashboard', '/metrics', '/plants/config', '/events', '/logs']
EXPERIMENTAL = ['/tracing', '/datasources', '/grafana', '/alerts', '/event-sources', '/settings']
SIZES = [(1366, 768), (1440, 900), (1920, 1080)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://localhost:5173')
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'logs' / 'batch3-verification'
    output.mkdir(parents=True, exist_ok=True)
    failures, checks = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width, height in SIZES[:1] if args.quick else SIZES:
            context = browser.new_context(viewport={'width': width, 'height': height})
            page = context.new_page()
            page.on('pageerror', lambda error: failures.append({'pageerror': str(error)}))

            def guard(route):
                # Browser acceptance never submits an operation or changes configuration.
                read_only_search = route.request.method == 'POST' and route.request.url.split('?')[0].endswith('/api/observability/tracing/search')
                if route.request.method not in ('GET', 'HEAD', 'OPTIONS') and not read_only_search:
                    failures.append({'unexpected_mutation': route.request.url})
                    route.abort()
                else:
                    route.continue_()

            page.route('**/api/**', guard)
            for path in FORMAL + ['/experimental'] + EXPERIMENTAL:
                response = page.goto(args.base_url + path, wait_until='networkidle')
                expect(page.locator('.sidebar')).to_be_visible()
                if response.status != 200:
                    failures.append({'path': path, 'status': response.status})
                if path in EXPERIMENTAL:
                    expect(page.locator('.experimental-feature')).to_be_visible()
                if path == '/grafana':
                    expect(page.locator('iframe')).to_have_count(0)
                metrics = page.evaluate('''() => {
                  const content = document.querySelector('.content');
                  return {bodyWidth: document.body.scrollWidth, viewportWidth: innerWidth,
                    bodyHeight: document.documentElement.scrollHeight, viewportHeight: innerHeight,
                    outerOverflow: content.scrollHeight > content.clientHeight + 2,
                    contentHeight: content.clientHeight, scrollHeight: content.scrollHeight};
                }''')
                if metrics['bodyWidth'] > width + 2 or metrics['bodyHeight'] > height + 2:
                    failures.append({'path': path, 'size': [width, height], 'overflow': metrics})
                if path in FORMAL and metrics['outerOverflow']:
                    failures.append({'path': path, 'size': [width, height], 'double_scroll': metrics})
                checks.append({'path': path, 'size': [width, height], **metrics})
                name = path.strip('/').replace('/', '-') or 'home'
                page.screenshot(path=str(output / f'{width}-{name}.png'), full_page=True)
            # Valid trailing slash URLs must retain the experimental warning.
            page.goto(args.base_url + '/grafana/', wait_until='networkidle')
            expect(page.locator('.experimental-feature')).to_be_visible()
            expect(page.locator('iframe')).to_have_count(0)
            context.close()
        browser.close()
    result = {'checks': checks, 'failures': failures, 'screenshots': str(output)}
    (output / 'acceptance.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    assert not failures, json.dumps(failures, ensure_ascii=True)


if __name__ == '__main__':
    main()
