"""Real-model routing and clarification checks; generates candidates only, never executes them."""
import argparse
import json
from pathlib import Path
import uuid

import httpx


PLANT = '当阳市金桥污水处理厂一期'


def context(page, plant=None):
    return {
        'pageId': page, 'route': {'events': '/events', 'dashboard': '/dashboard', 'metrics': '/metrics', 'graph': '/agents/knowledge'}[page],
        'plant': plant, 'indicator': None,
        'range': {'start': '2026-07-24 14:00', 'end': '2026-07-25 14:00'} if page == 'dashboard' else None,
        'source': 'monitoring-real' if page != 'events' else '事件接口',
        'freshness': 'historical' if page != 'events' else None,
        'status': 'ready', 'filters': {},
    }


def check_response(body, expected):
    if expected == 'clarify':
        assert not body.get('actions') and not body.get('handoff') and not body.get('pending'), body
        assert any(word in body.get('message', '') for word in ('请', '希望', '哪个', '哪家', '还是', '？', '?')), body
        return
    if expected == 'handoff':
        assert body.get('handoff', {}).get('query') and not body.get('actions'), body
        return
    capability, parameters = expected
    assert not body.get('handoff') and not body.get('pending'), body
    assert len(body.get('actions', [])) == 1, body
    action = body['actions'][0]
    assert action['capability'] == capability, body
    for key, value in parameters.items():
        assert action['parameters'].get(key) == value, body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--only', help='Comma-separated flow names')
    parser.add_argument('--repeat', type=int, default=1, choices=range(1, 11))
    parser.add_argument('--holdout', action='store_true', help='Different expressions and object types not embedded in the Skill')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    flows = [
        ('ambiguous-events', context('events'), [
            ('查看当前厂站最近6小时的总氮数据', 'clarify'),
            ('我要在指标查询里看，不需要AI分析。', 'clarify'),
            (f'厂站选{PLANT}。', ('metrics.filter', {'plant': PLANT, 'indicator': 'TN', 'range': '6h'})),
        ]),
        ('ambiguous-purpose', context('events'), [
            ('帮我看看COD最近一天的情况。', 'clarify'),
            (f'我要让主页面AI分析变化原因，厂站是{PLANT}。', 'handoff'),
        ]),
        ('explicit-metrics', context('events'), [
            (f'打开指标查询，展示{PLANT}最近6小时的总氮数据，不要分析。',
             ('metrics.filter', {'plant': PLANT, 'indicator': 'TN', 'range': '6h'})),
        ]),
        ('metrics-context', context('metrics', PLANT), [
            ('把当前厂站的氨氮监测记录按最近24小时展示出来。',
             ('metrics.filter', {'indicator': 'AN', 'range': '24h'})),
        ]),
        ('dashboard-context', context('dashboard', PLANT), [
            ('这个大屏只显示当前厂站的总磷。', ('dashboard.view', {'indicator': 'TP'})),
        ]),
        ('missing-plant', context('events'), [
            ('打开指标查询，看当前厂站最近1小时的COD记录。', 'clarify'),
            (f'就是{PLANT}。', ('metrics.filter', {'plant': PLANT, 'indicator': 'COD', 'range': '1h'})),
        ]),
        ('explicit-analysis', context('dashboard', PLANT), [
            ('请让主页面AI分析当前厂站总氮变化原因，并给出专业研判报告。', 'handoff'),
        ]),
        ('navigation', context('events'), [
            ('打开监测大屏。', ('navigate', {'pageId': 'dashboard'})),
        ]),
    ]
    if args.holdout:
        flows = [
            ('unknown-event', context('events'), [
                ('帮我打开那个事件的详情。', 'clarify'),
                ('事件编号是evt_holdout_42。', ('events.detail', {'eventId': 'evt_holdout_42'})),
            ]),
            ('unknown-node', context('graph'), [
                ('把那个节点定位出来。', 'clarify'),
                ('节点编号是node_holdout_17。', ('graph.focus', {'nodeId': 'node_holdout_17'})),
            ]),
            ('plant-before-location', context('events'), [
                ('帮我调出近24小时的总磷监测记录。', 'clarify'),
                (f'厂站是{PLANT}。', 'clarify'),
                ('放在指标查询页面展示就好。', ('metrics.filter', {'plant': PLANT, 'indicator': 'TP', 'range': '24h'})),
            ]),
            ('purpose-only', context('events', PLANT), [
                ('给我看看这个厂的氨氮情况。', 'clarify'),
            ]),
            ('ready-metrics-synonym', context('metrics', PLANT), [
                ('监测记录换成COD，时间选一小时。', ('metrics.filter', {'indicator': 'COD', 'range': '1h'})),
            ]),
            ('ready-dashboard-range', context('dashboard', PLANT), [
                ('当前大屏的采样窗口换成一天。', ('dashboard.range', {'range': '24h'})),
            ]),
            ('unsupported-range', context('metrics', PLANT), [
                ('请在这个指标查询页展示当前厂站最近一个月的总氮记录。', 'clarify'),
            ]),
            ('independent-navigation', context('events'), [
                ('去日志中心。', ('navigate', {'pageId': 'logs'})),
            ]),
        ]
    flows = [(f'{name}#{index + 1}', snapshot, turns) for index in range(args.repeat)
             for name, snapshot, turns in flows if not args.only or name in args.only.split(',')]
    results = []
    with httpx.Client(timeout=80, trust_env=False) as client:
        for name, snapshot, turns in flows:
            history, pending, records = [], None, []
            session = 'clarification-' + uuid.uuid4().hex
            try:
                for query, expected in turns:
                    response = client.post('http://127.0.0.1:8000/api/assistant/respond', json={
                        'query': query, 'session_id': session, 'context': snapshot,
                        'history': history, 'pending': pending,
                    })
                    body = response.json()
                    records.append({'query': query, 'status': response.status_code, 'response': body})
                    assert response.status_code == 200, body
                    check_response(body, expected)
                    if name.startswith('ambiguous-purpose#') and expected == 'handoff':
                        draft = body['handoff']['query']
                        assert 'COD' in draft and any(value in draft for value in ('一天', '24小时', '24h')), body
                        assert PLANT in draft, body
                    history.extend([{'role': 'user', 'content': query}, {'role': 'assistant', 'content': body['message']}])
                    pending = body.get('pending')
                result = {'name': name, 'passed': True, 'turns': records}
            except Exception as error:
                result = {'name': name, 'passed': False, 'error': str(error)[:3000], 'turns': records}
            results.append(result)
            print(json.dumps({'name': name, 'passed': result['passed']}, ensure_ascii=True), flush=True)
            (output / 'results.json').write_text(json.dumps({'passed': all(r['passed'] for r in results), 'cases': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if results and all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
