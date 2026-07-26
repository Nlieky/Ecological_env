#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""用 Playwright 打开监测大屏截图,验证前端展示了 InfluxDB 的 2026 真实数据。

前置:后端在 8000(读 InfluxDB)、vite dev 在 5173(proxy /api -> 8000)。
运行: ecological_env\Scripts\python.exe scripts\screenshot_dashboard.py
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:5173/dashboard"
OUT = Path(__file__).resolve().parent / "dashboard_screenshot.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("console", lambda m: errors.append(f"[console.{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))

    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3500)  # 等 echarts/数据渲染
    page.screenshot(path=str(OUT), full_page=True)

    body_text = page.inner_text("body")
    browser.close()

print("screenshot ->", OUT)
print("--- console/page errors (前10条) ---")
for e in errors[:10]:
    print(e)
print("--- 页面是否含 '2026' ---", "2026" in body_text)
print("--- body 文本片段(前 1000 字) ---")
print(body_text[:1000])
