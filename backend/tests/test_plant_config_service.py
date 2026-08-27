# backend/tests/test_plant_config_service.py
"""plant_config_service 单测：读写往返 / 校验规则 / 别名解析（含 yaml 段）。"""
import shutil, sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def yaml_env(tmp_path, monkeypatch):
    shutil.copy(PROJECT_ROOT / "shared/data/plant-hierarchy.yaml",
                tmp_path / "plant-hierarchy.yaml")
    import backend.services.plant_config_service as pcs
    monkeypatch.setattr(pcs, "YAML_PATH", tmp_path / "plant-hierarchy.yaml")
    monkeypatch.setattr(pcs, "PROJECT_ROOT", tmp_path)
    return pcs


def test_load_full(yaml_env):
    data = yaml_env.load_plant_config()
    assert "hierarchy" in data and "report_name_map" in data and "plant_configs" in data
    assert "plant_aliases" in data  # 迁移后必有


def test_alias_resolution_prefers_yaml(yaml_env):
    # yaml 里的别名优先于内置默认
    assert yaml_env.resolve_alias("金桥") == "当阳市金桥污水处理厂一期"
    yaml_env.save_section("plant_aliases", {"测试别名": "当阳市金桥污水处理厂一期"})
    assert yaml_env.resolve_alias("测试别名") == "当阳市金桥污水处理厂一期"


def test_alias_fallback_to_builtin(yaml_env):
    # yaml 无 plant_aliases 段时用内置两厂（向后兼容）
    yaml_env.save_section("plant_aliases", None)  # 删除段
    assert yaml_env.resolve_alias("洗舱站") == "洗舱站污水排放口"


def test_validate_reports_errors(yaml_env):
    # 别名指向不存在的厂 → 错误
    errs = yaml_env.validate_config({"hierarchy": {"当阳市": {"城东厂区": ["X厂"]}},
                                     "plant_aliases": {"a": "不存在厂"},
                                     "report_name_map": {}, "plant_configs": {}})
    assert any("不存在" in e or "别名" in e for e in errs)


def test_roundtrip_preserves_hierarchy(yaml_env):
    data = yaml_env.load_plant_config()
    data["hierarchy"]["枝江市"]["新厂区"] = ["测试排放口"]
    yaml_env.save_config(data)
    re = yaml_env.load_plant_config()
    assert "测试排放口" in re["hierarchy"]["枝江市"]["新厂区"]
