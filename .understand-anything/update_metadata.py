#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Update knowledge graph with scan result metadata."""

import json
from pathlib import Path

def main():
    project_root = Path(r"E:\project\Ecological_env")
    ua_dir = project_root / ".understand-anything"

    # Load current knowledge graph
    kg_file = ua_dir / "knowledge-graph.json"
    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    # Load scan result
    scan_file = ua_dir / "intermediate" / "scan-result.json"
    with open(scan_file, "r", encoding="utf-8") as f:
        scan = json.load(f)

    # Update metadata with scan information
    kg["metadata"].update({
        "languages": scan.get("languages", []),
        "frameworks": scan.get("frameworks", []),
        "complexity": scan.get("complexity", "unknown"),
        "fileCategories": scan.get("fileCategories", {}),
        "totalFiles": scan.get("totalFiles", 0),
        "scanDate": scan.get("scanDate", "2026-06-09")
    })

    # Ensure architecture has layer info
    if "architecture" in kg and "layers" in kg["architecture"]:
        kg["metadata"]["architectureLayers"] = len(kg["architecture"]["layers"])

    # Write back
    with open(kg_file, "w", encoding="utf-8") as f:
        json.dump(kg, f, ensure_ascii=False, indent=2)

    print("Updated knowledge graph with scan metadata")
    print("Languages:", kg["metadata"].get("languages"))
    print("Frameworks:", kg["metadata"].get("frameworks"))
    print("Complexity:", kg["metadata"].get("complexity"))

if __name__ == "__main__":
    main()
