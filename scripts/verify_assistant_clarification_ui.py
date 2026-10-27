"""Real-browser clarification flow; only read-only metric display may be executed."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from verify_assistant_intent_clarification import PLANT, check_response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--observe', action='store_true', help='Record all clarification turns without executing candidates, even when a routing assertion fails')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    records, blocked, errors, failures = [], [], [], []
    result = {'passed': False}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.add_init_script("sessionStorage.removeItem('ecological.assistant.v1')")
        page.on('pageerror', lambda error: errors.append(str(error)))

        def safe(route):
            if route.request.method not in ('GET', 'HEAD', 'OPTIONS') and not route.request.url.endswith('/assistant/respond'):
                blocked.append(route.request.url)
                return route.abort()
            return route.continue_()

        page.route('**/api/**', safe)
        try:
            page.goto('http://localhost:5173/events', wait_until='networkidle')
            page.get_by_role('button', name='AIOps 智能助手').click()
            for query, expected in [
                ('查看当前厂站最近6小时的总氮数据', 'clarify'),
                ('在指标查询里展示，不需要AI分析。', 'clarify'),
                (f'厂站是{PLANT}。', ('metrics.filter', {'plant': PLANT, 'indicator': 'TN', 'range': '6h'})),
            ]:
                page.locator('#assistant-query').fill(query)
                with page.expect_response(lambda r: '/api/assistant/respond' in r.url, timeout=80000) as pending:
                    page.locator('#assistant-query').press('Enter')
                response = pending.value
                body = response.json()
                records.append({'query': query, 'status': response.status, 'request': response.request.post_data_json, 'response': body})
                assert response.status == 200, body
                if args.observe:
                    try:
                        check_response(body, expected)
                    except AssertionError:
                        failures.append({'turn': len(records), 'expected': expected})
                else:
                    check_response(body, expected)
                page.get_by_role('button', name='发送', exact=True).wait_for()
                expect(page).to_have_url('http://localhost:5173/events')
                if expected == 'clarify' and not args.observe:
                    expect(page.locator('.message.assistant').last.locator('.action-card')).to_have_count(0)
            if args.observe:
                assert not failures, failures
                result = {'passed': True, 'observed_only': True}
                return finish_observation(output, page, result, records, blocked, errors)
            page.locator('.message.assistant').last.locator('.action-card').first.click()
            expect(page).to_have_url('http://localhost:5173/metrics')
            expect(page.locator('#metrics-plant')).to_have_value(PLANT)
            expect(page.locator('.metrics .chip.on').filter(has_text='TN')).to_be_visible()
            expect(page.locator('.metrics .chip.sm.on')).to_have_text('6H')
            expect(page.locator('.message.assistant').last.locator('.receipt')).to_contain_text('已加载', timeout=30000)
            assert not blocked and not errors, {'blocked': blocked, 'errors': errors}
            result = {'passed': True, 'target': '/metrics', 'indicator': 'TN', 'range': '6h', 'plant': PLANT}
        except Exception as error:
            result['error'] = str(error)[:3000]
        finally:
            page.screenshot(path=str(output / 'result.png'), full_page=True)
            browser.close()
    result.update(turns=records, blocked_writes=blocked, page_errors=errors, assertion_failures=failures)
    (output / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'error': result.get('error')}, ensure_ascii=True))
    return 0 if result['passed'] else 1


def finish_observation(output, page, result, records, blocked, errors):
    result.update(turns=records, blocked_writes=blocked, page_errors=errors)
    (output / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'observed_only': True}))
    return 0 if not blocked and not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
