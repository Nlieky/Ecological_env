"""
测试完整的LLM驱动流程

通过FastAPI后端调用主智能体，验证：
1. LLM理解用户意图
2. 主智能体调用子智能体
3. 子智能体处理任务
4. 返回整合结果
"""
import requests
import json

# API配置
API_URL = "http://localhost:8000/api/query"
HEADERS = {"Content-Type": "application/json"}

print("=" * 60)
print("完整的LLM驱动流程测试")
print("=" * 60)

# 测试查询
test_queries = [
    "最近24小时出水COD异常吗？",
    "分析当前废水监测数据",
    "检查是否有违规情况"
]

for i, query in enumerate(test_queries, 1):
    print(f"\n测试 {i}: {query}")
    print("-" * 60)

    # 发送请求
    payload = {"query": query}
    print(f"发送请求: {json.dumps(payload, ensure_ascii=False)}")

    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)

        print(f"响应状态: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print(f"\n[结果]")
            print(f"回答: {data.get('content', 'N/A')[:200]}...")

            if data.get('decision_path'):
                print(f"\n[决策路径]")
                for step in data.get('decision_path', []):
                    print(f"  步骤 {step.get('step_number')}: {step.get('step_name')}")
                    print(f"    决策: {step.get('decision')}")
                    print(f"    操作: {step.get('action')}")

            if data.get('sub_agent_calls'):
                print(f"\n[子智能体调用]")
                for call in data.get('sub_agent_calls', []):
                    print(f"  - {call}")

            print(f"\n[会话ID] {data.get('session_id')}")
            print(f"[时间戳] {data.get('timestamp')}")

        else:
            print(f"错误: {response.text}")

    except requests.exceptions.Timeout:
        print("请求超时（60秒）")
    except Exception as e:
        print(f"请求失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
