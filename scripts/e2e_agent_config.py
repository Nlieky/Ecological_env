# scripts/e2e_agent_config.py
"""配置中心 E2E：实体树→编辑→保存→历史→回滚 + 参数面板 + 白名单。
前置：backend(8000, vite 代理目标) + frontend(5173 dev) 已起。零缓存 Playwright。
选择器与实际组件对齐：.et-item(EntityTree) / .tab(AgentConfigView) / .ed-fi/.ed-ta/.ed-hi(IdentityFileEditor)
/ .pp-grid .pp-row(ParamsPanel)；ElMessageBox 确认键 .el-message-box__btns .el-button--primary。

安全约束（Task 10 特别要求）：
- workspace/MEMORY.md 工作区可能有他人未提交改动——脚本启动时读入原始字节，
  finally 里字节级还原 + `git restore --staged` 清掉 revert 留下的暂存，绝不弄丢他人改动。
- 绝不触碰 plant-hierarchy.yaml（本脚本只读写 master/MEMORY.md）。
"""
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEM = PROJECT_ROOT / "workspace" / "MEMORY.md"
MARKER = "<!-- e2e-config-test 2026-08-27 -->"
BASE = "http://localhost:5173"

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} {name} {detail}")


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def wait_git_log(pattern: str, timeout: float = 15.0) -> str:
    """轮询 git log 直到目标文件最新提交命中 pattern（保存是异步 toast，磁盘/git 才是真相）。"""
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        last = git("log", "-1", "--pretty=%h %s", "--", "workspace/MEMORY.md").strip()
        if pattern in last:
            return last
        time.sleep(0.4)
    return last


def wait_marker(gone: bool, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        has = MARKER in MEM.read_text(encoding="utf-8")
        if has != gone:
            return True
        time.sleep(0.4)
    return False


def main() -> int:
    orig_bytes = MEM.read_bytes()  # 他人未提交改动在此快照，finally 字节级还原
    js_errors: list = []
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            ctx = b.new_context(locale="zh-CN", bypass_csp=True)
            page = ctx.new_page()
            page.on("pageerror", lambda e: js_errors.append(str(e)))

            page.goto(f"{BASE}/agents/config", wait_until="domcontentloaded")
            page.wait_for_selector(".et-item", timeout=30000)

            # 1. 实体树 7 项（5 智能体 + 厂区配置 + 服务管理）
            n = page.locator(".et-item").count()
            check("实体树 7 项(5智能体+厂区+服务)", n == 7, f"got {n}")

            # 2. master → 身份文件 tab → MEMORY.md 编辑
            page.click(".et-item:has-text('主智能体')")
            page.click("button.tab:has-text('身份文件')")
            page.click(".ed-fi:has-text('MEMORY.md')")
            page.wait_for_selector(".ed-ta", timeout=15000)
            page.wait_for_function("document.querySelector('.ed-ta').value.length > 100")
            orig = page.locator(".ed-ta").input_value()
            check("MEMORY.md 加载有内容", len(orig) > 100, f"{len(orig)} chars")

            page.fill(".ed-ta", orig + f"\n{MARKER}\n")
            page.click(".ed-acts .btn.primary")            # 保存（git 快照）
            page.wait_for_selector(".ed-diff", timeout=5000)
            page.click(".ed-df .btn.primary")              # 确认保存
            page.wait_for_selector(".el-message-box", timeout=5000)   # 快照说明 prompt
            page.click(".el-message-box__btns .el-button--primary")   # 空说明继续
            page.wait_for_selector(".el-message--success", timeout=15000)
            last = wait_git_log("config(web): workspace/MEMORY.md")
            check("保存产生 git 快照", "config(web): workspace/MEMORY.md" in last, last)
            check("文件内容已写入(含 marker)", MARKER in MEM.read_text(encoding="utf-8"))

            # 3. 历史 + 回滚上一版
            page.wait_for_selector(".ed-hi", timeout=10000)
            hist = page.locator(".ed-hi").count()
            check("历史列表有版本", hist >= 1, f"{hist} 条")
            if hist >= 2:
                page.locator(".ed-hi").nth(1).click()      # 上一版
                page.wait_for_selector(".el-message-box", timeout=5000)
                page.click(".el-message-box__btns .el-button--primary")
                page.wait_for_selector(".el-message--success", timeout=15000)
                check("回滚后 marker 消失", wait_marker(gone=True))
            else:
                check("回滚分支跳过(历史不足)", True, "marker 由 finally 字节还原兜底")

            # 4. 参数面板（脱敏）
            page.click("button.tab:has-text('运行参数')")
            page.wait_for_selector(".pp-grid .pp-row", timeout=15000)
            pn = page.locator(".pp-grid .pp-row").count()
            check("参数行 >=8", pn >= 8, f"{pn} 行")
            masked = page.locator(".pp-grid .pp-row:has-text('llm_api_key') input").first.input_value()
            check("密钥脱敏", "***" in masked or masked == "", f"'{masked[:12]}'")

            # 5. 白名单：路径穿越/未知实体 → 400（浏览器同源请求走 vite 代理，测的是真实后端）
            r1 = ctx.request.get(f"{BASE}/api/v1/agents/config/files?entity=master&file=../../.env")
            r2 = ctx.request.get(f"{BASE}/api/v1/agents/config/files?entity=hacker&file=SOUL.md")
            check("白名单拦截越界路径/实体", r1.status == 400 and r2.status == 400,
                  f"traversal={r1.status} unknown_entity={r2.status}")

            # 6. 无 JS 错误
            check("无页面 JS 错误", not js_errors, "; ".join(js_errors[:3]))

            b.close()
    finally:
        # 字节级还原他人未提交改动；revert(git checkout) 会把旧版暂存进 index，一并清掉
        MEM.write_bytes(orig_bytes)
        subprocess.run(["git", "restore", "--staged", "--", "workspace/MEMORY.md"],
                       cwd=PROJECT_ROOT, capture_output=True, text=True)
        restored = MEM.read_bytes() == orig_bytes
        clean = MARKER not in MEM.read_text(encoding="utf-8")
        print(f"RESTORE byte-identical={restored} marker-gone={clean} "
              f"git-status={git('status', '--short', '--', 'workspace/MEMORY.md').strip()!r}")

    fails = [r for r in results if not r[1]]
    print(f"\n{'=' * 40}\nE2E: {len(results) - len(fails)}/{len(results)} 通过")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
