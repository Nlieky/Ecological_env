"""Generic page-operation browser regression; model and business mutations use fixtures."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from datetime import datetime, timedelta
from copy import deepcopy

from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:5173')
    parser.add_argument('--output', default='logs/assistant-verification/operation-contract')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(Path('frontend/src/assistant/contract.generated.json').read_text(encoding='utf-8'))
    version = contract.get('contract_version', contract.get('version'))
    state = {'action': None, 'zero': False, 'detect_calls': 0}
    requests, blocked, cases, errors = [], [], [], []
    plant = '通用验收厂甲'
    start, end = '2026-07-01 00:00:00', '2026-07-02 00:00:00'
    indicators = {}
    for field, base in [('pH', 7), ('TN', 20), ('COD', 150)]:
        points = lambda offset: [{'time': f'2026-07-01 {hour:02d}:00:00', 'value': base + offset + hour / 100} for hour in range(24)]
        indicators[field] = {'label': field, 'unit': '', 'limit': None, 'influent': base + .23, 'effluent': base - 1 + .23,
                             'status': 'normal', 'series': {'influent': points(0), 'effluent': points(-1)}}
    dashboard = {'plant_id': plant, 'window_hours': 24, 'segment_start': start, 'segment_end': end,
                 'latest_time': end, 'influent_points': 24, 'effluent_points': 24, 'indicators': indicators,
                 'data_context': {'origin': 'real', 'mode': 'historical', 'freshness': 'historical', 'bucket': 'fixture-real',
                                  'timezone': 'Asia/Shanghai', 'latest_sample_at': end, 'warning': None}}

    def intercept(route):
        req = route.request
        path = unquote(urlparse(req.url).path)
        if not path.startswith('/api/'):
            return route.continue_()
        requests.append({'path': path, 'method': req.method})
        if path.endswith('/assistant/capabilities'):
            return route.fulfill(json={**contract, 'event_writes_enabled': False})
        if path.endswith('/assistant/respond'):
            body = req.post_data_json
            action = {**state['action'], 'contract_version': version, 'context': body['context'],
                      'parameter_sources': {key: 'explicit' for key in state['action']['parameters']}}
            return route.fulfill(json={'message': '已准备页面操作，请点击执行。', 'actions': [action], 'contract_version': version})
        if path.endswith('/v1/detection/run'):
            state['detect_calls'] += 1
            body = req.post_data_json
            field = {'NH3-N': 'AN', 'SS': 'suspended_solids'}.get(body['indicator'], body['indicator'])
            value = indicators[field]['series'][body['side']][10]['value']
            annotations = [] if state['zero'] else [{'timestamp': '2026-07-01T02:00:00Z', 'value': value, 'type': body['algorithm']}]
            return route.fulfill(json={'success': True, 'data': {'status': 'completed', 'actionData': {'annotations': annotations}, 'execution_context': body}})
        if req.method not in ('GET', 'HEAD', 'OPTIONS'):
            blocked.append(path)
            return route.abort()
        if path.endswith('/v1/plants/tree'):
            return route.fulfill(json={'success': True, 'data': {'cities': [], 'ungrouped': [{'plant_id': plant, 'status': 'historical'}]}})
        if path.endswith('/dashboard') and '/v1/plants/' in path:
            hours = int(parse_qs(urlparse(req.url).query).get('hours', ['24'])[0])
            data = deepcopy(dashboard)
            data['window_hours'] = hours
            data['segment_start'] = (datetime.fromisoformat(end) - timedelta(hours=hours)).isoformat(sep=' ')
            for indicator in data['indicators'].values():
                for side in ('influent', 'effluent'):
                    indicator['series'][side] = [point for point in indicator['series'][side] if point['time'] >= data['segment_start']]
            return route.fulfill(json={'success': True, 'data': data})
        if path.endswith('/events'):
            return route.fulfill(json={'data': [], 'total': 0})
        if path.endswith('/logs'):
            return route.fulfill(json={'success': True, 'data': [], 'total': 0})
        return route.continue_()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080}, reduced_motion='reduce')
        page.set_default_timeout(15000)
        page.route('**/*', intercept)
        page.on('pageerror', lambda error: errors.append(str(error)))

        def open_panel():
            if not page.locator('#global-assistant').is_visible():
                page.get_by_role('button', name='AIOps 智能助手').click()

        def send(capability, parameters):
            state['action'] = {'capability': capability, 'parameters': parameters}
            open_panel()
            page.locator('#assistant-query').fill('通用操作回归')
            with page.expect_response(lambda r: '/api/assistant/respond' in r.url):
                page.locator('#assistant-query').press('Enter')
            button = page.locator('.message.assistant').last.locator('.action-card').first
            expect(button).to_be_enabled()
            return button

        def check(name, action):
            try:
                detail = action()
                cases.append({'name': name, 'passed': True, 'detail': detail})
            except Exception as error:
                cases.append({'name': name, 'passed': False, 'error': str(error)[:1400]})
            print(json.dumps(cases[-1], ensure_ascii=False), flush=True)
            page.screenshot(path=str(output / (name + '.png')), full_page=True)
            (output / 'progress.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')

        def dashboard_ready():
            page.goto(args.base_url + '/dashboard', wait_until='networkidle')
            expect(page.locator('.dash-page .grid')).to_be_visible()
            expect(page.locator('.dash-page .page-state')).to_have_attribute('aria-busy', 'false')
            stop = page.get_by_role('button', name='⏹ 停止', exact=True)
            if stop.is_visible():
                stop.click()

        def navigation():
            dashboard_ready()
            send('navigate', {'pageId': 'events'}).click()
            expect(page).to_have_url(args.base_url + '/events')

        def filter_events():
            dashboard_ready()
            send('events.filter', {'status': 'processing'}).click()
            expect(page).to_have_url(args.base_url + '/events')
            expect(page.locator('.el-select').filter(has_text='处理中')).to_be_visible()

        def metrics_filter():
            dashboard_ready()
            send('metrics.filter', {'plant': plant, 'indicator': 'TN', 'range': '6h'}).click()
            expect(page).to_have_url(args.base_url + '/metrics')
            expect(page.locator('#metrics-plant')).to_have_value(plant)
            expect(page.locator('.metrics .chip.on').filter(has_text='TN')).to_be_visible()
            expect(page.locator('.metrics .chip.sm.on')).to_have_text('6H')
            expect(page.locator('.message.assistant').last.locator('.receipt')).to_contain_text('已加载')

        def dashboard_range():
            dashboard_ready()
            send('dashboard.range', {'range': '6h'}).click()
            expect(page.locator('.quality-card')).to_contain_text('6h')
            expect(page.locator('.message.assistant').last.locator('.receipt')).to_contain_text('6h')

        def detect(field, side, zero=False):
            dashboard_ready()
            state['zero'] = zero
            before = state['detect_calls']
            button = send('dashboard.detect', {'algorithm': 'iforest', 'indicator': field, 'side': side})
            button.click()
            open_panel()
            message = page.locator('.message.assistant').last
            expect(message).to_contain_text('0' if zero else '1')
            expect(button).to_be_disabled()
            assert state['detect_calls'] == before + 1
            charts = page.evaluate('''async () => {
                const {default: echarts} = await import('/src/lib/echarts.ts');
                return Array.from(document.querySelectorAll('.p-chart')).map(el => {
                    const option = echarts.getInstanceByDom(el)?.getOption();
                    return {field:el.closest('.panel')?.querySelector('.p-name')?.textContent,
                        series:option?.series?.map(s=>({name:s.name, points:s.markPoint?.data || []}))};
                });
            }''')
            chart = next(item for item in charts if item['field'].strip().startswith(field))
            expected_side = '进水' if side == 'influent' else '出水'
            for series in chart['series']:
                assert len(series['points']) == (0 if zero or series['name'] != expected_side else 1), chart
            return chart

        try:
            check('navigation', navigation)
            check('cross-page-events-filter', filter_events)
            check('cross-page-metrics-filter', metrics_filter)
            check('actual-dashboard-range', dashboard_range)
            check('influent-TN-marks', lambda: detect('TN', 'influent'))
            check('effluent-COD-marks', lambda: detect('COD', 'effluent'))
            check('empty-pH-result', lambda: detect('pH', 'influent', True))
        finally:
            browser.close()
            report = {'passed': all(case['passed'] for case in cases) and not errors and not blocked, 'cases': cases,
                      'page_errors': errors, 'blocked_writes': blocked, 'requests': requests,
                      'safety': 'All model/detection POSTs fulfilled by fixtures; other writes blocked.'}
            (output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
