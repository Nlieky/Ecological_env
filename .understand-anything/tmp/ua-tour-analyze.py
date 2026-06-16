#!/usr/bin/env python3
import json
import sys
from collections import defaultdict, deque

def main():
    if len(sys.argv) < 3:
        print("Usage: python ua-tour-analyze.py <input-json> <output-json>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    nodes = input_data.get('nodes', [])
    edges = input_data.get('edges', [])
    layers = input_data.get('layers', [])

    # 构建邻接表
    in_edges = defaultdict(list)  # node -> incoming edges
    out_edges = defaultdict(list) # node -> outgoing edges

    for node in nodes:
        node_id = node['id']
        in_edges[node_id] = []
        out_edges[node_id] = []

    for edge in edges:
        source = edge['source']
        target = edge['target']
        if target in in_edges:
            in_edges[target].append(edge)
        if source in out_edges:
            out_edges[source].append(edge)

    # A. Fan-In Ranking (重要性)
    fan_in_ranking = []
    for node in nodes:
        node_id = node['id']
        fan_in_ranking.append({
            'id': node_id,
            'fanIn': len(in_edges[node_id]),
            'name': node.get('name', ''),
            'summary': node.get('summary', ''),
            'type': node.get('type', '')
        })

    fan_in_ranking.sort(key=lambda x: x['fanIn'], reverse=True)
    fan_in_ranking = fan_in_ranking[:20]

    # B. Fan-Out Ranking (范围)
    fan_out_ranking = []
    for node in nodes:
        node_id = node['id']
        fan_out_ranking.append({
            'id': node_id,
            'fanOut': len(out_edges[node_id]),
            'name': node.get('name', ''),
            'summary': node.get('summary', ''),
            'type': node.get('type', '')
        })

    fan_out_ranking.sort(key=lambda x: x['fanOut'], reverse=True)
    fan_out_ranking = fan_out_ranking[:20]

    # 计算阈值
    fan_in_values = [len(in_edges[n['id']]) for n in nodes]
    fan_out_values = [len(out_edges[n['id']]) for n in nodes]

    if fan_in_values:
        fan_in_max = max(fan_in_values)
        fan_in_threshold = fan_in_max * 0.9  # top 10%
        fan_in_sorted = sorted(fan_in_values)
        fan_in_bottom_threshold = fan_in_sorted[len(fan_in_sorted) // 4]  # bottom 25%
    else:
        fan_in_threshold = 0
        fan_in_bottom_threshold = 0

    if fan_out_values:
        fan_out_max = max(fan_out_values)
        fan_out_top_threshold = fan_out_max * 0.9  # top 10%
    else:
        fan_out_top_threshold = 0

    # C. Entry Point Candidates
    entry_point_candidates = []

    for node in nodes:
        score = 0
        filename = node.get('name', '')
        file_path = node.get('filePath', '')
        node_type = node.get('type', '')

        # 代码文件评分规则
        if node_type == 'file':
            # 入口文件名
            if filename == '__init__.py':
                score += 3
            if filename in ['main.py', 'app.py', 'server.py', 'index.ts', 'index.js']:
                score += 3

            # 文件深度（根目录或一级）
            depth = file_path.count('/')
            if depth <= 1:
                score += 1

            # 高fan-out（top 10%）
            fan_out = len(out_edges[node['id']])
            if fan_out >= fan_out_top_threshold:
                score += 1

            # 低fan-in（bottom 25%）
            fan_in = len(in_edges[node['id']])
            if fan_in <= fan_in_bottom_threshold:
                score += 1

        # 文档文件评分规则
        if node_type == 'document':
            if filename == 'README.md' and depth == 0:
                score += 5
            elif filename.endswith('.md') and depth <= 1:
                score += 2

        if score > 0:
            entry_point_candidates.append({
                'id': node['id'],
                'score': score,
                'name': filename,
                'summary': node.get('summary', '')
            })

    entry_point_candidates.sort(key=lambda x: x['score'], reverse=True)
    entry_point_candidates = entry_point_candidates[:5]

    # D. BFS Traversal (从入口点开始)
    # 找到代码入口点（排除文档）
    code_entry_points = [ep for ep in entry_point_candidates
                        if any(n['id'] == ep['id'] and n.get('type') == 'file' for n in nodes)]

    if code_entry_points:
        start_node = code_entry_points[0]['id']
    elif entry_point_candidates:
        start_node = entry_point_candidates[0]['id']
    else:
        start_node = nodes[0]['id'] if nodes else None

    bfs_order = []
    depth_map = {}
    visited = set()
    queue = deque()

    if start_node:
        queue.append((start_node, 0))
        visited.add(start_node)

        while queue:
            node, depth = queue.popleft()
            bfs_order.append(node)
            depth_map[node] = depth

            # 只跟随imports和calls边
            for edge in out_edges.get(node, []):
                if edge.get('type') in ['imports', 'calls']:
                    target = edge.get('target')
                    if target and target not in visited:
                        visited.add(target)
                        queue.append((target, depth + 1))

    # 按深度分组
    by_depth = defaultdict(list)
    for node, depth in depth_map.items():
        by_depth[str(depth)].append(node)

    # E. Non-Code Files Inventory
    non_code_files = {
        'documentation': [],
        'infrastructure': [],
        'data': [],
        'config': []
    }

    for node in nodes:
        node_type = node.get('type', '')
        if node_type == 'document':
            non_code_files['documentation'].append({
                'id': node['id'],
                'name': node.get('name', ''),
                'summary': node.get('summary', '')
            })
        elif node_type in ['service', 'pipeline']:
            non_code_files['infrastructure'].append({
                'id': node['id'],
                'name': node.get('name', ''),
                'summary': node.get('summary', '')
            })
        elif node_type in ['table', 'schema', 'endpoint']:
            non_code_files['data'].append({
                'id': node['id'],
                'name': node.get('name', ''),
                'summary': node.get('summary', '')
            })
        elif node_type == 'config':
            non_code_files['config'].append({
                'id': node['id'],
                'name': node.get('name', ''),
                'summary': node.get('summary', '')
            })

    # F. Tightly Coupled Clusters
    # 找出双向关系
    bidirectional_pairs = []
    edge_set = set()

    for edge in edges:
        edge_key = f"{edge['source']}|{edge['target']}"
        edge_set.add(edge_key)

    for edge in edges:
        if edge.get('type') in ['imports', 'calls']:
            reverse_key = f"{edge['target']}|{edge['source']}"
            if reverse_key in edge_set:
                bidirectional_pairs.append([edge['source'], edge['target']])

    # 构建簇
    clusters = []
    visited_nodes = set()

    for pair in bidirectional_pairs:
        if pair[0] in visited_nodes or pair[1] in visited_nodes:
            continue

        cluster = set(pair)
        added = True

        while added:
            added = False
            for node in nodes:
                node_id = node['id']
                if node_id in cluster:
                    continue

                # 计算该节点与簇中节点的连接数
                connections = 0
                for cluster_node in cluster:
                    if f"{node_id}|{cluster_node}" in edge_set or \
                       f"{cluster_node}|{node_id}" in edge_set:
                        connections += 1

                if connections >= 2:
                    cluster.add(node_id)
                    added = True

        if len(cluster) >= 2:
            cluster_nodes = list(cluster)
            for n in cluster_nodes:
                visited_nodes.add(n)

            # 计算簇内部的边数
            edge_count = 0
            for a in cluster_nodes:
                for b in cluster_nodes:
                    if a != b and f"{a}|{b}" in edge_set:
                        edge_count += 1

            clusters.append({
                'nodes': cluster_nodes,
                'edgeCount': edge_count
            })

    clusters.sort(key=lambda x: x['edgeCount'], reverse=True)
    clusters = clusters[:10]

    # G. Layer List
    layers_output = {
        'count': len(layers),
        'list': [{'id': l['id'], 'name': l['name'], 'description': l['description']}
                 for l in layers]
    }

    # H. Node Summary Index
    node_summary_index = {}
    for node in nodes:
        node_summary_index[node['id']] = {
            'name': node.get('name', ''),
            'type': node.get('type', ''),
            'summary': node.get('summary', ''),
            'filePath': node.get('filePath', '')
        }

    # 输出结果
    output = {
        'scriptCompleted': True,
        'entryPointCandidates': entry_point_candidates,
        'fanInRanking': fan_in_ranking,
        'fanOutRanking': fan_out_ranking,
        'bfsTraversal': {
            'startNode': start_node,
            'order': bfs_order,
            'depthMap': depth_map,
            'byDepth': dict(by_depth)
        },
        'nonCodeFiles': non_code_files,
        'clusters': clusters,
        'layers': layers_output,
        'nodeSummaryIndex': node_summary_index,
        'totalNodes': len(nodes),
        'totalEdges': len(edges)
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Results written to {output_file}")
    sys.exit(0)

if __name__ == '__main__':
    main()