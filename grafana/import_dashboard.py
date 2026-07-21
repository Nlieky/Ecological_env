#!/usr/bin/env python3
"""把 stream_01 dashboard 导入 Grafana 并授予 Viewer 角色查看权限（供匿名 iframe 嵌入）。

幂等，可重复执行。前提：Grafana 在跑、admin 账号可用。
用法：
    python grafana/import_dashboard.py
    GRAFANA_URL=http://localhost:3000 GRAFANA_AUTH=admin:admin python grafana/import_dashboard.py

为什么需要授 Viewer 权限：默认情况下 API 导入的 dashboard 匿名(Viewer)无 dashboards:read，
iframe 嵌入会 403。显式给 Viewer 角色 View 权限后，前端 /grafana 才能 iframe 渲染。
"""
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

GRAFANA = os.getenv("GRAFANA_URL", "http://localhost:3000")
AUTH = os.getenv("GRAFANA_AUTH", "admin:admin")
UID = "wastewater-fixed"
DASH_FILE = Path(__file__).parent / "dashboards" / "stream_01.json"


def _req(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    token = base64.b64encode(AUTH.encode()).decode()
    req = urllib.request.Request(
        GRAFANA + path, data=data, method=method,
        headers={"Content-Type": "application/json", "Authorization": "Basic " + token},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def main() -> None:
    dash = json.loads(DASH_FILE.read_text(encoding="utf-8"))
    s, _ = _req("POST", "/api/dashboards/db", {"dashboard": dash, "folderId": 0, "overwrite": True})
    print(f"import stream_01 (uid={UID}): HTTP {s}")
    # Viewer 角色 View(1) + admin Admin(4) → 匿名(Viewer)可读，iframe 可嵌入
    s, _ = _req("POST", f"/api/dashboards/uid/{UID}/permissions",
                {"items": [{"role": "Viewer", "permission": 1}, {"userId": 1, "permission": 4}]})
    print(f"grant Viewer View permission: HTTP {s}")
    print("done — 前端 /grafana 现在可匿名 iframe 嵌入 stream_01。")


if __name__ == "__main__":
    main()
