"""Canonical subagent names, paths, outputs, and runtime tool policy."""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SubagentSpec:
    name: str
    directory: str
    result_file: str


_SPECS = {
    "multi-dimensional-data-perception": SubagentSpec(
        "multi-dimensional-data-perception",
        "subagents/multi-dimensional-data-perception-agent",
        "data_result.json",
    ),
    "anomaly-detection": SubagentSpec(
        "anomaly-detection", "subagents/anomaly-detection-agent", "anomaly_result.json"
    ),
    "rule-reasoning": SubagentSpec(
        "rule-reasoning", "subagents/rule-reasoning-agent", "rule_reasoning_result.json"
    ),
    "disposition-execution": SubagentSpec(
        "disposition-execution",
        "subagents/disposition-execution-agent",
        "disposition_result.json",
    ),
}

_ALIASES = {
    "data-perception": "multi-dimensional-data-perception",
    "anomaly": "anomaly-detection",
    "rule": "rule-reasoning",
    "disposition": "disposition-execution",
}

_SUBAGENT_TOOL_ALLOWLIST = {"skill_view", "skills_list", "terminal"}


def resolve_subagent(name: str) -> SubagentSpec:
    canonical = _ALIASES.get(name, name)
    try:
        return _SPECS[canonical]
    except KeyError as exc:
        raise ValueError(f"Unknown subagent: {name}") from exc


def known_subagent_names() -> tuple[str, ...]:
    return tuple((*_SPECS.keys(), *_ALIASES.keys()))


def prepare_result_target(session_dir: str | Path, result_file: str) -> Path:
    """Remove only this stage's prior output before a new invocation."""
    root = Path(session_dir).resolve()
    target = (root / result_file).resolve()
    if target.parent != root:
        raise ValueError(f"Invalid result filename: {result_file}")
    target.unlink(missing_ok=True)
    return target


def filter_subagent_tools(tools: Iterable[dict]) -> list[dict]:
    return [
        tool
        for tool in tools
        if isinstance(tool, dict)
        and (tool.get("function") or {}).get("name") in _SUBAGENT_TOOL_ALLOWLIST
    ]

