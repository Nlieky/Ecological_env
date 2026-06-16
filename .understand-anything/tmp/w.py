import json
output = {"nodes": [{"id": "file:shared/operators/__init__.py", "type": "file", "name": "__init__.py", "filePath": "shared/operators/__init__.py", "summary": "异常检测算子库的统一入口模块，整合机器学习、深度学习和专用三类检测器，提供算子获取和列表查询功能。", "tags": ["entry-point", "barrel", "异常检测", "算子库", "工厂模式"], "complexity": "moderate"}], "edges": [{"source": "file:shared/operators/__init__.py", "target": "file:shared/operators/deep_learning/__init__.py", "type": "imports", "direction": "forward", "weight": 0.7}]}
with open(".understand-anything/intermediate/batch-1.json", "w", encoding="utf-8") as f: json.dump(output, f, ensure_ascii=False, indent=2)
print("OK")
