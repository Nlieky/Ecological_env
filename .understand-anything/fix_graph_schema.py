#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix knowledge graph to match dashboard schema."""

import json
from pathlib import Path

def main():
    project_root = Path(r"E:\project\Ecological_env")
    ua_dir = project_root / ".understand-anything"

    # Load assembled graph
    with open(ua_dir / "intermediate" / "assembled-graph.json", "r", encoding="utf-8") as f:
        assembled = json.load(f)

    # Load scan result
    with open(ua_dir / "intermediate" / "scan-result.json", "r", encoding="utf-8") as f:
        scan = json.load(f)

    # Load architecture
    arch_file = ua_dir / "intermediate" / "architecture-analysis.json"
    try:
        with open(arch_file, "r", encoding="utf-8") as f:
            arch_data = json.load(f)
            layers = arch_data.get("layers", [])
    except:
        layers = []

    # Load tour
    tour_file = ua_dir / "intermediate" / "tour.json"
    try:
        with open(tour_file, "r", encoding="utf-8") as f:
            tour_data = json.load(f)
            tour = tour_data.get("tour", tour_data)
            tour_steps = tour.get("steps", [])
    except:
        tour_steps = []

    # Build correct schema
    knowledge_graph = {
        "version": "1.0.0",
        "kind": "codebase",
        "project": {
            "name": "废水虚假排放智能监测系统",
            "description": "基于多智能体协同的废水虚假排放智能监测系统。采用六层标准化架构，集成LLM驱动的智能体、多维异常检测算法、规则推理引擎，实现插瓶干扰、暗管偷排、清水稀释等违规行为的精准识别，支持自然语言交互分析和Web可视化监控。",
            "languages": scan.get("languages", []),
            "frameworks": scan.get("frameworks", []),
            "analyzedAt": "2026-06-09T15:45:00+08:00",
            "gitCommitHash": "8579de201a27332a5482944dd74a1c81f4f9c289"
        },
        "nodes": assembled.get("nodes", []),
        "edges": assembled.get("edges", []),
        "layers": layers,
        "tour": tour_steps
    }

    # Write output
    output_file = ua_dir / "knowledge-graph.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(knowledge_graph, f, ensure_ascii=False, indent=2)

    print("Fixed knowledge graph written to:", output_file)
    print("Project name:", knowledge_graph["project"]["name"])
    print("Nodes:", len(knowledge_graph["nodes"]))
    print("Edges:", len(knowledge_graph["edges"]))
    print("Layers:", len(knowledge_graph["layers"]))
    print("Tour steps:", len(knowledge_graph["tour"]))

if __name__ == "__main__":
    main()
