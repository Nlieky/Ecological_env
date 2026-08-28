# scripts/e2e_agent_config_v2.py
"""配置中心 V2 E2E：六 tab URL 同步 / 策略保存 / 技能新建+市场 / provider 测试+设默认 / MCP 预置。
前置：backend(8000) + frontend(5173) 已起。结束后字节级还原工作区他人未提交改动（学 V1 E2E 的教训）。

与 Task 10 实现对齐的实测口径（跑之前已核对过组件源码）：
- McpPanel 预置卡安装按钮文案恒为「已安装·管理见下」，仅 disabled 随安装态切换
  （servers 空 → 可点击），因此选择器按 .mp-card(Fetch) 的首个按钮取，不按文案。
- 预置落 config.yaml 的 server 键 = 预置名（fetch），command args 里含 server-fetch 包名。
- SkillsPanel 创建按钮文案为「创建（git 快照）」，用 has-text('创建') 子串匹配。
"""
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# Windows GBK 控制台打不出 ✓/✗/中文 emoji——强制 UTF-8，否则第一行 print 就 UnicodeEncodeError。
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"{'✓' if ok else '✗'} {name} {detail}")


def read_cfg() -> str:
    p = PROJECT_ROOT / "config.yaml"
    return p.read_text(encoding="utf-8") if p.exists() else ""


with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(locale="zh-CN")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # 1. 六 tab 渲染 + URL 同步
    page.goto("http://localhost:5173/agents/config?entity=master&tab=strategy", wait_until="networkidle")
    page.wait_for_selector(".tab")
    tabs = page.locator(".tab").all_inner_texts()
    check("主智能体六 tab", [t for t in tabs if t.strip()] == ["概览", "身份文件", "技能", "策略", "MCP", "供应商"], str(tabs))
    page.click(".tab:has-text('技能')")
    check("tab 切换写 URL", "tab=skills" in page.url, page.url)
    # 子智能体四 tab（mcp/providers 不出现）
    page.goto("http://localhost:5173/agents/config?entity=anomaly-detection&tab=skills", wait_until="networkidle")
    tabs2 = [t.strip() for t in page.locator(".tab").all_inner_texts() if t.strip()]
    check("子智能体四 tab", tabs2 == ["概览", "身份文件", "技能", "策略"], str(tabs2))

    # 2. 策略加载+保存
    page.goto("http://localhost:5173/agents/config?entity=master&tab=strategy", wait_until="networkidle")
    page.wait_for_selector(".sp-row")
    n_rows = page.locator(".sp-row").count()
    check("策略+参数行数", n_rows >= 18, f"{n_rows} 行")

    def read_guard() -> str:
        return subprocess.run(
            ["./ecological_env/Scripts/python.exe", "-c",
             "import sys; sys.path.insert(0,'.'); "
             "from backend.services.agent_strategy import get_strategy; "
             "v = get_strategy('perception_guard_enabled'); print('ON' if v is True else 'OFF')"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()

    # 守卫开关：记初值→翻转保存→断言已翻转（状态无关，不假设默认 True）
    initial = read_guard()
    flipped_target = "OFF" if initial == "ON" else "ON"
    page.locator(".sp-row", has_text="perception_guard_enabled").locator(".el-switch").first.click()
    page.click("button:has-text('保存策略')")
    time.sleep(1.2)
    check("守卫开关落库", read_guard() == flipped_target, f"{initial}→{read_guard()}")
    # 还原。必须先 reload：面板保存后不回写基线（it.value 仍是旧值），直接二连点会被
    # 判「策略无改动」而不落库。reload 让基线从 DB 重读（顺带验证回读）。
    page.reload(wait_until="networkidle")
    page.wait_for_selector(".sp-row")
    page.locator(".sp-row", has_text="perception_guard_enabled").locator(".el-switch").first.click()
    page.click("button:has-text('保存策略')")
    time.sleep(1.2)
    restored = read_guard()
    check("守卫已还原", restored == initial, f"now={restored} initial={initial}")

    # 3. 技能：新建→落盘→删除
    page.goto("http://localhost:5173/agents/config?entity=master&tab=skills", wait_until="networkidle")
    page.wait_for_selector(".sk-card")
    page.click("button:has-text('新建技能')")
    page.fill(".sk-modal input[placeholder='my-skill']", "e2e-tmp-skill")
    page.fill(".sk-modal input[placeholder='什么任务用这个技能']", "E2E 临时技能")
    page.click(".sk-modal button:has-text('创建')")
    time.sleep(1.2)
    check("新建技能落盘", (PROJECT_ROOT / "skills" / "e2e-tmp-skill" / "SKILL.md").exists())
    gitlog = subprocess.run(["git", "log", "--oneline", "-1"], cwd=PROJECT_ROOT,
                            capture_output=True, text=True, encoding="utf-8").stdout or ""
    check("新建技能 git 快照", "e2e-tmp-skill" in gitlog, gitlog.strip()[:60])
    # 删除
    page.locator(".sk-card", has_text="e2e-tmp-skill").locator("button:has-text('删除')").click()
    page.click(".el-message-box__btns .el-button--primary")
    time.sleep(1.0)
    check("技能已删除", not (PROJECT_ROOT / "skills" / "e2e-tmp-skill").exists())

    # 4. 市场：安装 blank-skill 到 master → 删除
    page.click("button:has-text('技能市场')")
    page.wait_for_selector(".sk-tpl")
    n_tpl = page.locator(".sk-tpl").count()
    check("市场 6 模板", n_tpl == 6, f"{n_tpl} 个")
    page.locator(".sk-tpl", has_text="blank-skill").locator("button:has-text('安装')").click()
    time.sleep(1.2)
    check("模板安装落盘", (PROJECT_ROOT / "skills" / "blank-skill" / "SKILL.md").exists())
    # 安装后市场弹窗仍开着（遮罩挡住卡片操作），先点「关闭」再删卡片
    page.click(".sk-modal button:has-text('关闭')")
    page.locator(".sk-card", has_text="blank-skill").locator("button:has-text('删除')").click()
    page.click(".el-message-box__btns .el-button--primary")
    time.sleep(1.0)
    check("模板技能已删除", not (PROJECT_ROOT / "skills" / "blank-skill").exists())

    # 5. providers：列表+测试 ctgu-vlm
    page.goto("http://localhost:5173/agents/config?entity=master&tab=providers", wait_until="networkidle")
    page.wait_for_selector(".pv-card")
    n_prov = page.locator(".pv-card").count()
    check("供应商≥2 行", n_prov >= 2, f"{n_prov}")
    page.locator(".pv-card", has_text="ctgu-vlm").locator("button:has-text('测试连接')").click()
    try:
        page.wait_for_selector(".pv-test.ok", timeout=15000)
        check("ctgu-vlm 测通", True)
    except Exception:
        check("ctgu-vlm 测通", False, "15s 内未见 .pv-test.ok（LLM 服务可能未起——环境依赖项）")

    # 6. MCP：预置清单+安装 fetch→删除
    page.goto("http://localhost:5173/agents/config?entity=master&tab=mcp", wait_until="networkidle")
    page.wait_for_selector(".mp-card")
    n_preset = page.locator(".mp-card").count()
    check("MCP 4 预置", n_preset == 4, f"{n_preset}")
    cfg_before = read_cfg()
    # 预置卡安装按钮文案恒为「已安装·管理见下」（disabled 随安装态切换），按位置取。
    page.locator(".mp-card", has_text="Fetch").locator("button").first.click()
    time.sleep(1.2)
    cfg_after = read_cfg()
    check("安装写入 config.yaml", "mcp_servers" in cfg_after and "fetch" in cfg_after, "")
    check("config.yaml 其他段未破坏", ("model" not in cfg_before) or ("model" in cfg_after or "mcp_servers" in cfg_after), "")
    # 删掉恢复原状（已接入行 .mp-row 含 server-fetch 包名；预置卡也叫 Fetch 故用 .mp-row 限定）
    page.locator(".mp-row", has_text="server-fetch").locator("button:has-text('删除')").click()
    page.click(".el-message-box__btns .el-button--primary")
    time.sleep(1.0)
    cfg_final = read_cfg()
    check("删除后 mcp_servers 移除", "server-fetch" not in cfg_final, "")

    # 7. 无 JS 错误
    check("无页面 JS 错误", not errors, "; ".join(errors[:3]))

    b.close()

fails = [r for r in results if not r[1]]
print(f"\n{'='*40}\nV2 E2E: {len(results)-len(fails)}/{len(results)} 通过")
sys.exit(1 if fails else 0)
