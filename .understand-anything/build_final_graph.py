#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build final knowledge graph with proper metadata."""

import json
from pathlib import Path

def main():
    project_root = Path(r"E:\project\Ecological_env")
    intermediate_dir = project_root / ".understand-anything" / "intermediate"

    # Load assembled graph
    assembled_file = intermediate_dir / "assembled-graph.json"
    with open(assembled_file, "r", encoding="utf-8") as f:
        assembled = json.load(f)

    # Load architecture analysis
    arch_file = intermediate_dir / "architecture-analysis.json"
    try:
        with open(arch_file, "r", encoding="utf-8") as f:
            architecture = json.load(f)
    except:
        architecture = {"layers": []}

    # Load tour
    tour_file = intermediate_dir / "tour.json"
    try:
        with open(tour_file, "r", encoding="utf-8") as f:
            tour_data = json.load(f)
            tour = tour_data.get("tour", tour_data)
    except:
        tour = {"steps": []}

    # Build final knowledge graph
    final_graph = {
        "metadata": {
            "schemaVersion": "1.0.0",
            "projectName": "废水虚假排放智能监测系统",
            "projectDescription": "基于多智能体协同的废水虚假排放智能监测系统。采用六层标准化架构，集成LLM驱动的智能体、多维异常检测算法、规则推理引擎，实现插瓶干扰、暗管偷排、清水稀释等违规行为的精准识别，支持自然语言交互分析和Web可视化监控。",
            "generatedAt": "2026-06-09T15:45:00+08:00",
            "language": "zh",
            "totalNodes": len(assembled.get("nodes", [])),
            "totalEdges": len(assembled.get("edges", [])),
            "gitCommitHash": "8579de201a27332a5482944dd74a1c81f4f9c289",
            "pluginVersion": "2.7.5"
        },
        "nodes": assembled.get("nodes", []),
        "edges": assembled.get("edges", []),
        "architecture": architecture,
        "tour": tour
    }

    # Write output
    output_file = project_root / ".understand-anything" / "knowledge-graph.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_graph, f, ensure_ascii=False, indent=2)

    print("Final knowledge graph written to: {}".format(output_file))
    print("Total nodes: {}".format(len(final_graph["nodes"])))
    print("Total edges: {}".format(len(final_graph["edges"])))
    print("Architecture layers: {}".format(len(final_graph.get("architecture", {}).get("layers", []))))
    print("Tour steps: {}".format(len(final_graph.get("tour", {}).get("steps", []))))

if __name__ == "__main__":
    main()
