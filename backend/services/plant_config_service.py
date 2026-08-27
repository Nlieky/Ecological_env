# backend/services/plant_config_service.py
"""plant-hierarchy.yaml 管理服务：结构化读写 + 校验 + 原子落盘。

yaml 顶层四段：hierarchy(市→区→厂[]) / report_name_map / plant_configs / plant_aliases。
_RESERVED 与 shared/data/discover_plants.py 保持一致——新厂自动发现不被配置段干扰。
"""
import os
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
YAML_PATH = PROJECT_ROOT / "shared" / "data" / "plant-hierarchy.yaml"

_RESERVED = {"report_name_map", "plant_configs", "plant_aliases"}

# 兜底别名（yaml 无段时的默认；与 InfluxDB plant_id 一致）
_BUILTIN_ALIASES = {
    "金桥": "当阳市金桥污水处理厂一期",
    "当阳市金桥污水处理厂一期": "当阳市金桥污水处理厂一期",
    "洗舱站": "洗舱站污水排放口",
    "洗舱站污水排放口": "洗舱站污水排放口",
}


def load_plant_config() -> dict:
    if not YAML_PATH.exists():
        return {"hierarchy": {}, "report_name_map": {}, "plant_configs": {}, "plant_aliases": {}}
    with open(YAML_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {
        "hierarchy": {k: v for k, v in raw.items() if k not in _RESERVED},
        "report_name_map": raw.get("report_name_map") or {},
        "plant_configs": raw.get("plant_configs") or {},
        "plant_aliases": raw.get("plant_aliases") or {},
    }


def save_section(section: str, value) -> None:
    """改单段（value=None 删除段）。读-改-写整份 yaml。"""
    with open(YAML_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if value is None:
        raw.pop(section, None)
    else:
        raw[section] = value
    _atomic_dump(raw)


def save_config(data: dict) -> dict:
    """整份保存（页面保存按钮）：合并四段，保留未知段不动。"""
    with open(YAML_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    for k, v in data.items():
        if v is None:
            raw.pop(k, None)
        else:
            raw[k] = v
    # hierarchy 是拼出来的（非保留键集合），逐键覆盖：先删旧层级键再加新的
    for k in [k for k in raw if k not in _RESERVED]:
        raw.pop(k)
    raw.update(data.get("hierarchy") or {})
    _atomic_dump(raw)
    _git_snapshot()
    return load_plant_config()


def validate_config(data: dict) -> list:
    """返回错误列表（空=通过）。规则：别名/映射值必须存在于层级中的厂集合。"""
    errs = []
    plants = set()
    for city, zones in (data.get("hierarchy") or {}).items():
        if not isinstance(zones, dict):
            errs.append(f"层级[{city}]格式错误：应为 市→厂区→厂列表")
            continue
        for zone, plist in zones.items():
            if not isinstance(plist, list):
                errs.append(f"层级[{city}.{zone}]格式错误：应为厂列表")
                continue
            plants.update(plist)
    for alias, pid in (data.get("plant_aliases") or {}).items():
        if pid not in plants:
            errs.append(f"别名「{alias}」指向不存在的厂「{pid}」（须先在层级中添加）")
    for fname, pid in (data.get("report_name_map") or {}).items():
        if pid not in plants:
            errs.append(f"报表映射「{fname}」指向不存在的厂「{pid}」")
    return errs


def resolve_alias(alias_text: str):
    """任务文本→plant_id。yaml 段优先（含自身全称映射），无段/无命中走内置。"""
    cfg = load_plant_config()
    aliases = cfg.get("plant_aliases") or {}
    merged = dict(_BUILTIN_ALIASES)
    merged.update(aliases)
    for alias, pid in merged.items():
        if alias in alias_text:
            return pid
    return None


def _atomic_dump(raw: dict) -> None:
    tmp = YAML_PATH.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(raw, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    os.replace(tmp, YAML_PATH)


def _git_snapshot() -> None:
    """yaml 保存即 git 快照（只 add 本文件；失败静默——校验已过,落盘成功不因 git 挂掉而报错）。"""
    import subprocess
    rel = YAML_PATH.relative_to(PROJECT_ROOT).as_posix()
    try:
        subprocess.run(["git", "add", "--", rel], cwd=PROJECT_ROOT, capture_output=True, timeout=30)
        subprocess.run(["git", "commit", "-m", f"config(web): {rel} — 厂区配置在线编辑",
                        "--", rel], cwd=PROJECT_ROOT, capture_output=True, timeout=30)
    except Exception:
        pass
