"""Live read-only Agent smoke; retain one clearly labelled acceptance conversation."""
import json
import time
import uuid

import requests


def main():
    session = str(uuid.uuid4())
    query = '第二批服务验收：请简短确认服务连通；不要调用工具，不新增、修改或删除任何业务知识和事件。'
    started = time.monotonic()
    done = None
    with requests.post('http://localhost:8000/api/query/stream', json={
        'query': query, 'session_id': session,
    }, stream=True, timeout=(10, 180)) as response:
        response.raise_for_status()
        response.encoding = 'utf-8'
        for line in response.iter_lines(decode_unicode=True):
            if not line.startswith('data:'):
                continue
            event = json.loads(line[5:].strip())
            if event.get('type') == 'error':
                raise AssertionError(event)
            if event.get('type') == 'done':
                done = event
                break  # Immediately close just like the completed frontend reader.
    assert done and done.get('content'), 'No successful terminal answer'
    final_session = done.get('session_id') or session
    detail = requests.get(f'http://localhost:8000/api/v1/conversations/{final_session}', timeout=10).json()
    assert detail.get('success') and len(detail['data']['messages']) >= 2, detail
    assert detail['data']['messages'][-1]['content'] == done['content'], 'Answer was not persisted before done'
    trace = requests.get(f'http://localhost:8000/api/logs/trace/{final_session}', timeout=10).json()
    assert trace.get('master_decision'), 'Audit was not persisted before done'
    for field in ['queue_elapsed_ms', 'turn_elapsed_ms']:
        assert isinstance(done.get(field), (int, float)) and done[field] >= 0, (field, done.get(field))
    print(json.dumps({'session_id': final_session, 'elapsed_ms': round((time.monotonic() - started) * 1000),
                      'queue_elapsed_ms': done['queue_elapsed_ms'], 'turn_elapsed_ms': done['turn_elapsed_ms'],
                      'messages': len(detail['data']['messages']), 'audit_persisted_before_done': True}, ensure_ascii=True))


if __name__ == '__main__':
    main()
