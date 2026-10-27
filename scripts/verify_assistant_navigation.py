"""Regression: real navigation remains usable after source data finishes loading."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    output = Path('logs/assistant-verification/navigation-refresh')
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        # Start the genuine model request with a loading source snapshot, then
        # let the real page settle before executing its explicit navigation.
        page.goto('http://localhost:5173/dashboard', wait_until='domcontentloaded')
        page.get_by_role('button', name='AIOps 智能助手').click()
        page.locator('#assistant-query').fill('打开事件中心')
        with page.expect_response(lambda r: '/api/assistant/respond' in r.url, timeout=75000) as pending:
            page.locator('#assistant-query').press('Enter')
        response = pending.value
        body = response.json()
        assert response.status == 200, body
        assert any(a['capability'] == 'navigate' and a['parameters'] == {'pageId': 'events'} for a in body['actions']), body
        expect(page.locator('.dash-page .page-state')).to_have_attribute('aria-busy', 'false', timeout=60000)
        page.locator('.action-card').first.click()
        expect(page).to_have_url('http://localhost:5173/events', timeout=15000)
        assert not errors, errors
        page.screenshot(path=str(output / 'events.png'), full_page=True)
        result = {'passed': True, 'request_context': response.request.post_data_json['context'], 'response': body, 'url': page.url, 'page_errors': errors}
        (output / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'passed': True, 'url': page.url}))
        browser.close()


if __name__ == '__main__':
    main()
