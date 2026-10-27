"""Safe browser acceptance: all mutations and model requests are intercepted.

Run with the three application services already running:
    python scripts/verify_global_assistant_ui.py --base-url http://127.0.0.1:5173
Artifacts contain fixture data and sanitized context only, never backend bodies.
"""
import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5173')
    parser.add_argument('--output', default='logs/assistant-verification')
    parser.add_argument('--only', help='Comma-separated case names for targeted reruns')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(Path('frontend/src/assistant/contract.generated.json').read_text(encoding='utf-8'))
    results, requests, blocked, errors = [], [], [], []
    fixture = {'action': None, 'handoff': False, 'unknown': False, 'confirm': 0}
    event = dict(id='ui-fixture-event', plantId='UI验收厂站', status='pending', severity='high', timestamp='2026-10-16T00:00:00Z', updatedAt='2026-10-16T00:00:00Z', violationTypes=[], evidence={}, confidence=0.8)
    operation = dict(operation_id='ui-fixture-operation', event_id=event['id'], new_status='processing', status='completed', identity='本地操作会话，身份未认证')

    def intercept(route):
        req = route.request
        path = urlparse(req.url).path
        method = req.method
        if method in ('GET', 'HEAD', 'OPTIONS') and not path.startswith('/api/'):
            return route.continue_()
        if method not in ('GET', 'HEAD', 'OPTIONS'):
            if path.endswith('/assistant/respond') and method == 'POST':
                body = req.post_data_json
                requests.append({'kind': 'respond', 'query': body['query'], 'context': body['context'], 'session_id': body['session_id']})
                prepared = {**fixture['action'], 'contract_version': contract['contract_version'], 'context': body['context'], 'parameter_sources': {key: 'explicit' for key in fixture['action']['parameters']}} if fixture['action'] else None
                value = {'message': '隔离验收回答 ' + body['query'], 'actions': [prepared] if prepared else [], 'contract_version': contract['contract_version']}
                if fixture['handoff']:
                    value['handoff'] = {'query': 'UI验收专业交接问题', 'context': body['context']}
                return route.fulfill(json=value)
            if path.endswith('/assistant/event-proposals') and method == 'POST':
                body = req.post_data_json
                requests.append({'kind': 'prepare', 'body': body})
                return route.fulfill(json=dict(proposal_id='ui-fixture-proposal', event_id=body['event_id'], plant_id=event['plantId'], old_status='pending', new_status=body['new_status'], reason=body['reason'], expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(), expected_updated_at=event['updatedAt'], identity=operation['identity']))
            if path.endswith('/assistant/event-proposals/ui-fixture-proposal/confirm') and method == 'POST':
                fixture['confirm'] += 1
                requests.append({'kind': 'confirm', 'body': req.post_data_json})
                if fixture['unknown']:
                    return route.abort('connectionfailed')
                return route.fulfill(json=operation)
            blocked.append({'method': method, 'path': path})
            return route.fulfill(status=403, json={'detail': 'Browser verification blocks all non-fixture writes and model calls'})
        if path.endswith('/assistant/capabilities'):
            return route.fulfill(json={**contract, 'event_writes_enabled': True})
        if '/assistant/operations/' in path:
            requests.append({'kind': 'query-operation', 'path': path})
            return route.fulfill(json=operation)
        if path.endswith('/v1/conversations/ui-fixture-session'):
            return route.fulfill(json={'success': True, 'data': {'id': 'ui-fixture-session', 'title': 'UI验收审计会话', 'message_count': 1, 'messages': [{'role': 'user', 'content': '只读审计夹具', 'timestamp': None}]}})
        if path.endswith('/v1/knowledge/node/ui-fixture-node'):
            return route.fulfill(json={'success': True, 'node': {'id':'ui-fixture-node', 'type':'plant', 'label':'UI验收图谱节点', 'props':{}}, 'neighbors':{}})
        if path.endswith('/events/' + event['id']):
            return route.fulfill(json=event)
        if path.endswith('/events'):
            requests.append({'kind': 'events-read', 'url': req.url})
            return route.fulfill(json={'data': [event], 'total': 1})
        if path.endswith('/logs'):
            requests.append({'kind': 'logs-read', 'url': req.url})
        return route.continue_()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080}, reduced_motion='reduce')
        context.route('**/*', intercept)
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())

        def screenshot(name):
            page.screenshot(path=str(output / (name + '.png')), full_page=True)

        def check(name, action):
            if args.only and name not in args.only.split(','):
                return
            try:
                detail = action()
                results.append({'name': name, 'passed': True, 'detail': detail})
            except Exception as error:
                results.append({'name': name, 'passed': False, 'error': str(error)[:1800]})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
            (output / 'progress.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            screenshot(re.sub(r'[^a-zA-Z0-9_-]', '_', name))

        def goto(path):
            page.goto(args.base_url + path, wait_until='domcontentloaded', timeout=60000)
            try:
                page.wait_for_load_state('networkidle', timeout=15000)
            except PlaywrightTimeout:
                # Polling/data requests can stay active; the Vue shell is the readiness boundary.
                expect(page.locator('button.fab')).to_be_attached()

        def open_panel():
            if not page.locator('#global-assistant').is_visible():
                page.locator('button.fab').click()
            expect(page.locator('#assistant-query')).to_be_visible()

        def send(query, capability=None, params=None, handoff=False):
            fixture['action'] = {'capability': capability, 'parameters': params, 'label': query} if capability else None
            fixture['handoff'] = handoff
            open_panel()
            page.locator('#assistant-query').fill(query)
            page.locator('#assistant-query').press('Enter')
            expect(page.locator('.message.assistant').last).to_contain_text('隔离验收回答 ' + query)

        def execute(query, capability, params):
            send(query, capability, params)
            page.locator('.message.assistant').last.locator('.action-card').first.click()

        try:
            for width, height in [(1366, 768), (1440, 900), (1920, 1080), (1100, 768)]:
                def viewport_case(width=width, height=height):
                    page.set_viewport_size({'width': width, 'height': height})
                    goto('/events')
                    launcher = page.locator('.fab')
                    expect(launcher).to_be_visible()
                    styles = launcher.evaluate('(el)=>{const s=getComputedStyle(el);return {background:s.backgroundImage,blur:s.backdropFilter,color:s.color,border:s.borderColor,shadow:s.boxShadow,radius:s.borderRadius}}')
                    assert 'gradient' in styles['background'] and 'blur(14px)' in styles['blur']
                    assert styles['color'] == 'rgb(30, 41, 59)' and styles['shadow'] != 'none'
                    screenshot(f'{width}x{height}-capsule')
                    open_panel()
                    panel = page.locator('#global-assistant')
                    expect(panel).to_have_css('width', '420px')
                    geometry = page.evaluate('()=>({sidebar:document.querySelector(".admin").firstElementChild.getBoundingClientRect().width,main:document.querySelector(".main").getBoundingClientRect().width,docked:document.querySelector("#global-assistant").classList.contains("docked")})')
                    assert geometry['docked'] == (width - geometry['sidebar'] - 420 >= 900), geometry
                    if geometry['docked']:
                        assert geometry['main'] >= 900
                    screenshot(f'{width}x{height}-default')
                    page.get_by_role('button', name='展开宽度', exact=True).click()
                    expect(panel).to_have_css('width', '560px')
                    screenshot(f'{width}x{height}-expanded')
                    page.get_by_role('button', name='恢复默认宽度').click()
                    page.locator('#assistant-query').press('Escape')
                    expect(launcher).to_be_focused()
                    return {'theme': styles, 'layout': geometry}
                check(f'viewport-{width}x{height}', viewport_case)

            page.set_viewport_size({'width': 1920, 'height': 1080})
            for page_id, path in [('dashboard','/dashboard'), ('metrics','/metrics'), ('events','/events'), ('audit','/agents/audit'), ('graph','/agents/knowledge'), ('logs','/logs'), ('config','/agents/config')]:
                def context_case(page_id=page_id, path=path):
                    goto(path)
                    send('context-' + page_id)
                    body = next(r for r in reversed(requests) if r['kind'] == 'respond')
                    assert body['context']['pageId'] == page_id, body
                    assert body['context']['route'] == path
                    assert not re.search(r'api_key|password|credential|raw_body', json.dumps(body['context']))
                    return body['context']
                check('context-' + page_id, context_case)

            def navigation():
                goto('/events')
                execute('navigate-logs', 'navigate', {'pageId': 'logs'})
                expect(page).to_have_url(re.compile('/logs$'))
            check('navigation', navigation)

            def events_filter():
                goto('/events')
                execute('filter-events', 'events.filter', {'status': 'processing', 'severity': 'high'})
                expect(page.locator('.message.assistant').last).to_contain_text('筛选完成')
                assert any('status=processing' in r.get('url','') and 'severity=high' in r.get('url','') for r in requests)
            check('events-filter', events_filter)

            def logs_filter():
                goto('/logs')
                execute('filter-logs', 'logs.filter', {'module': 'api'})
                expect(page.locator('.message.assistant').last.locator('.receipt')).to_be_visible()
                assert any(('api' in r.get('url','')) for r in requests if r['kind'] == 'logs-read')
            check('logs-filter', logs_filter)

            def drawer():
                goto('/events')
                execute('event-detail', 'events.detail', {'eventId': event['id']})
                expect(page.locator('.el-drawer:visible')).to_be_visible()
                expect(page.locator('#global-assistant')).to_be_hidden()
                expect(page.locator('.el-drawer:visible')).to_contain_text(event['id'])
            check('native-drawer-coordination', drawer)

            for capability, params, path, success in [('audit.focus', {'sessionId':'ui-fixture-session'}, '/agents/audit', '已加载会话 ui-fixture-session'), ('graph.focus', {'nodeId':'ui-fixture-node'}, '/agents/knowledge', '已定位节点 ui-fixture-node')]:
                def focus_target(capability=capability, params=params, path=path, success=success):
                    goto(path)
                    execute('focus-' + capability, capability, params)
                    open_panel()
                    expect(page.locator('.message.assistant').last).to_contain_text(success)
                check('fixture-' + capability, focus_target)

            for capability, params, path in [('audit.focus', {'sessionId':'ui-missing-session'}, '/agents/audit'), ('graph.focus', {'nodeId':'ui-missing-node'}, '/agents/knowledge')]:
                def missing_target(capability=capability, params=params, path=path):
                    goto(path)
                    execute('missing-' + capability, capability, params)
                    expect(page.locator('.message.assistant').last.locator('.receipt')).to_be_visible()
                    text = page.locator('.message.assistant').last.inner_text()
                    assert '已加载会话 ui-missing' not in text and '已定位节点 ui-missing' not in text
                    return text
                check('honest-' + capability, missing_target)

            def strategy():
                goto('/agents/config')
                execute('strategy-diff', 'strategy.draft', {'language_constraint': 'en'})
                expect(page.get_by_text('助手建议草稿（尚未应用或保存）')).to_be_visible()
                expect(page.locator('.sp-hint').first).to_contain_text('language_constraint')
                before = len(blocked)
                page.get_by_role('button', name='应用到编辑表单', exact=True).click()
                expect(page.get_by_text('助手建议草稿（尚未应用或保存）')).to_be_hidden()
                assert len(blocked) == before, blocked
                row = page.locator('.sp-row').filter(has=page.locator('.sp-key', has_text='language_constraint'))
                expect(row).to_contain_text('en')
            check('strategy-diff-apply-without-save', strategy)

            def handoff():
                goto('/events')
                send('handoff-test', handoff=True)
                page.get_by_role('button', name='交给主 AI 助手 · 查看交接').last.click()
                expect(page).to_have_url(re.compile('/chat$'))
                expect(page.locator('.comp input')).to_have_value(re.compile('UI验收专业交接问题'))
                assert not any('/chat' in b['path'] for b in blocked), blocked
                open_panel()
                expect(page.locator('.messages')).to_contain_text('handoff-test')
                assert page.locator('.messages').get_by_text('UI验收专业交接问题', exact=True).count() == 0
                page.get_by_role('button', name='收起助手').click()
                expect(page.locator('#global-assistant')).to_be_hidden()
                open_panel()
                expect(page.locator('.messages')).to_contain_text('handoff-test')
            check('handoff-prefill-independent-reopen', handoff)

            def prepare_event(label):
                goto('/events')
                send(label, 'event.propose', {'eventId':event['id'], 'new_status':'processing', 'reason':'隔离浏览器验收'})
                page.locator('.message.assistant').last.locator('.action-card').first.click()
                card = page.locator('.message.assistant').last.locator('.event-card')
                card.get_by_role('button', name='核验并准备确认').click()
                expect(card.get_by_role('button', name='确认修改此事件')).to_be_visible()
                expect(card).to_contain_text('pending → processing')
                return card

            def cancel_event():
                card = prepare_event('cancel-event')
                before = fixture['confirm']
                card.get_by_role('button', name='取消变更', exact=True).click()
                expect(card.get_by_role('button', name='确认修改此事件')).to_be_hidden()
                page.get_by_role('button', name='收起助手').click()
                expect(page.locator('#global-assistant')).to_be_hidden()
                open_panel()
                assert fixture['confirm'] == before
                return {'confirm_calls': before, 'behavior': 'Explicit cancellation and close/reopen do not submit'}
            check('event-prepare-close-without-submit', cancel_event)

            def confirmed_event():
                card = prepare_event('confirmed-event')
                fixture['unknown'] = False
                card.get_by_role('button', name='确认修改此事件').click()
                expect(card).to_contain_text('已核验：ui-fixture-event → processing')
                assert any(r['kind'] == 'query-operation' for r in requests)
            check('event-confirm-and-read-result', confirmed_event)

            def unknown_event():
                card = prepare_event('unknown-event')
                fixture['unknown'] = True
                card.get_by_role('button', name='确认修改此事件').click()
                expect(card).to_contain_text('结果待核验')
                before = fixture['confirm']
                page.get_by_role('button', name='收起助手').click()
                page.reload()
                page.wait_for_load_state('networkidle')
                open_panel()
                page.get_by_role('button', name='查询操作结果').last.click()
                expect(page.locator('.messages')).to_contain_text('已核验：ui-fixture-event → processing')
                assert fixture['confirm'] == before
                assert any(r['kind'] == 'query-operation' for r in requests)
            check('event-unknown-reload-query-without-repeat', unknown_event)
        finally:
            browser.close()
            report = {'passed': all(r['passed'] for r in results), 'cases':results, 'requests':requests, 'blocked_writes':blocked, 'page_errors':errors, 'fixture_confirm_calls':fixture['confirm'], 'safety':'All non-GET/HEAD/OPTIONS requests were either fulfilled by explicit fixture or blocked; no writes/model calls reached services.'}
            (output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'passed':report['passed'], 'cases':len(results), 'failed':[r['name'] for r in results if not r['passed']], 'blocked_writes':len(blocked), 'output':str(output.resolve())}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
