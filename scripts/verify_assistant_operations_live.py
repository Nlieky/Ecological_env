"""Real model + read-only page-operation acceptance. All business writes blocked."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='logs/assistant-verification/operation-live-20261019')
    parser.add_argument('--only', help='Comma-separated case names for diagnosis')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    results, blocked, errors = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080}, reduced_motion='reduce')
        page.set_default_timeout(15000)
        # Isolate independent acceptance cases; multi-turn sends within one
        # page still share the same pending intent and conversation history.
        page.add_init_script("sessionStorage.removeItem('ecological.assistant.v1')")
        page.on('pageerror', lambda error: errors.append(str(error)))
        def safe(route):
            req = route.request
            if req.method not in ('GET', 'HEAD', 'OPTIONS') and not req.url.endswith(('/assistant/respond', '/v1/detection/run')):
                blocked.append(req.url)
                return route.abort()
            return route.continue_()
        page.route('**/api/**', safe)
        def ready():
            page.goto('http://localhost:5173/dashboard', wait_until='networkidle', timeout=60000)
            expect(page.locator('.dash-page .grid')).to_be_visible(timeout=60000)
            expect(page.locator('.dash-page .page-state')).to_have_attribute('aria-busy', 'false', timeout=60000)
            stop = page.get_by_role('button', name='⏹ 停止', exact=True)
            if stop.is_visible(): stop.click()
            page.get_by_role('button', name='AIOps 智能助手').click()
        def send(query):
            page.locator('#assistant-query').fill(query)
            with page.expect_response(lambda r: '/api/assistant/respond' in r.url, timeout=75000) as pending:
                page.locator('#assistant-query').press('Enter')
            response = pending.value
            assert response.status == 200, {'status': response.status, 'detail': response.text()[:500]}
            # An empty composer intentionally disables Send after completion.
            # Its label changes back from 解释中… when response processing ends.
            page.get_by_role('button', name='发送', exact=True).wait_for()
            return response.json()
        def execute_detect(body, side):
            assert len(body.get('actions', [])) == 1 and body['actions'][0]['capability'] == 'dashboard.detect', body
            assert body['actions'][0]['parameters']['side'] == side, body
            with page.expect_response(lambda r: '/v1/detection/run' in r.url, timeout=110000) as pending:
                page.locator('.message.assistant').last.locator('.action-card').first.click()
            response = pending.value
            payload = response.json()
            assert response.status == 200 and payload.get('success'), payload
            count = len(payload['data']['actionData']['annotations'])
            button = page.locator('.message.assistant').last.locator('.action-card').first
            expect(button).to_be_disabled(timeout=20000)
            expect(button).to_contain_text('已完成' if count else '完成', timeout=20000)
            charts = page.evaluate('''async () => { const {default:e}=await import('/src/lib/echarts.ts');
                return Array.from(document.querySelectorAll('.p-chart')).map(el=>({field:el.closest('.panel')?.getAttribute('data-indicator'),
                series:e.getInstanceByDom(el)?.getOption()?.series?.map(s=>({name:s.name,count:s.markPoint?.data?.length||0}))})); }''')
            field = body['actions'][0]['parameters']['indicator']
            chart = next(item for item in charts if item['field'] == field)
            target = '进水' if side == 'influent' else '出水'
            for series in chart['series']:
                assert series['count'] == (count if series['name'] == target else 0), chart
            return {'parameters': body['actions'][0]['parameters'], 'binding': payload['data']['execution_context'], 'annotations': count, 'chart': chart}
        def check(name, function):
            if args.only and name not in args.only.split(','): return
            try:
                detail = function()
                results.append({'name': name, 'passed': True, 'detail': detail})
            except Exception as error:
                results.append({'name': name, 'passed': False, 'error': str(error)[:1800]})
            print(json.dumps({'name': name, 'passed': results[-1]['passed'], 'error': results[-1].get('error')}, ensure_ascii=True), flush=True)
            page.screenshot(path=str(output / (name + '.png')), full_page=True)
            (output / 'results.json').write_text(json.dumps({'passed': all(r['passed'] for r in results), 'cases': results, 'blocked_writes': blocked, 'page_errors': errors}, ensure_ascii=False, indent=2), encoding='utf-8')
        def detect_query(query, side):
            ready()
            return execute_detect(send(query), side)
        def clarification():
            ready()
            first = send('请帮我标出当前厂站当前窗口的pH统计异常。')
            (output / 'clarification-first.json').write_text(json.dumps(first, ensure_ascii=False, indent=2), encoding='utf-8')
            assert first.get('pending') and not first.get('actions'), first
            second = send('进水就行，检测方案采用你提供的默认方案。')
            (output / 'clarification-second.json').write_text(json.dumps(second, ensure_ascii=False, indent=2), encoding='utf-8')
            result = execute_detect(second, 'influent')
            # The model may expand the named default into an explicit intent
            # value. Verify the declared choice and preserve actual provenance,
            # rather than falsely relabeling a model-provided field as a default.
            contract = json.loads(Path('frontend/src/assistant/contract.generated.json').read_text(encoding='utf-8'))
            descriptor = next(item for item in contract['capabilities'] if item['id'] == 'dashboard.detect')
            assert result['parameters']['algorithm'] == descriptor['defaults']['values']['algorithm'], second
            result['parameter_sources'] = second['actions'][0]['parameter_sources']
            return result
        def events():
            ready()
            body = send('打开事件中心，只显示正在处理的事件。')
            assert [a['capability'] for a in body['actions']] == ['events.filter'], body
            page.locator('.message.assistant').last.locator('.action-card').first.click()
            expect(page).to_have_url('http://localhost:5173/events')
            expect(page.locator('.el-select').filter(has_text='处理中')).to_be_visible()
        try:
            check('influent-TN-outliers', lambda: detect_query('在当前厂站当前采样窗口，对进水总氮运行离群检测，把检出的统计异常点标在图上。', 'influent'))
            check('effluent-COD-constant', lambda: detect_query('请对当前窗口的出水COD做恒值检测并在页面标注，不需要专业研判。', 'effluent'))
            check('multi-turn-default', clarification)
            check('cross-page-events-filter', events)
        finally:
            browser.close()
        return 0 if all(r['passed'] for r in results) and not blocked and not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
