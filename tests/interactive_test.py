"""
交互式LLM测试工具

在终端中直接输入问题，实时查看LLM驱动的智能体响应
"""
import requests
import json

API_URL = "http://localhost:8000/api/query"
HEADERS = {"Content-Type": "application/json"}

print("=" * 60)
print("废水监测系统 - LLM驱动智能体交互测试")
print("=" * 60)
print("输入你的问题，输入 'quit' 退出")
print()

while True:
    try:
        query = input("你> ").strip()

        if not query:
            continue

        if query.lower() in ['quit', 'exit', 'q']:
            print("再见！")
            break

        print("\n[处理中...]")
        response = requests.post(API_URL, json={"query": query}, headers=HEADERS, timeout=60)

        if response.status_code == 200:
            data = response.json()

            print(f"\n智能体> ", end="")

            # 提取回答内容
            if isinstance(data.get('content'), str):
                print(data['content'])
            elif isinstance(data.get('content'), dict):
                print(data['content'].get('final_response', str(data['content'])))
            else:
                print(str(data.get('content', '无法解析回答')))

            # 显示决策路径
            if data.get('decision_path'):
                print("\n[决策路径]")
                for step in data['decision_path']:
                    print(f"  {step.get('step_number')}. {step.get('step_name')}: {step.get('decision')}")

            # 显示会话信息
            print(f"\n[会话ID] {data.get('session_id', 'N/A')}")
            print(f"[时间] {data.get('timestamp', 'N/A')}")

        else:
            print(f"\n错误: {response.status_code}")
            print(response.text)

        print("\n" + "-" * 60)

    except KeyboardInterrupt:
        print("\n\n再见！")
        break
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n" + "-" * 60)
