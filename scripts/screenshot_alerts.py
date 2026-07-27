#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Playwright 截图告警中心(/alerts),验证 AlertCenterView 渲染。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:5173/alerts"
OUT = Path(__file__).resolve().parent / "alerts_screenshot.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(OUT), full_page=True)
    body = page.inner_text("body")
    browser.close()

print("screenshot ->", OUT)
print("console_errors:", errors[:5])
print("has_alert_center:", "告警中心" in body)
print("has_pending_label:", "待处理" in body)
print("shows_event_or_empty:", "evt_001" in body or "cod_high" in body or "暂无待处理" in body)
