"""Synthetic, read-only probe of actual Hermes provider messages, without persisting system prompt or credentials."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.verify_assistant_intent_clarification import context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--variant', choices=['baseline', 'skill-last', 'mode-scope', 'scoped-skill-last'], default='baseline')
    parser.add_argument('--repeat', type=int, default=1)
    args = parser.parse_args()
    from scripts.start_agent import AgentService
    from shared.assistant.master_turn import SystemInteractionRuntime

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    service = AgentService()
    captures = []
    model_shapes = []
    skill = Path('skills/system-interaction-core/SKILL.md').read_text(encoding='utf-8')

    def factory(session):
        agent = service._create_main_agent(system_interaction=True, session_id=session)
        original_turn = agent.run_conversation
        original_api = agent._interruptible_api_call
        original_stream = agent._interruptible_streaming_api_call

        def turn(**kwargs):
            # Diagnostic-only prompt variants; no production routing/filter changes.
            if args.variant in ('skill-last', 'scoped-skill-last'):
                prefix, document = agent.ephemeral_system_prompt.split('\n能力契约：', 1)
                agent.ephemeral_system_prompt = prefix.replace(skill, '') + '\n能力契约：' + document + '\n' + skill
            if args.variant in ('mode-scope', 'scoped-skill-last'):
                agent.ephemeral_system_prompt += '\n当前模式优先：身份文件的专业编排与主动取数职责仅适用于专业分析通道，不适用于本轮。澄清问题是本轮完整有效的回答，不要求生成候选。能力契约是字段合法性约束，不是必须采取操作的要求。'
            result = original_turn(**kwargs)
            raw = result.get('final_response') if isinstance(result, dict) else None
            try:
                data = json.loads(raw)
                model_shapes.append({key: {'type': type(value).__name__, 'keys': list(value) if isinstance(value, dict) else None}
                                     for key, value in data.items()})
            except (ValueError, TypeError, AttributeError):
                model_shapes.append({'non_object_json': True})
            return result

        def record(kwargs):
            messages = kwargs.get('messages', [])
            systems = [m.get('content', '') for m in messages if m.get('role') == 'system']
            joined = '\n'.join(systems)
            captures.append({
                'roles': [m.get('role') for m in messages],
                'system_count': len(systems), 'system_chars': len(joined),
                'system_sha256': hashlib.sha256(joined.encode()).hexdigest(),
                'full_skill_present': skill.strip() in joined,
                'skill_before_contract': joined.find('# 全系统交互') < joined.find('能力契约：'),
                'professional_identity_instruction_count': joined.count('目标是带着答案回来，不是带着问题'),
                'professional_agents_file_loaded': '凡涉及数据 / 监测 / 异常' in joined,
                'private_memory_loaded': '## MEMORY.md' in joined,
                'tools_sent': len(kwargs.get('tools') or []),
                'response_format': kwargs.get('response_format'),
                # All non-system messages are our own synthetic test inputs.
                'messages': [m for m in messages if m.get('role') != 'system'],
            })

        def capture(kwargs):
            record(kwargs)
            return original_api(kwargs)

        def capture_stream(kwargs, **options):
            record(kwargs)
            return original_stream(kwargs, **options)

        agent.run_conversation = turn
        agent._interruptible_api_call = capture
        agent._interruptible_streaming_api_call = capture_stream
        return agent

    runtime = SystemInteractionRuntime(factory, 'skills/system-interaction-core/SKILL.md')
    results = []
    requests = [
        ('first-missing-object', '打开指标查询，看当前厂站最近1小时的COD记录。', []),
        ('followup-missing-object', '我要在指标查询里看，不需要AI分析。', [
            {'role': 'user', 'content': '查看当前厂站最近6小时的总氮数据'},
            {'role': 'assistant', 'content': '请明确厂站，以及希望在大屏还是指标查询页查看这6小时总氮数据。'},
        ]),
    ]
    for name, query, history in [(f'{name}-{index}', query, history) for index in range(args.repeat) for name, query, history in requests]:
        try:
            result = runtime.respond({'query': query, 'session_id': 'probe-' + name, 'context': context('events'), 'history': history})
            results.append({'name': name, 'response': result, 'clarified': not result.get('actions') and not result.get('handoff')})
        except Exception as error:
            results.append({'name': name, 'clarified': False, 'error': type(error).__name__})
        print(json.dumps({'name': name, 'clarified': results[-1]['clarified']}, ensure_ascii=True), flush=True)
        (output / 'results.json').write_text(json.dumps({'variant': args.variant, 'captures': captures, 'model_shapes': model_shapes, 'cases': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
