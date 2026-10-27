"""Real browser + real model regression for assistant response compatibility.

Only sends assistant/respond; never clicks action cards or submits business writes.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    output = Path('logs/assistant-verification/live-503')
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://localhost:5173/dashboard', wait_until='domcontentloaded')
        page.get_by_role('button', name='AIOps 智能助手').click()
        for index in range(12):
            query = '解释当前页面' if index % 2 == 0 else '请帮我打开事件中心'
            page.locator('#assistant-query').fill(query)
            with page.expect_response(lambda r: '/api/assistant/respond' in r.url, timeout=60000) as pending:
                page.locator('#assistant-query').press('Enter')
            response = pending.value
            body = response.json()
            request = response.request.post_data_json
            case = {'index': index, 'query': query, 'status': response.status,
                    'context': request['context'], 'history_count': len(request['history']),
                    'response': body}
            results.append(case)
            print(json.dumps({'case': index, 'status': response.status,
                              'history_count': len(request['history'])}), flush=True)
            (output / 'results.json').write_text(json.dumps({'cases': results, 'page_errors': errors}, ensure_ascii=False, indent=2), encoding='utf-8')
            assert response.status == 200, case
            assert isinstance(body.get('message'), str) and body['message']
            assert isinstance(body.get('actions'), list)
            page.get_by_role('button', name='发送', exact=True).wait_for()
        # Closing/reopening and a browser refresh retain history, not a fake pending task.
        page.get_by_role('button', name='收起助手').click()
        page.get_by_role('button', name='AIOps 智能助手').click()
        page.reload(wait_until='domcontentloaded')
        page.get_by_role('button', name='AIOps 智能助手').click()
        page.locator('#assistant-query').fill('解释当前页面')
        with page.expect_response(lambda r: '/api/assistant/respond' in r.url, timeout=60000) as pending:
            page.locator('#assistant-query').press('Enter')
        response = pending.value
        assert response.status == 200, response.text()
        page.get_by_role('button', name='发送', exact=True).wait_for()
        page.screenshot(path=str(output / 'after.png'), full_page=True)
        assert not errors, errors
        results.append({'index': 12, 'restored': True, 'status': response.status, 'response': response.json()})
        (output / 'results.json').write_text(json.dumps({'passed': True, 'cases': results, 'page_errors': errors}, ensure_ascii=False, indent=2), encoding='utf-8')
        browser.close()


if __name__ == '__main__':
    main()
