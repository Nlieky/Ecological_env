"""
快速测试API连接
"""
import requests
import json

# 简单测试
print("测试API连接...")

try:
    # 测试健康检查
    response = requests.get("http://localhost:8000/api/health", timeout=5)
    print(f"健康检查: {response.status_code} - {response.json().get('status')}")

    # 测试查询接口（设置较长超时）
    print("\n发送测试查询...")
    response = requests.post(
        "http://localhost:8000/api/query",
        json={"query": "你好"},
        timeout=180  # 3分钟超时
    )

    if response.status_code == 200:
        data = response.json()
        print("查询成功!")
        print(f"会话ID: {data.get('session_id')}")
        print(f"内容类型: {type(data.get('content'))}")

        # 显示决策路径
        if data.get('decision_path'):
            print("\n决策路径:")
            for step in data.get('decision_path', [])[:5]:
                print(f"  - {step.get('step_name')}: {step.get('decision')}")
    else:
        print(f"查询失败: {response.status_code}")
        print(response.text[:200])

except requests.exceptions.Timeout:
    print("请求超时（LLM处理时间过长）")
except Exception as e:
    print(f"错误: {e}")
