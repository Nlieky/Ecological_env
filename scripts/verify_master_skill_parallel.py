"""Live main/sidebar overlap smoke, no tools or business writes requested."""
import asyncio
import json
import time
import uuid
from pathlib import Path
import httpx
from playwright.async_api import async_playwright


async def main():
    output = Path('logs/assistant-verification/migration-live')
    output.mkdir(parents=True, exist_ok=True)
    sid = 'parallel-check-' + uuid.uuid4().hex[:12]
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
        async def professional():
            begin = time.monotonic() - started
            response = await client.post('http://localhost:8642/query', json={
                'query': '请用一句简短中文介绍你自己。只回答身份，不调用任何工具。',
                'session_id': sid,
            })
            return {'status': response.status_code, 'start': begin,
                    'end': time.monotonic() - started, 'body': response.json()}
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width':1440, 'height':900})
            # Same external ID as professional request deliberately tests channel isolation.
            await context.add_init_script('sessionStorage.setItem("ecological.assistant.v1", ' + json.dumps(json.dumps({'version':1,'sessionId':sid,'messages':[]})) + ')')
            page = await context.new_page()
            await page.goto('http://localhost:5173/dashboard', wait_until='domcontentloaded')
            await page.get_by_role('button', name='AIOps 智能助手').click()
            await page.locator('#assistant-query').fill('解释当前页面，不执行操作。')
            # Prepare the browser first; otherwise a short main turn can finish
            # during Chromium startup and never actually exercise concurrency.
            pro_task = asyncio.create_task(professional())
            log = Path('logs/assistant-verification/operation-20261019/agent-final.err.log')
            for _ in range(150):
                if pro_task.done() or ('处理查询: session=' + sid) in log.read_text(encoding='utf-8', errors='replace'):
                    break
                await asyncio.sleep(.05)
            begin = time.monotonic() - started
            async with page.expect_response(lambda r:'/api/assistant/respond' in r.url, timeout=70000) as pending:
                await page.locator('#assistant-query').press('Enter')
            response = await pending.value
            side = {'status':response.status,'start':begin,'end':time.monotonic()-started,'body':await response.json()}
            await page.get_by_role('button', name='发送', exact=True).wait_for()
            await page.screenshot(path=str(output/'parallel.png'), full_page=True)
            await browser.close()
        pro = await pro_task
        report = {'professional':pro,'sidebar':side,
                  'transport_overlap':max(pro['start'],side['start']) < min(pro['end'],side['end']),
                  'same_external_session_id':sid}
        (output/'parallel.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'main_status':pro['status'],'side_status':side['status'],
                          'overlap':report['transport_overlap'],'main_seconds':round(pro['end']-pro['start'],2),
                          'side_seconds':round(side['end']-side['start'],2)}),flush=True)
        assert pro['status']==200 and side['status']==200, report
        assert report['transport_overlap'], 'Requests did not overlap; do not claim parallel verification'
        assert pro['body'].get('success') is True
        assert not pro['body'].get('trace',{}).get('subagent_calls',[]) if pro['body'].get('trace') else True


if __name__ == '__main__':
    asyncio.run(main())
