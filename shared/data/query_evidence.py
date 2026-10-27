"""Deterministic response evidence from session artifacts, never model claims."""
import json
from pathlib import Path
from shared.data.source_context import sampling_timestamp
import pandas as pd


def _read(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _dict(value):
    return value if isinstance(value, dict) else {}


def _timestamp(value):
    if value is None:
        return None
    try:
        timestamp = sampling_timestamp(value)
        return None if pd.isna(timestamp) else timestamp
    except (ValueError, TypeError, OverflowError):
        return None


def _line(metadata, plant, start, end, filename):
    context = _dict(metadata.get("data_context"))
    origin = context.get("origin") or "unverified"
    mode = context.get("mode") or "unverified"
    if origin not in {"real", "simulated", "unverified"} or not context.get("bucket"):
        origin = "unverified"
    if origin == "unverified":
        caveat = "来源未核实，不得作为实时监管证据"
    elif origin == "simulated":
        caveat = "模拟演示数据"
    else:
        caveat = {"historical": "历史真实数据，非实时接入", "live": "以原始采样时间及新鲜度为准"}.get(mode, "数据模式未知，不得表述为实时监管证据")
    warning = context.get("warning")
    return (f"来源 {origin}；bucket `{context.get('bucket') or '未知'}`；监测点 {plant or '未知'}；"
            f"实际采样 {start.isoformat()} 至 {end.isoformat()}；证据 `{filename}`。{caveat}。"
            + (f"{warning}。" if isinstance(warning, str) and warning else ""))


def append_evidence(content, session_dir):
    if not session_dir:
        return content
    root = Path(session_dir)
    lines, primary_plant = [], None
    artifact = _read(root / "data_result.json")
    if artifact.get("status") == "completed":
        result = _dict(artifact.get("result"))
        timestamps = []
        for side in ("influent", "effluent"):
            rows = result.get(side)
            for row in rows if isinstance(rows, list) else []:
                timestamp = _timestamp(_dict(row).get("timestamp"))
                if timestamp is not None:
                    timestamps.append(timestamp)
        if timestamps:
            metadata = _dict(result.get("metadata"))
            primary_plant = metadata.get("plant")
            lines.append(_line(metadata, primary_plant, min(timestamps), max(timestamps), "data_result.json"))
    for plant, entry in _read(root / "data_result_plants.json").items():
        entry = _dict(entry)
        if entry.get("status") != "completed" or plant == primary_plant:
            continue
        metadata = _dict(entry.get("metadata"))
        span = _dict(metadata.get("sampling_range"))
        start, end = _timestamp(span.get("start")), _timestamp(span.get("end"))
        if start is None or end is None or start > end:
            continue
        lines.append(_line(metadata, plant, start, end, "data_result_plants.json"))
    if not lines:
        return content
    return content + "\n\n---\n数据证据（服务器读取本会话记录，可能沿用前轮采样快照）：\n\n" + "\n\n".join(lines) + "\n\n异常不等于违规；本结果用于辅助研判，需人工复核。"
