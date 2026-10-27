"""Read-only browser state acceptance. All fixtures are GET-only; never writes backend data."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'logs' / 'batch3-verification'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://localhost:5173')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    results, mutations = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        def run(name, test, width=1366):
            context = browser.new_context(viewport={'width': width, 'height': 768})
            page = context.new_page()
            page.set_default_timeout(7000)
            page.set_default_navigation_timeout(30000)
            state = {'mode': 'ok', 'calls': []}
            node = {'id': 'fixture-node', 'label': '验收节点', 'type': 'plant', 'props': {'说明': '验收详情'}}
            def route_handler(route):
                req = route.request
                if req.method not in ('GET', 'HEAD', 'OPTIONS'):
                    mutations.append({'method': req.method, 'url': req.url})
                    route.abort()
                    return
                parsed = urlparse(req.url)
                path, query = parsed.path, parse_qs(parsed.query)
                state['calls'].append(req.url)
                status, data = 200, None
                if path == '/api/v1/conversations':
                    rows = [{'id': 'fixture-session', 'title': '部分标题命中验收', 'message_count': 1, 'started_at': '2026-01-01T00:00:00Z'}]
                    search = query.get('search', [''])[0]
                    if search and search not in rows[0]['title'] and search not in rows[0]['id']: rows = []
                    data = {'success': True, 'data': {'conversations': rows, 'total_count': len(rows), 'page': 1, 'page_size': 20}}
                elif path.startswith('/api/v1/conversations/'):
                    data = {'success': True, 'data': {'id': path.rsplit('/', 1)[-1], 'title': '深链接会话验收', 'message_count': 1, 'messages': [{'role': 'user', 'content': '验收消息'}]}}
                elif path.startswith('/api/logs/trace/'):
                    data = {'session_id': 'fixture-session', 'master_decision': None, 'subagent_runs': [], 'operator_calls': [], 'llm_calls': []}
                elif path == '/api/logs':
                    status = 500 if state['mode'] == 'error' else 200
                    data = {'data': [{'id': i, 'module': 'api', 'content': f'验收日志 {i}', 'timestamp': '2026-01-01T00:00:00Z', 'details': {'key': '独立上下文'}} for i in range(20)], 'total': 45}
                elif path == '/api/v1/plants/tree':
                    data = {'success': True, 'data': {'cities': [], 'ungrouped': [{'plant_id': '验收厂', 'name': '验收厂'}]}}
                elif path.endswith('/dashboard'):
                    status = 500 if state['mode'] == 'error' else 200
                    series = {'influent': [{'time': '2026-01-01T01:00:00', 'value': 40}], 'effluent': [] if state['mode'] == 'partial' else [{'time': '2026-01-01T01:00:00', 'value': 12}]}
                    data = {'success': True, 'data': {'plant_id': '验收厂', 'window_hours': 24, 'latest_time': '2026-01-01T01:00:00', 'segment_start': '2026-01-01', 'segment_end': '2026-01-02', 'influent_points': 1, 'effluent_points': 0 if state['mode'] == 'partial' else 1, 'data_context': {'origin': 'real', 'mode': 'historical', 'freshness': 'historical', 'timezone': 'Asia/Shanghai', 'bucket': 'fixture'}, 'indicators': {'COD': {'label': 'COD', 'unit': 'mg/L', 'series': series, 'current': {'influent': 40, 'effluent': 12}, 'status': 'normal'}}}}
                elif path == '/api/v1/system/history':
                    data = {'data': [{'day': f'2026-01-{i:02}', 'points': 2, 'influent_points': 1, 'effluent_points': 1, 'exceed': 0, 'metrics': {'effluent': {'COD': 12}}} for i in range(1, 31)]}
                elif path == '/api/v1/knowledge/graph':
                    data = {'success': True, 'seeded': True, 'nodes': [node], 'edges': [], 'stats': {'nodes': 1, 'edges': 0, 'node_types': {'plant': 1}, 'edge_types': {}}}
                    if state['mode'] == 'empty':
                        data.update(seeded=False, nodes=[], edges=[])
                elif path.startswith('/api/v1/knowledge/node/'):
                    status = {'notfound': 404, 'error': 500}.get(state['mode'], 200)
                    data = {'success': True, 'node': node, 'neighbors': {}}
                elif path == '/api/v1/agents/config/entities':
                    status = 500 if state['mode'] == 'error' else 200
                    data = {'success': True, 'data': [{'name': 'master', 'label': '主智能体', 'icon': '', 'dir': 'fixture', 'identity_files': ['AGENTS.md'], 'skills': []}]}
                elif path == '/api/v1/agents/config/files':
                    data = {'success': True, 'data': {'path': 'AGENTS.md', 'content': '验收原文', 'size': 12, 'mtime': '2026-01-01'}}
                elif path == '/api/v1/agents/config/files/history': data = {'success': True, 'data': []}
                elif path == '/api/v1/agents/config/skills':
                    data = {'success': True, 'data': {'skills': [{'name': 'fixture-skill', 'display_name': '验收技能', 'description': '只读fixture', 'scripts': [], 'enabled': True}], 'templates': []}}
                elif path == '/api/v1/agents/config/skills/file':
                    data = {'success': True, 'data': {'path': 'SKILL.md', 'content': '验收技能原文', 'size': 18, 'mtime': '2026-01-01'}}
                if data is None: route.continue_()
                else: route.fulfill(status=status, content_type='application/json', body=json.dumps(data))
            page.route('**/api/**', route_handler)
            def goto(path):
                page.goto(args.base_url + path, wait_until='networkidle')
            try:
                test(page, state, goto)
                results.append({'name': name, 'passed': True})
            except Exception as error:
                results.append({'name': name, 'passed': False, 'error': str(error), 'url': page.url})
            finally:
                page.screenshot(path=str(OUT / f'state-{name}.png'), full_page=True)
                context.close()

        def audit(p, s, go):
            go('/agents/audit?session=outside-session')
            expect(p.locator('.d-ttl')).to_have_text('深链接会话验收')
            expect(p.locator('.selection-note')).to_be_visible()
            p.get_by_label('搜索标题或会话ID').fill('部分标题')
            p.wait_for_timeout(500)
            expect(p.locator('.list .item')).to_have_count(1)
            assert any('search=' in x and '%E9%83%A8' in x for x in s['calls'])
            p.get_by_label('清除搜索').click()
            expect(p.get_by_label('搜索标题或会话ID')).to_have_value('')
            expect(p.locator('.list .item')).to_have_count(1)
        run('audit-search-clear-deeplink', audit)

        def metrics(p, s, go):
            s['mode'] = 'error'; go('/metrics')
            expect(p.get_by_role('button', name='重试', exact=True)).to_be_visible()
            p.screenshot(path=str(OUT / 'state-metrics-initial-error.png'))
            s['mode'] = 'partial'; p.get_by_role('button', name='重试', exact=True).click()
            expect(p.get_by_text('当前指标缺少出水数据', exact=True)).to_be_visible()
            expect(p.get_by_text('部分数据暂不可用', exact=True)).to_be_visible()
            p.screenshot(path=str(OUT / 'state-metrics-partial.png'))
            s['mode'] = 'error'; p.get_by_role('button', name='24H', exact=True).click()
            expect(p.locator('.page-state__message').filter(has_text=re.compile('刷新失败.*保留'))).to_be_visible()
            expect(p.locator('.stats')).to_be_visible()
            p.screenshot(path=str(OUT / 'state-metrics-stale-preserved.png'))
            s['mode'] = 'ok'
            p.locator('input[type=date]').nth(0).fill('2026-02-02')
            p.locator('input[type=date]').nth(1).fill('2026-01-01')
            expect(p.get_by_text('结束日期不能早于开始日期', exact=True)).to_be_visible()
        run('metrics-error-partial-stale-date', metrics)

        def dashboard(p, s, go):
            go('/dashboard')
            expect(p.locator('.board')).to_be_visible()
            expect(p.locator('.live-dot.on')).to_have_count(0)
            p.get_by_role('button', name='态势历史', exact=True).click()
            expect(p.locator('.sh .tbl .tr')).to_have_count(31)
            p.locator('.sh .tbl').evaluate('(e) => e.scrollTop = e.scrollHeight')
            assert p.locator('.sh .tbl').evaluate('(e) => e.scrollTop + e.clientHeight >= e.scrollHeight - 2')
            p.locator('.sh .tbl .tr').last.scroll_into_view_if_needed()
            box = p.locator('.sh .tbl .tr').last.bounding_box()
            assert box and box['y'] >= 0 and box['y'] + box['height'] <= 770, box
        run('dashboard-historical-scroll', dashboard)

        def graph(mode):
            def test(p, s, go):
                s['mode'] = mode; go('/agents/knowledge?focus=fixture-node')
                expect(p.locator('.el-drawer')).to_be_visible()
                p.screenshot(path=str(OUT / f'state-graph-open-{mode}.png'))
                if mode == 'notfound':
                    expect(p.get_by_text('未找到节点：fixture-node', exact=True)).to_be_visible()
                    s['mode'] = 'ok'; p.get_by_role('button', name='重新查找节点', exact=True).click()
                elif mode == 'error':
                    expect(p.get_by_role('button', name='重试', exact=True)).to_be_visible()
                    s['mode'] = 'ok'; p.get_by_role('button', name='重试', exact=True).click()
                expect(p.locator('.kg-detail-head h3')).to_have_text('验收节点')
                p.get_by_role('button', name='关闭', exact=True).click()
                expect(p.locator('.el-drawer')).to_have_count(0)
            return test
        for mode in ['ok', 'notfound', 'error']: run('graph-drawer-' + mode, graph(mode), 1100)

        def graph_empty(p, s, go):
            s['mode'] = 'empty'; go('/agents/knowledge')
            expect(p.get_by_text('暂无图谱数据，请联系管理员核验知识库初始化状态', exact=True)).to_be_visible()
            s['mode'] = 'ok'; p.get_by_role('button', name='刷新图谱', exact=True).click()
            expect(p.locator('.kg-body')).to_be_visible()
            p.locator('.kg-search').click()
            p.locator('.el-select-dropdown__item').filter(has_text='验收节点').click()
            expect(p.locator('.kg-detail-head h3')).to_have_text('验收节点')
        run('graph-empty-recover-click', graph_empty, 1100)

        def config(p, s, go):
            s['mode'] = 'error'; go('/agents/config?tab=files')
            expect(p.get_by_text('配置初始化失败，请重试', exact=True)).to_be_visible()
            s['mode'] = 'ok'; p.get_by_role('button', name='重试', exact=True).click()
            p.locator('.ed-fi').click()
            expect(p.locator('textarea.ed-ta')).to_have_value('验收原文')
            assert not p.evaluate("() => !dispatchEvent(new Event('beforeunload', {cancelable: true}))")
            p.locator('textarea.ed-ta').fill('验收未保存草稿')
            assert p.evaluate("() => !dispatchEvent(new Event('beforeunload', {cancelable: true}))")
        run('config-retry-beforeunload', config)

        def skills_dirty(p, s, go):
            go('/agents/config?tab=skills')
            p.get_by_role('button', name='查看/编辑', exact=True).click()
            expect(p.locator('textarea.sk-ta')).to_have_value('验收技能原文')
            p.locator('textarea.sk-ta').fill('验收技能未保存草稿')
            assert p.evaluate("() => !dispatchEvent(new Event('beforeunload', {cancelable: true}))")
            dialogs = []
            def dismiss(dialog):
                dialogs.append(dialog.message)
                dialog.dismiss()
            p.on('dialog', dismiss)
            p.get_by_role('button', name='身份文件', exact=True).click()
            expect(p.locator('textarea.sk-ta')).to_have_value('验收技能未保存草稿')
            assert dialogs and '未保存' in dialogs[0]
        run('config-skills-dirty-guard', skills_dirty)

        def logs(p, s, go):
            s['mode'] = 'error'; go('/logs')
            expect(p.get_by_role('button', name='重试', exact=True)).to_be_visible()
            s['mode'] = 'ok'; p.get_by_role('button', name='重试', exact=True).click()
            expect(p.locator('.log-row')).to_have_count(20)
            p.locator('summary').first.click()
            expect(p.locator('details[open]')).to_have_count(1)
            expect(p.locator('details[open] .dv')).to_have_text('独立上下文')
            box = p.locator('.pager').bounding_box()
            assert box and box['y'] + box['height'] <= 770, box
            p.locator('.pager .btn-next').click()
            p.wait_for_timeout(300)
            assert any('page=2' in x for x in s['calls'])
        run('logs-retry-expand-pagination', logs)
        browser.close()
    report = {'passed': sum(r['passed'] for r in results), 'total': len(results), 'checks': results, 'blocked_mutations': mutations}
    (OUT / 'states.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    return 1 if mutations or any(not r['passed'] for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
