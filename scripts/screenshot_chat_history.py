#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 G:点历史会话后,聊天区还原该会话的 messages。"""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:5173/chat"
OUT = Path(__file__).resolve().parent / "chat_history_screenshot.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2500)  # 等 conversations 加载

    si = page.locator(".si")
    n = si.count()
    first_text = si.first.inner_text().replace("\n", " ")[:60] if n else "(无历史会话)"
    before_body = page.inner_text("body")
    if n:
        si.first.click()
        page.wait_for_timeout(2500)  # 等 openConversation 还原 messages
    page.screenshot(path=str(OUT), full_page=True)
    after_body = page.inner_text("body")
    browser.close()

print("screenshot ->", OUT)
print("errors:", errors[:5])
print("history_count:", n)
print("first_conv:", first_text)
# 还原成功:点击后聊天区出现该会话的历史消息内容
print("chat_area_gained_messages:", len(after_body) > len(before_body) + 20)
print("has_chat_content:", any(k in after_body for k in ["2026", "COD", "进水", "氨氮", "您好", "你好", "需要", "异常", "请问"]))
