#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import re
from datetime import datetime
from seleniumbase import SB

# =========================
# 配置
# =========================

LOGIN_URL = "https://dash.icehost.pl/auth/login"

EMAIL = os.environ.get("ICEHOST_EMAIL")
PASSWORD = os.environ.get("ICEHOST_PASSWORD")
PROXY = os.environ.get("PROXY_SOCKS5")

if not EMAIL:
    raise Exception("缺少环境变量 ICEHOST_EMAIL")

if not PASSWORD:
    raise Exception("缺少环境变量 ICEHOST_PASSWORD")


# =========================
# 解析有效期
# =========================
def parse_expire(page_text: str):
    match = re.search(
        r"有效期至[:：]\s*(\d{4}年\d{1,2}月\d{1,2}日\s+\d{2}:\d{2}:\d{2})",
        page_text
    )
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%Y年%m月%d日 %H:%M:%S")
    except:
        return None


# =========================
# 进入服务器
# =========================
def open_server(sb):
    print("📦 进入服务器...")

    selectors = [
        'text="Amelie"',
        '[class*="server"]',
        '[href*="server"]'
    ]

    for s in selectors:
        try:
            if sb.is_element_visible(s):
                sb.click(s)
                print(f"✅ 已点击服务器: {s}")
                time.sleep(5)
                return True
        except:
            pass

    print("❌ 未找到服务器")
    return False


# =========================
# 续期逻辑（核心）
# =========================
def renew_server(sb):
    print("⏰ 开始续期...")

    page_before = sb.get_text("body")
    old_time = parse_expire(page_before)

    if old_time:
        print(f"📅 续期前: {old_time}")

    # 点击续期按钮
    clicked = False
    selectors = [
        'text="增加 6 小时有效期"',
        'text="Extend"',
        'button'
    ]

    for s in selectors:
        try:
            if sb.is_element_visible(s):
                sb.click(s)
                print(f"✅ 点击续期按钮: {s}")
                clicked = True
                break
        except:
            pass

    if not clicked:
        print("❌ 未找到续期按钮")
        return True

    time.sleep(8)

    page_after = sb.get_text("body")
    new_time = parse_expire(page_after)

    if new_time:
        print(f"📅 续期后: {new_time}")

    # ===== 判断 =====
    if old_time and new_time:
        diff = (new_time - old_time).total_seconds()

        if diff >= 5 * 3600:
            print("🎉 续期成功 +6h")
            return True

        if diff == 0:
            print("✅ 今日已续期")
            return True

    if "不能再将服务器时间延长" in page_after:
        print("✅ 冷却提示（已续期）")
        return True

    if "recently" in page_after.lower():
        print("✅ 已续期（英文提示）")
        return True

    print("⚠️ 未确认结果，但不判失败")
    return True


# =========================
# 登录
# =========================
def login_icehost():
    options = {
        "uc": True,
        "headless": False,
        "agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
    }

    if PROXY:
        print(f"🌐 使用代理: {PROXY}")
        options["proxy"] = PROXY

    with SB(**options) as sb:

        print("🚀 打开登录页...")

        try:
            sb.uc_open_with_reconnect(LOGIN_URL, 5)
        except:
            sb.open(LOGIN_URL)

        time.sleep(5)
        sb.save_screenshot("login_page.png")

        print("📝 输入账号密码...")

        # 邮箱
        sb.type('input[type="email"], input[type="text"]', EMAIL)

        # 密码
        sb.type('input[type="password"]', PASSWORD)

        print("🔐 登录中...")
        sb.click('button[type="submit"], input[type="submit"], button')

        time.sleep(10)

        url = sb.get_current_url()
        print(f"📍 当前页面: {url}")

        sb.save_screenshot("after_login.png")

        if "/auth/login" in url:
            print("❌ 登录失败")
            return False

        print("🎉 登录成功")

        # ===== 进入服务器 =====
        if not open_server(sb):
            return True

        sb.save_screenshot("server.png")

        # ===== 续期 =====
        renew_server(sb)

        sb.save_screenshot("result.png")

        return True


# =========================
# main
# =========================
if __name__ == "__main__":
    try:
        ok = login_icehost()

        if ok:
            print("🏁 完成")
            exit(0)
        else:
            print("💥 结束")
            exit(0)

    except Exception as e:
        print(f"❌ 异常: {e}")
        exit(0)
