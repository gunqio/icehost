#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
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
        print("🚀 打开 IceHost 登录页...")

        try:
            sb.uc_open_with_reconnect(LOGIN_URL, 5)
        except Exception:
            sb.open(LOGIN_URL)

        time.sleep(5)

        sb.save_screenshot("login_page.png")

        print("📝 填写账号密码...")

        # 邮箱输入框
        email_selectors = [
            'input[type="email"]',
            'input[placeholder*="mail"]',
            'input[placeholder*="Mail"]',
            'input[placeholder*="email"]',
            'input[placeholder*="Email"]',
            'input[type="text"]'
        ]

        email_ok = False

        for selector in email_selectors:
            try:
                if sb.is_element_visible(selector):
                    sb.type(selector, EMAIL)
                    email_ok = True
                    print(f"✅ 找到邮箱框: {selector}")
                    break
            except Exception:
                pass

        if not email_ok:
            raise Exception("未找到邮箱输入框")

        # 密码框
        sb.type('input[type="password"]', PASSWORD)

        print("🔐 提交登录...")

        # 登录按钮
        button_selectors = [
            'button[type="submit"]',
            'button',
            'input[type="submit"]'
        ]

        clicked = False

        for selector in button_selectors:
            try:
                if sb.is_element_visible(selector):
                    sb.click(selector)
                    clicked = True
                    print(f"✅ 点击登录按钮: {selector}")
                    break
            except Exception:
                pass

        if not clicked:
            raise Exception("未找到登录按钮")

        print("⏳ 等待登录完成...")
        time.sleep(10)

        current_url = sb.get_current_url()

        print(f"📍 当前页面: {current_url}")

        sb.save_screenshot("after_login.png")

        # 登录成功判断
        if "/auth/login" not in current_url:
            print("🎉 登录成功")
            return True

        # 再检查是否出现错误提示
        page_source = sb.get_page_source().lower()

        error_keywords = [
            "invalid",
            "incorrect",
            "wrong password",
            "failed",
            "error"
        ]

        if any(x in page_source for x in error_keywords):
            print("❌ 登录失败：账号或密码错误")
        else:
            print("⚠️ 仍停留在登录页")

        return False


if __name__ == "__main__":
    try:
        result = login_icehost()

        if result:
            print("🏁 任务完成")
            exit(0)
        else:
            print("💥 任务失败")
            exit(1)

    except Exception as e:
        print(f"❌ 异常: {e}")
        exit(1)
