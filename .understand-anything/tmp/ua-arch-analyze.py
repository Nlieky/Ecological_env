#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
架构分析脚本 - 分析文件路径和导入关系，识别架构层次
"""
import json
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path


def load_input(input_path):
    """加载输入JSON文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def extract_file_nodes(data):
    """从原始图谱数据中提取文件节点和相关边"""
    nodes = data.get('nodes', [])
    edges = data.get('edges', [])

    # 提取文件节点
    file_nodes = []
    config_nodes = []
    document_nodes = []
    schema_nodes = []
    table_nodes = []
    all_file_nodes = []

    node_id_map = {}  # 映射原始ID到新的命名规范

    for node in nodes:
        node_id = node.get('id', '')
        node_type = node.get('type', 'unknown')

        if node_type == 'file':
            file_path = node.get('filePath', '')
            # 转换为新的ID格式
            new_id = f"file:{file_path}"
            node_data = {
                'id': new_id,
                'type': 'file',
                'name': node.get('name', ''),
                'filePath': file_path,
                'summary': node.get('summary', ''),
                'tags': node.get('tags', []),
                'languageNotes': node.get('languageNotes', ''),
                'complexity': node.get('complexity', '')
            }
            file_nodes.append(node_data)
            all_file_nodes.append(node_data)
            node_id_map[node_id] = new_id

        elif node_type == 'config':
            file_path = node.get('filePath', node.get('name', ''))
            new_id = f"config:{file_path}"
            node_data = {
                'id': new_id,
                'type': 'config',
                'name': node.get('name', ''),
                'filePath': file_path,
                'summary': node.get('summary', ''),
                'tags': node.get('tags', [])
            }
            config_nodes.append(node_data)
            all_file_nodes.append(node_data)
            node_id_map[node_id] = new_id

        elif node_type == 'document':
            file_path = node.get('filePath', node.get('name', ''))
            new_id = f"document:{file_path}"
            node_data = {
                'id': new_id,
                'type': 'document',
                'name': node.get('name', ''),
                'filePath': file_path,
                'summary': node.get('summary', ''),
                'tags': node.get('tags', [])
            }
            document_nodes.append(node_data)
            all_file_nodes.append(node_data)
            node_id_map[node_id] = new_id

        elif node_type == 'schema':
            file_path = node.get('filePath', node.get('name', ''))
            new_id = f"schema:{file_path}"
            node_data = {
                'id': new_id,
                'type': 'schema',
                'name': node.get('name', ''),
                'filePath': file_path,
                'summary': node.get('summary', ''),
                'tags': node.get('tags', [])
            }
            schema_nodes.append(node_data)
            all_file_nodes.append(node_data)
            node_id_map[node_id] = new_id

        elif node_type == 'table':
            file_path = node.get('filePath', node.get('name', ''))
            new_id = f"table:{file_path}"
            node_data = {
                'id': new_id,
                'type': 'table',
                'name': node.get('name', ''),
                'filePath': file_path,
                'summary': node.get('summary', ''),
                'tags': node.get('tags', [])
            }
            table_nodes.append(node_data)
            all_file_nodes.append(node_data)
            node_id_map[node_id] = new_id

    # 提取导入边
    import_edges = []
    all_edges = []

    for edge in edges:
        source = edge.get('source', '')
        target = edge.get('target', '')
        edge_type = edge.get('type', '')

        # 转换节点ID
        new_source = node_id_map.get(source, '')
        new_target = node_id_map.get(target, '')

        if new_source and new_target:
            edge_data = {
                'source': new_source,
                'target': new_target,
                'type': edge_type
            }

            # 只记录文件级别的导入边
            if edge_type == 'imports' and new_source.startswith('file:') and new_target.startswith('file:'):
                import_edges.append(edge_data)

            all_edges.append(edge_data)

    return {
        'fileNodes': all_file_nodes,
        'importEdges': import_edges,
        'allEdges': all_edges
    }


def get_common_prefix(file_paths):
    """计算所有文件路径的公共前缀"""
    if not file_paths:
        return ''

    # 规范化路径
    normalized_paths = [p.replace('\\', '/') for p in file_paths]

    # 分割路径
    split_paths = [p.split('/') for p in normalized_paths]

    # 找出最短路径长度
    min_len = min(len(parts) for parts in split_paths)

    # 找公共前缀
    common_parts = []
    for i in range(min_len):
        part = split_paths[0][i]
        if all(parts[i] == part for parts in split_paths):
            common_parts.append(part)
        else:
            break

    common_prefix = '/'.join(common_parts)
    if common_prefix and not common_prefix.endswith('/'):
        common_prefix += '/'

    return common_prefix


def group_by_directory(file_nodes, common_prefix):
    """按目录分组文件节点"""
    groups = defaultdict(list)

    for node in file_nodes:
        file_path = node.get('filePath', '')

        # 移除公共前缀
        if common_prefix and file_path.startswith(common_prefix):
            remaining = file_path[len(common_prefix):]
        else:
            remaining = file_path

        # 规范化路径分隔符
        remaining = remaining.replace('\\', '/')

        # 获取第一级目录
        parts = remaining.split('/')
        if len(parts) > 1:
            # 有子目录，使用第一级目录名
            group_name = parts[0]
        else:
            # 根目录文件，按文件类型分组
            filename = parts[0] if parts else ''
            ext = os.path.splitext(filename)[1].lower()
            base = os.path.splitext(filename)[0].lower()

            if filename in ['README', 'README.md', 'CHANGELOG.md', 'CONTRIBUTING.md']:
                group_name = 'docs'
            elif ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg']:
                group_name = 'config'
            elif ext in ['.md', '.rst', '.txt']:
                group_name = 'docs'
            elif ext in ['.sh', '.bat', '.ps1']:
                group_name = 'scripts'
            else:
                group_name = 'root'

        groups[group_name].append(node['id'])

    return dict(groups)


def group_by_node_type(file_nodes):
    """按节点类型分组"""
    groups = defaultdict(list)

    for node in file_nodes:
        node_type = node.get('type', 'file')
        groups[node_type].append(node['id'])

    return dict(groups)


def build_adjacency_matrix(import_edges, file_node_ids):
    """构建导入邻接矩阵"""
    # 初始化邻接表
    fan_out = defaultdict(int)  # 每个文件导入多少其他文件
    fan_in = defaultdict(int)   # 每个文件被多少文件导入
    adjacency = defaultdict(set)  # 每个文件导入哪些文件

    for edge in import_edges:
        source = edge['source']
        target = edge['target']

        if source in file_node_ids and target in file_node_ids:
            fan_out[source] += 1
            fan_in[target] += 1
            adjacency[source].add(target)

    return {
        'fanOut': dict(fan_out),
        'fanIn': dict(fan_in),
        'adjacency': {k: list(v) for k, v in adjacency.items()}
    }


def compute_directory_imports(directory_groups, import_edges, file_node_to_dir):
    """计算目录间的导入关系"""
    dir_imports = defaultdict(lambda: defaultdict(int))

    for edge in import_edges:
        source = edge['source']
        target = edge['target']

        from_dir = file_node_to_dir.get(source)
        to_dir = file_node_to_dir.get(target)

        if from_dir and to_dir and from_dir != to_dir:
            dir_imports[from_dir][to_dir] += 1

    # 转换为列表格式
    result = []
    for from_dir, to_dirs in dir_imports.items():
        for to_dir, count in to_dirs.items():
            result.append({
                'from': from_dir,
                'to': to_dir,
                'count': count
            })

    return result


def compute_intra_group_density(directory_groups, import_edges, file_node_to_dir):
    """计算组内导入密度"""
    density = {}

    # 统计每个组的内部边数和总边数
    for group_name, node_ids in directory_groups.items():
        node_set = set(node_ids)
        internal_edges = 0
        total_edges = 0

        for edge in import_edges:
            source = edge['source']
            target = edge['target']

            if source in node_set or target in node_set:
                total_edges += 1
                if source in node_set and target in node_set:
                    internal_edges += 1

        density_value = internal_edges / total_edges if total_edges > 0 else 0
        density[group_name] = {
            'internalEdges': internal_edges,
            'totalEdges': total_edges,
            'density': density_value
        }

    return density


def match_directory_patterns(directory_groups):
    """匹配目录名称到架构模式"""
    patterns = {
        # API层
        'routes': 'api', 'api': 'api', 'controllers': 'api', 'endpoints': 'api',
        'handlers': 'api', 'routers': 'api', 'controller': 'api',

        # 服务层
        'services': 'service', 'core': 'service', 'lib': 'service',
        'domain': 'service', 'logic': 'service', 'internal': 'service',
        'composables': 'service', 'signals': 'service',

        # 数据层
        'models': 'data', 'db': 'data', 'data': 'data',
        'persistence': 'data', 'repository': 'data', 'entities': 'data',
        'entity': 'data', 'migrations': 'data', 'sql': 'data',

        # UI层
        'components': 'ui', 'views': 'ui', 'pages': 'ui',
        'ui': 'ui', 'layouts': 'ui', 'screens': 'ui',

        # 中间件
        'middleware': 'middleware', 'plugins': 'middleware',
        'interceptors': 'middleware', 'guards': 'middleware',

        # 工具层
        'utils': 'utility', 'helpers': 'utility', 'common': 'utility',
        'shared': 'utility', 'tools': 'utility', 'pkg': 'utility',
        'templatetags': 'utility',

        # 配置层
        'config': 'config', 'constants': 'config', 'env': 'config',
        'settings': 'config', 'management': 'config',

        # 测试层
        '__tests__': 'test', 'test': 'test', 'tests': 'test',
        'spec': 'test', 'specs': 'test',

        # 类型层
        'types': 'types', 'interfaces': 'types', 'schemas': 'types',
        'contracts': 'types', 'dtos': 'types', 'dto': 'types',

        # 状态层
        'store': 'state', 'state': 'state', 'reducers': 'state',
        'actions': 'state', 'slices': 'state',

        # 资源层
        'assets': 'assets', 'static': 'assets', 'public': 'assets',

        # 入口层
        'cmd': 'entry', 'bin': 'entry',

        # 文档层
        'docs': 'documentation', 'documentation': 'documentation',
        'wiki': 'documentation',

        # 基础设施层
        'deploy': 'infrastructure', 'deployment': 'infrastructure',
        'infra': 'infrastructure', 'infrastructure': 'infrastructure',
        'docker': 'infrastructure', 'k8s': 'infrastructure',
        'kubernetes': 'infrastructure', 'helm': 'infrastructure',
        'charts': 'infrastructure', 'terraform': 'infrastructure',
        'tf': 'infrastructure',

        # CI/CD层
        '.github': 'ci-cd', '.gitlab': 'ci-cd', '.circleci': 'ci-cd',
    }

    matches = {}
    for dir_name in directory_groups.keys():
        matched = False
        for pattern, label in patterns.items():
            if pattern in dir_name.lower():
                matches[dir_name] = label
                matched = True
                break
        if not matched:
            # 默认未匹配
            matches[dir_name] = 'unknown'

    return matches


def match_file_patterns(file_nodes):
    """匹配文件级别的模式"""
    patterns = {
        # 测试文件
        ('.test.',): 'test',
        ('.spec.',): 'test',
        ('test_', '.py'): 'test',
        ('_test.', '.go'): 'test',
        ('Test', '.java'): 'test',
        ('_spec.', '.rb'): 'test',
        ('Test', '.php'): 'test',
        ('Tests', '.cs'): 'test',

        # 类型文件
        ('.d.ts',): 'types',

        # 入口文件
        ('index.ts',): 'entry',
        ('index.js',): 'entry',
        ('__init__.py',): 'entry',
        ('manage.py',): 'entry',
        ('wsgi.py',): 'config',
        ('asgi.py',): 'config',
        ('main.go',): 'entry',
        ('main.rs',): 'entry',
        ('lib.rs',): 'entry',
        ('Application.java',): 'entry',
        ('Program.cs',): 'entry',
        ('config.ru',): 'entry',

        # 配置文件
        ('Cargo.toml',): 'config',
        ('go.mod',): 'config',
        ('Gemfile',): 'config',
        ('pom.xml',): 'config',
        ('build.gradle',): 'config',
        ('composer.json',): 'config',
        ('tsconfig.json',): 'config',
        ('package.json',): 'config',

        # 基础设施文件
        ('Dockerfile',): 'infrastructure',
        ('docker-compose.',): 'infrastructure',
        ('.tf',): 'infrastructure',
        ('.tfvars',): 'infrastructure',
        ('Makefile',): 'infrastructure',

        # CI/CD文件
        ('.github/workflows/',): 'ci-cd',
        ('.gitlab-ci.yml',): 'ci-cd',
        ('Jenkinsfile',): 'ci-cd',

        # 数据文件
        ('.sql',): 'data',

        # 类型定义文件
        ('.graphql',): 'types',
        ('.gql',): 'types',
        ('.proto',): 'types',

        # 文档文件
        ('.md',): 'documentation',
        ('.rst',): 'documentation',
    }

    file_matches = {}
    for node in file_nodes:
        file_path = node.get('filePath', '')
        filename = os.path.basename(file_path)

        for pattern_tuple in patterns:
            label = patterns[pattern_tuple]
            matched = False

            for pattern in pattern_tuple:
                if pattern.startswith('.'):
                    # 扩展名匹配
                    if filename.endswith(pattern):
                        file_matches[node['id']] = label
                        matched = True
                        break
                elif pattern.startswith('.github'):
                    # 路径匹配
                    if pattern in file_path:
                        file_matches[node['id']] = label
                        matched = True
                        break
                else:
                    # 文件名匹配
                    if pattern in filename:
                        file_matches[node['id']] = label
                        matched = True
                        break

            if matched:
                break

    return file_matches


def detect_deployment_topology(file_nodes):
    """检测部署拓扑"""
    topology = {
        'hasDockerfile': False,
        'hasCompose': False,
        'hasK8s': False,
        'hasTerraform': False,
        'hasCI': False,
        'infraFiles': []
    }

    for node in file_nodes:
        file_path = node.get('filePath', '').lower()

        if 'dockerfile' in file_path:
            topology['hasDockerfile'] = True
            topology['infraFiles'].append(node['filePath'])
        elif 'docker-compose' in file_path:
            topology['hasCompose'] = True
            topology['infraFiles'].append(node['filePath'])
        elif any(x in file_path for x in ['.k8s', 'k8s', 'kubernetes', 'helm', 'charts']):
            topology['hasK8s'] = True
            topology['infraFiles'].append(node['filePath'])
        elif any(x in file_path for x in ['.tf', 'terraform', 'tfvars']):
            topology['hasTerraform'] = True
            topology['infraFiles'].append(node['filePath'])
        elif any(x in file_path for x in ['.github', '.gitlab', '.circleci', 'jenkinsfile']):
            topology['hasCI'] = True
            topology['infraFiles'].append(node['filePath'])

    return topology


def detect_data_pipeline(file_nodes):
    """检测数据管道"""
    pipeline = {
        'schemaFiles': [],
        'migrationFiles': [],
        'dataModelFiles': [],
        'apiHandlerFiles': []
    }

    for node in file_nodes:
        file_path = node.get('filePath', '').lower()
        tags = node.get('tags', [])

        if 'schema' in tags or any(x in file_path for x in ['schema', '.graphql', '.proto']):
            pipeline['schemaFiles'].append(node['filePath'])
        elif 'migration' in file_path or 'migrate' in file_path:
            pipeline['migrationFiles'].append(node['filePath'])
        elif 'model' in tags or any(x in file_path for x in ['model', 'entity', 'db']):
            pipeline['dataModelFiles'].append(node['filePath'])
        elif any(x in tags for x in ['api', 'handler', 'endpoint', 'route']):
            pipeline['apiHandlerFiles'].append(node['filePath'])

    return pipeline


def compute_doc_coverage(directory_groups, file_nodes):
    """计算文档覆盖率"""
    docs_in_groups = set()

    for node in file_nodes:
        if node.get('type') == 'document':
            file_path = node.get('filePath', '')
            # 检查是否在某个组的目录中
            for group_name in directory_groups.keys():
                if group_name in file_path or group_name == 'docs':
                    docs_in_groups.add(group_name)
                    break

    total_groups = len(directory_groups)
    groups_with_docs = len(docs_in_groups)

    # 找出没有文档的组
    undocumented = [g for g in directory_groups.keys() if g not in docs_in_groups]

    return {
        'groupsWithDocs': groups_with_docs,
        'totalGroups': total_groups,
        'coverageRatio': groups_with_docs / total_groups if total_groups > 0 else 0,
        'undocumentedGroups': undocumented
    }


def compute_dependency_direction(inter_group_imports):
    """计算依赖方向"""
    # 统计每对组之间的导入关系
    pair_imports = defaultdict(lambda: {'a_to_b': 0, 'b_to_a': 0})

    for imp in inter_group_imports:
        from_dir = imp['from']
        to_dir = imp['to']

        # 创建排序的键以确保一致性
        key = tuple(sorted([from_dir, to_dir]))
        if from_dir < to_dir:
            pair_imports[key]['a_to_b'] += imp['count']
        else:
            pair_imports[key]['b_to_a'] += imp['count']

    # 确定主导方向
    dependencies = []
    for key, counts in pair_imports.items():
        dir_a, dir_b = key

        if counts['a_to_b'] > counts['b_to_a']:
            dependencies.append({
                'dependent': dir_b,
                'dependsOn': dir_a,
                'strength': counts['a_to_b']
            })
        elif counts['b_to_a'] > counts['a_to_b']:
            dependencies.append({
                'dependent': dir_a,
                'dependsOn': dir_b,
                'strength': counts['b_to_a']
            })

    return dependencies


def compute_cross_category_edges(all_edges):
    """计算跨类别边"""
    cross_category = defaultdict(lambda: defaultdict(int))

    for edge in all_edges:
        source = edge['source']
        target = edge['target']
        edge_type = edge['type']

        # 提取节点类型
        source_type = source.split(':')[0] if ':' in source else 'unknown'
        target_type = target.split(':')[0] if ':' in target else 'unknown'

        cross_category[source_type][target_type] += 1

    # 转换为列表格式
    result = []
    for from_type, to_types in cross_category.items():
        for to_type, count in to_types.items():
            result.append({
                'fromType': from_type,
                'toType': to_type,
                'count': count
            })

    return result


def create_file_node_to_dir_map(directory_groups):
    """创建文件节点到目录的映射"""
    mapping = {}
    for dir_name, node_ids in directory_groups.items():
        for node_id in node_ids:
            mapping[node_id] = dir_name
    return mapping


def analyze(input_path, output_path):
    """主分析函数"""
    # 加载数据
    data = load_input(input_path)

    # 提取文件节点和边
    extracted = extract_file_nodes(data)
    file_nodes = extracted['fileNodes']
    import_edges = extracted['importEdges']
    all_edges = extracted['allEdges']

    # 创建文件节点ID集合
    file_node_ids = {node['id'] for node in file_nodes}

    # 获取文件路径
    file_paths = [node.get('filePath', '') for node in file_nodes if node.get('filePath')]
    common_prefix = get_common_prefix(file_paths)

    # A. 目录分组
    directory_groups = group_by_directory(file_nodes, common_prefix)

    # B. 节点类型分组
    node_type_groups = group_by_node_type(file_nodes)

    # C. 导入邻接矩阵
    adjacency = build_adjacency_matrix(import_edges, file_node_ids)

    # 创建文件节点到目录的映射
    file_node_to_dir = create_file_node_to_dir_map(directory_groups)

    # E. 组间导入频率
    inter_group_imports = compute_directory_imports(directory_groups, import_edges, file_node_to_dir)

    # F. 组内导入密度
    intra_group_density = compute_intra_group_density(directory_groups, import_edges, file_node_to_dir)

    # G. 目录模式匹配
    pattern_matches = match_directory_patterns(directory_groups)

    # 文件模式匹配
    file_pattern_matches = match_file_patterns(file_nodes)

    # H. 部署拓扑检测
    deployment_topology = detect_deployment_topology(file_nodes)

    # I. 数据管道检测
    data_pipeline = detect_data_pipeline(file_nodes)

    # J. 文档覆盖率
    doc_coverage = compute_doc_coverage(directory_groups, file_nodes)

    # K. 依赖方向
    dependency_direction = compute_dependency_direction(inter_group_imports)

    # 跨类别边
    cross_category_edges = compute_cross_category_edges(all_edges)

    # 文件统计
    files_per_group = {name: len(ids) for name, ids in directory_groups.items()}
    node_type_counts = {t: len(ids) for t, ids in node_type_groups.items()}

    # 构建输出
    output = {
        'scriptCompleted': True,
        'commonPrefix': common_prefix,
        'directoryGroups': directory_groups,
        'nodeTypeGroups': node_type_groups,
        'crossCategoryEdges': cross_category_edges,
        'interGroupImports': inter_group_imports,
        'intraGroupDensity': intra_group_density,
        'patternMatches': pattern_matches,
        'filePatternMatches': file_pattern_matches,
        'deploymentTopology': deployment_topology,
        'dataPipeline': data_pipeline,
        'docCoverage': doc_coverage,
        'dependencyDirection': dependency_direction,
        'fileStats': {
            'totalFileNodes': len(file_nodes),
            'filesPerGroup': files_per_group,
            'nodeTypeCounts': node_type_counts
        },
        'fileFanIn': adjacency['fanIn'],
        'fileFanOut': adjacency['fanOut']
    }

    # 写入输出文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python ua-arch-analyze.py <input_path> <output_path>')
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        result = analyze(input_path, output_path)
        print(f'Analysis complete. Results written to {output_path}')
        print(f'Found {result["fileStats"]["totalFileNodes"]} file nodes')
        print(f'Identified {len(result["directoryGroups"])} directory groups')
        sys.exit(0)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
