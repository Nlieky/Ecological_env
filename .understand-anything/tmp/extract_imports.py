import os
import json
import ast
from pathlib import Path
from collections import defaultdict

def find_module_file(module_name, search_dirs, all_py_files):
    """
    查找模块文件
    module_name: 模块名 (如 'task_receiving_and_parsing', 'shared.configs.llm_client')
    search_dirs: 搜索目录列表
    all_py_files: 所有Python文件路径集合 (项目根目录开始的绝对路径)
    """
    parts = module_name.split('.')
    results = set()

    for search_dir in search_dirs:
        # 尝试直接 .py 文件
        test_path = os.path.join(search_dir, *parts) + '.py'
        if os.path.exists(test_path):
            rel_path = os.path.relpath(test_path, search_dir)
            # 检查是否在项目中
            for py_file in all_py_files:
                if py_file.endswith(rel_path) or py_file == test_path:
                    results.add(py_file)
                    break

        # 尝试包目录 __init__.py
        test_path = os.path.join(search_dir, *parts, '__init__.py')
        if os.path.exists(test_path):
            for py_file in all_py_files:
                if py_file == test_path:
                    results.add(py_file)
                    break

    return results

def extract_python_imports(file_path, project_root, all_py_files, all_py_paths):
    """提取Python文件的导入"""
    imports = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 移除 BOM
        if content.startswith('﻿'):
            content = content[1:]

        tree = ast.parse(content, filename=file_path)

        # 获取当前文件目录
        file_dir = os.path.dirname(file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, False))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    level = node.level  # 相对导入层级
                    imports.append((node.module, level > 0))

        # 解析导入为文件路径
        resolved = set()

        for imp_name, is_relative in imports:
            # 跳过标准库和第三方库
            if imp_name in ['os', 'sys', 'json', 'time', 'datetime', 'logging', 'pathlib',
                           'collections', 'typing', 'math', 're', 'itertools', 'functools',
                           'threading', 'multiprocessing', 'subprocess', 'io', 'random',
                           'flask', 'requests', 'pandas', 'numpy', 'scipy', 'sklearn',
                           'torch', 'tensorflow', 'matplotlib', 'plotly', 'seaborn',
                           'anthropic', 'openai', 'langchain', 'pytest', 'yaml']:
                continue

            # 确定搜索目录
            if is_relative:
                search_dirs = [file_dir]
            else:
                search_dirs = [file_dir, project_root]

            found = find_module_file(imp_name, search_dirs, all_py_paths)
            resolved.update(found)

        return sorted(resolved)
    except Exception as e:
        return []

def extract_import_map(scan_result_path, project_root):
    """提取所有文件的import map"""
    with open(scan_result_path, 'r', encoding='utf-8') as f:
        scan_data = json.load(f)

    files = scan_data['files']

    # 构建Python文件集合
    all_py_paths = set()
    py_file_map = {}  # 绝对路径 -> 相对路径

    for f in files:
        if f['language'] == 'python':
            full_path = os.path.normpath(os.path.join(project_root, f['path']))
            all_py_paths.add(full_path)
            py_file_map[full_path] = f['path']

    import_map = {}
    files_with_imports = 0
    total_edges = 0

    for f in files:
        import_map[f['path']] = []

    # 只处理Python文件
    for f in files:
        if f['language'] == 'python':
            full_path = os.path.normpath(os.path.join(project_root, f['path']))
            imported_paths = extract_python_imports(full_path, project_root, py_file_map, all_py_paths)

            # 转换为相对路径
            relative_imports = []
            for imp_path in imported_paths:
                if imp_path in py_file_map:
                    relative_imports.append(py_file_map[imp_path])

            if relative_imports:
                import_map[f['path']] = sorted(relative_imports)
                files_with_imports += 1
                total_edges += len(relative_imports)

    return {
        'scriptCompleted': True,
        'stats': {
            'filesScanned': len(files),
            'filesWithImports': files_with_imports,
            'totalEdges': total_edges
        },
        'importMap': import_map
    }

if __name__ == '__main__':
    scan_path = r'E:\project\Ecological_env\.understand-anything\tmp\ua-scan-files.json'
    project_root = r'E:\project\Ecological_env'

    result = extract_import_map(scan_path, project_root)

    output_path = r'E:\project\Ecological_env\.understand-anything\tmp\ua-import-map-output.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f'Import extraction complete: {result["stats"]["filesScanned"]} files scanned')
    print(f'Files with imports: {result["stats"]["filesWithImports"]}')
    print(f'Total edges: {result["stats"]["totalEdges"]}')

    # 显示一些示例
    sample_items = [(k, v) for k, v in result['importMap'].items() if v][:5]
    for path, imports in sample_items:
        print(f'  {path}: {imports[:3]}...' if len(imports) > 3 else f'  {path}: {imports}')
