#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Merge batch analysis results into a single knowledge graph."""

import json
import os
from pathlib import Path

def load_json(filepath):
    """Load JSON file if it exists."""
    if not filepath.exists():
        return {"nodes": [], "edges": []}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error loading {}: {}".format(filepath, e))
        return {"nodes": [], "edges": []}

def merge_graphs(graphs):
    """Merge multiple graphs into one."""
    merged = {"nodes": [], "edges": []}
    seen_nodes = {}
    seen_edges = {}

    for graph in graphs:
        # Merge nodes
        for node in graph.get("nodes", []):
            node_id = node.get("id", "")
            if node_id and node_id not in seen_nodes:
                seen_nodes[node_id] = node
                merged["nodes"].append(node)

        # Merge edges
        for edge in graph.get("edges", []):
            # Create edge key from source, target, and relation
            edge_key = (
                edge.get("source", ""),
                edge.get("target", ""),
                edge.get("relation", "")
            )
            if edge_key not in seen_edges:
                seen_edges[edge_key] = edge
                merged["edges"].append(edge)

    return merged

def main():
    project_root = Path(r"E:\project\Ecological_env")
    intermediate_dir = project_root / ".understand-anything" / "intermediate"
    output_file = intermediate_dir / "assembled-graph.json"

    # Find all batch files
    batch_files = list(intermediate_dir.glob("batch-*.json"))
    batch_files.sort(key=lambda p: p.name)

    print(f"Found {len(batch_files)} batch files")

    # Load all batch graphs
    graphs = []
    for batch_file in batch_files:
        graph = load_json(batch_file)
        if graph.get("nodes") or graph.get("edges"):
            graphs.append(graph)
            print(f"Loaded {batch_file.name}: {len(graph.get('nodes', []))} nodes, {len(graph.get('edges', []))} edges")

    if not graphs:
        print("No valid batch files found!")
        return

    # Merge all graphs
    merged = merge_graphs(graphs)

    # Add metadata
    merged["metadata"] = {
        "schemaVersion": 1,
        "totalNodes": len(merged["nodes"]),
        "totalEdges": len(merged["edges"]),
        "batchFilesProcessed": len(graphs)
    }

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\nMerged graph written to: {output_file}")
    print(f"Total nodes: {len(merged['nodes'])}")
    print(f"Total edges: {len(merged['edges'])}")

if __name__ == "__main__":
    main()
