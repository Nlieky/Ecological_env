"""Batch 2 browser acceptance; mutations are intercepted fixtures, never live writes."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in-process', action='store_true', help='Read GETs through current backend code')
    args = parser.parse_args()
    checks, errors = [], []
    output = ROOT / 'logs/batch2-verification'
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1600, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        client = None
        if args.in_process:
            from fastapi.testclient import TestClient
            from backend.main import app
            client = TestClient(app)
            def current_api(route):
                assert route.request.method == 'GET', 'Only fixture routes may accept mutations'
                url = urlsplit(route.request.url)
                response = client.get(url.path + ('?' + url.query if url.query else ''))
                route.fulfill(status=response.status_code, content_type='application/json', body=response.content)
            # Vite also serves /src/api/*.ts; match actual API prefixes only.
            page.route('**/api/v1/**', current_api)
            page.route('**/api/events**', current_api)
            page.route('**/api/logs**', current_api)
        page.goto('http://localhost:5173/chat', wait_until='networkidle')
        page.route('**/api/query/stream', lambda route: route.fulfill(
            status=200, content_type='text/event-stream',
            body='data: {"type":"delta","text":"部分回答：测试数据，非业务结论"}\n\n'))
        page.locator('input').last.fill('浏览器断流验收，不调用真实模型')
        page.locator('.comp input').press('Enter')
        expect(page.locator('.msg.assistant').last).to_contain_text('部分回答：测试数据，非业务结论')
        expect(page.locator('.msg.assistant').last).to_contain_text('未收到完成事件')
        expect(page.locator('.comp input')).to_be_enabled()
        page.screenshot(path=str(output / 'chat-interrupted.png'), full_page=True)
        checks.append('stream EOF releases waiting state and retains partial answer with error')
        page.unroute('**/api/query/stream')
        page.route('**/api/query/stream', lambda route: route.fulfill(
            status=200, content_type='text/event-stream', body=(
                'data: {"type":"progress","subagent":"anomaly-detection","stage":"start"}\r\n\r\n'
                'data: {"type":"progress","subagent":"anomaly-detection","stage":"done","elapsed_ms":1234}\r\n\r\n'
                'data: {"type":"done","content":"浏览器流式恢复成功（测试夹具）","session_id":"browser-fixture","queue_elapsed_ms":100,"turn_elapsed_ms":2000}\r\n\r\n')))
        page.locator('input').last.fill('浏览器恢复验收，不调用真实模型')
        page.locator('.comp input').press('Enter')
        expect(page.locator('.msg.assistant').last).to_contain_text('浏览器流式恢复成功')
        expect(page.locator('.msg.assistant').last).to_contain_text('耗时')
        expect(page.locator('.comp input')).to_be_enabled()
        checks.append('CRLF completed response recovers and exposes measured timing')
        pending_create = []
        page.route('**/api/v1/conversations', lambda route: (
            pending_create.append(route) if route.request.method == 'POST' else route.continue_()))
        page.get_by_role('button', name='+ 新对话', exact=True).click()
        expect(page.locator('.comp input')).to_be_disabled()
        assert len(pending_create) == 1
        pending_create[0].fulfill(status=200, content_type='application/json',
                                 body='{"success":true,"data":{"id":"browser-new-fixture"}}')
        expect(page.locator('.comp input')).to_be_enabled()
        checks.append('pending conversation creation prevents sending; success unlocks input')
        page.unroute('**/api/v1/conversations')
        page.goto('http://localhost:5173/agents/audit', wait_until='networkidle')
        expect(page.locator('.list .item').first).to_be_visible()
        page.locator('.list .item').first.click()
        expect(page.locator('.d-meta')).to_be_visible()
        session_id = page.locator('.d-meta').inner_text().split(' · ')[-1]
        page.goto('http://localhost:5173/agents/audit?session=' + session_id, wait_until='networkidle')
        expect(page.locator('.d-meta')).to_contain_text(session_id)
        page.get_by_label('搜索标题或会话ID').fill('__batch2_nonexistent_%_')
        page.locator('.list-search button[type=submit]').click()
        expect(page.locator('.list-cnt')).to_have_text('0 条')
        expect(page.locator('.selection-note')).to_contain_text('不在本页列表')
        expect(page.locator('.d-meta')).to_contain_text(session_id)
        page.get_by_label('搜索标题或会话ID').fill(session_id)
        page.locator('.list-search button[type=submit]').click()
        expect(page.locator('.list-cnt')).to_have_text('1 条')
        expect(page.locator('.list-pager')).to_contain_text('1 / 1')
        page.locator('.list-search button[type=button]').click()
        expect(page.locator('.list .item').first).to_be_visible()
        page.screenshot(path=str(output / 'audit-retrieval.png'), full_page=True)
        checks.append('audit search/clear, page reset and deep-link preserve detail outside search results')
        event_requests = []
        event_list_failure = False
        def event_fixture(route):
            event_requests.append((route.request.method, route.request.url))
            if route.request.method == 'PUT':
                route.fulfill(status=400, content_type='application/json', body='{"detail":"fixture rejected status"}')
            elif event_list_failure:
                route.fulfill(status=500, content_type='application/json', body='{"detail":"fixture list failed"}')
            else:
                route.fulfill(status=200, content_type='application/json', body=json.dumps({'data': [{
                    'id': 'browser-event-fixture', 'timestamp': '2026-07-14T08:00:00',
                    'plantId': '测试厂区', 'severity': 'high', 'status': 'pending',
                    'violationTypes': ['浏览器验收夹具'], 'evidence': []}], 'total': 21}))
        page.route('**/api/events**', event_fixture)
        def relation_fixture(route):
            route.fulfill(status=500, content_type='application/json', body='{"detail":"fixture relation failed"}')
        page.route('**/api/v1/knowledge/node/case%3Abrowser-event-fixture', relation_fixture)
        page.goto('http://localhost:5173/events', wait_until='networkidle')
        expect(page.locator('.el-pagination')).to_contain_text('21')
        page.locator('.el-pagination .btn-next').click()
        expect(page.locator('.el-pager li.is-active')).to_have_text('2')
        assert any('page=2' in url for method, url in event_requests if method == 'GET')
        page.locator('.evc .el-table__body-wrapper tr').first.click()
        expect(page.locator('.el-drawer')).to_be_visible()
        expect(page.locator('.el-drawer')).to_contain_text('关联链路加载失败')
        page.locator('.d-status .el-select').click()
        page.locator('.el-select-dropdown__item:visible').filter(has_text='已解决').click()
        expect(page.locator('.d-status')).to_contain_text('状态更新失败')
        expect(page.locator('.d-status .el-select__placeholder')).to_contain_text('待处理')
        expect(page.locator('.evc .el-table__body-wrapper tr').first).to_contain_text('待处理')
        page.screenshot(path=str(output / 'events-rejected-save.png'), full_page=True)
        checks.append('event pagination, rejected status preserves confirmed value, relation failure is independent')
        page.unroute('**/api/v1/knowledge/node/case%3Abrowser-event-fixture')
        page.route('**/api/v1/knowledge/node/case%3Abrowser-event-fixture', lambda route: route.fulfill(
            status=404, content_type='application/json', body='{"detail":"not found"}'))
        page.locator('.el-drawer').get_by_role('button', name='重试', exact=True).click()
        expect(page.locator('.el-drawer')).to_contain_text('该事件无图谱关联')
        checks.append('event relation 404 is no relation, unlike transport failure')
        event_list_failure = True
        page.goto('http://localhost:5173/events', wait_until='networkidle')
        expect(page.locator('.evc [role=alert]')).to_contain_text('事件列表加载失败')
        expect(page.get_by_text('无匹配事件', exact=True)).to_have_count(0)
        event_list_failure = False
        page.locator('.evc [role=alert]').get_by_role('button', name='重试', exact=True).click()
        expect(page.locator('.evc .el-table__body-wrapper tr').first).to_contain_text('浏览器验收夹具')
        checks.append('event list failure is not empty and retry recovers')
        page.goto('http://localhost:5173/agents/config?entity=master&tab=strategy', wait_until='networkidle')
        expect(page.locator('.sp')).to_contain_text('保存的配置不等于正在运行的配置')
        expect(page.locator('.sp')).to_contain_text('下一次适用读取')
        expect(page.locator('.sp')).to_contain_text('下一次新子智能体')
        dialogs = []
        def dismiss_unsaved(dialog):
            dialogs.append(dialog.message)
            dialog.dismiss()
        page.on('dialog', dismiss_unsaved)
        row = page.locator('.sp-row').filter(has=page.locator('.sp-key', has_text='action_shortcircuit_timeout'))
        field = row.locator('input')
        previous = field.input_value()
        field.fill(str(int(previous) + 1))
        field.press('Tab')
        page.locator('.nav-e').filter(has_text='服务管理').click()
        expect(page.locator('.sp')).to_be_visible()
        assert dialogs and '未保存' in dialogs[-1]
        field.fill(previous)
        field.press('Tab')
        page.remove_listener('dialog', dismiss_unsaved)
        service_ready = False
        service_read_failure = False
        def service_status_fixture(route):
            if service_read_failure:
                route.fulfill(status=500, content_type='application/json', body='{"detail":"fixture status read failed"}')
            else:
                route.fulfill(status=200, content_type='application/json', body=json.dumps({'success': True, 'data': {
                    'alive': True, 'ready': service_ready, 'port': 8642, 'pids': [], 'saved_model': 'fixture-model'}}))
        page.route('**/api/v1/agents/config/service/status', service_status_fixture)
        page.route('**/api/v1/agents/config/service/restart', lambda route: route.fulfill(
            status=200, content_type='application/json', body='{"ok":false,"new_alive":true,"new_ready":false,"warn":"fixture not initialized"}'))
        page.locator('.nav-e').filter(has_text='服务管理').click()
        expect(page.locator('.sc')).to_contain_text('可连接，尚未就绪')
        expect(page.locator('.sc')).to_contain_text('已保存兜底模型')
        expect(page.locator('.sc')).to_contain_text('未验证运行中供应商实际加载的模型')
        page.locator('.sc').get_by_role('button', name='一键重启', exact=True).click()
        page.locator('.el-message-box').get_by_role('button', name='确定', exact=True).click()
        expect(page.locator('.sc-res.bad')).to_contain_text('尚未就绪')
        expect(page.locator('.sc-res.ok')).to_have_count(0)
        page.screenshot(path=str(output / 'config-readiness.png'), full_page=True)
        checks.append('config saved/read timing and dirty navigation guard; unready restart never claims activation')
        service_ready = True
        page.locator('.sc').get_by_role('button', name='刷新状态', exact=True).click()
        expect(page.locator('.sc-v.ok')).to_contain_text('已就绪')
        service_read_failure = True
        page.locator('.sc').get_by_role('button', name='刷新状态', exact=True).click()
        expect(page.locator('.sc-v.bad')).to_contain_text('状态读取失败')
        expect(page.locator('.sc-v.ok')).to_have_count(0)
        checks.append('failed status refresh cannot retain ready green from previous successful read')
        logs_read_failure = True
        trace_read_failure = True
        def log_list_fixture(route):
            if logs_read_failure:
                route.fulfill(status=500, content_type='application/json', body='{"detail":"fixture logs failed"}')
            else:
                route.fulfill(status=200, content_type='application/json', body=json.dumps({'data': [{
                    'id': 'log-id-is-not-session-id', 'timestamp': '2026-10-08T08:00:00',
                    'module': 'master', 'latency_ms': 1, 'content': '日志联动测试夹具',
                    'details': {'session_id': session_id}}], 'total': 1}))
        def trace_fixture(route):
            if trace_read_failure:
                route.fulfill(status=500, content_type='application/json', body='{"detail":"fixture trace failed"}')
            else:
                route.fulfill(status=200, content_type='application/json', body=json.dumps({
                    'session_id': session_id, 'master_decision': None, 'subagent_executions': [],
                    'operator_calls': [], 'llm_calls': []}))
        page.route('**/api/logs?**', log_list_fixture)
        page.route('**/api/logs/trace/**', trace_fixture)
        page.goto('http://localhost:5173/logs', wait_until='networkidle')
        expect(page.locator('.logs [role=alert]')).to_contain_text('日志加载失败')
        expect(page.get_by_text('暂无日志记录', exact=True)).to_have_count(0)
        logs_read_failure = False
        page.locator('.logs [role=alert]').get_by_role('button', name='重试', exact=True).click()
        expect(page.get_by_role('link', name='查看追溯', exact=True)).to_have_attribute('href', '/logs/trace/' + session_id)
        page.get_by_role('link', name='查看追溯', exact=True).click()
        expect(page.locator('.trc [role=alert]')).to_contain_text('追溯加载失败')
        trace_read_failure = False
        page.locator('.trc [role=alert]').get_by_role('button', name='重试', exact=True).click()
        expect(page.locator('.trc')).to_contain_text('暂无已记录的追溯数据')
        expect(page.locator('.sid')).to_have_text(session_id)
        page.screenshot(path=str(output / 'logs-session-trace.png'), full_page=True)
        checks.append('logs error/retry uses actual session link; trace failure differs from successful empty record')
        page.goto('http://localhost:5173/agents/knowledge?focus=pattern:bottle_interference', wait_until='networkidle')
        expect(page.locator('.kg-detail h3')).to_have_text('插瓶干扰')
        expect(page.locator('.kg-navbar .el-radio-button.is-active')).to_contain_text('领域知识')
        pattern_legend = page.locator('.kg-type-row').filter(has_text='违规模式')
        pattern_legend.click()
        expect(pattern_legend).to_have_class('kg-type-row off')
        def focus_node(node_id):
            page.evaluate('''url => {
                const state = {...window.history.state};
                window.history.pushState(state, '', url);
                window.dispatchEvent(new PopStateEvent('popstate', {state}));
            }''', '/agents/knowledge?focus=' + node_id)
        focus_node('pattern:artificial_fitting')
        expect(page.locator('.kg-detail h3')).to_have_text('人工拟合')
        expect(pattern_legend).to_have_class('kg-type-row')
        focus_node('service:frontend')
        expect(page.locator('.kg-detail h3')).to_contain_text('5173')
        expect(page.locator('.kg-navbar .el-radio-button.is-active')).to_contain_text('服务拓扑')
        focus_node('browser-missing-node-fixture')
        expect(page.locator('.kg-detail')).to_contain_text('未找到节点')
        page.route('**/api/v1/knowledge/node/pattern%3Abottle_interference', lambda route: route.fulfill(
            status=500, content_type='application/json', body='{"detail":"fixture node failed"}'))
        focus_node('pattern:bottle_interference')
        expect(page.locator('.kg-detail [role=alert]')).to_contain_text('节点详情加载失败')
        expect(page.locator('.kg-chart')).to_be_visible()
        page.unroute('**/api/v1/knowledge/node/pattern%3Abottle_interference')
        page.locator('.kg-detail').get_by_role('button', name='重试', exact=True).click()
        expect(page.locator('.kg-detail h3')).to_have_text('插瓶干扰')
        expect(page.locator('.kg-navbar .el-radio-button.is-active')).to_contain_text('领域知识')
        page.screenshot(path=str(output / 'knowledge-focus.png'), full_page=True)
        checks.append('reactive graph focus honors actual types and hidden legend; 404 differs from detail failure/retry')
        assert not errors, errors
        browser.close()
        if client:
            client.close()
    print(json.dumps({'mode': 'current-code-in-process' if args.in_process else 'running-services',
                      'checks': checks, 'page_errors': errors, 'screenshots': str(output)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
