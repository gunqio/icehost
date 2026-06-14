#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
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


def parse_expiry_date(page_text):
    patterns = [
        r'有效期至[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{1,2}):(\d{1,2})',
        r'有效期至[：:]\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{1,2}):(\d{1,2})',
        r'Expires?[：:]\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{1,2}):(\d{1,2})',
        r'Ważność do[：:]\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{1,2}):(\d{1,2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, page_text)
        if match:
            year, month, day, hour, minute, second = map(int, match.groups())
            if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                return datetime(year, month, day, hour, minute, second)
    return None


def renew_server(sb):
    print("\n🔄 开始执行续期操作...")
    time.sleep(3)

    # ---------- 1. 确保在详情页 ----------
    current_url = sb.get_current_url()
    if "/server/" not in current_url:
        print("📍 进入服务器详情页...")
        try:
            show_btn = sb.find_element('//*[contains(text(), "POKAŻ MOJE SERWERY")]', timeout=3)
            if show_btn.is_displayed():
                sb.execute_script("arguments[0].scrollIntoView(true);", show_btn)
                time.sleep(0.5)
                show_btn.click()
                print("✅ 点击了'POKAŻ MOJE SERWERY'")
                time.sleep(2)
        except:
            print("⚠️ 未找到'POKAŻ MOJE SERWERY'，可能已展开")

        clicked = False
        server_texts = [
            "free-servers-4.icehost.pl:30159",
            "free-servers-4.icehost.pl",
            "Amelie Serwer testowy"
        ]
        for text in server_texts:
            try:
                elem = sb.find_element(f'//*[contains(text(), "{text}")]', timeout=3)
                if elem:
                    sb.execute_script("arguments[0].scrollIntoView(true);", elem)
                    time.sleep(0.5)
                    elem.click()
                    clicked = True
                    print(f"✅ 点击服务器条目: {text}")
                    break
            except:
                continue

        if not clicked:
            print("❌ 未找到服务器条目")
            sb.save_screenshot("no_server_entry.png")
            return False
        time.sleep(5)

    # ---------- 2. 等待有效期出现 ----------
    print("⏳ 等待有效期信息加载...")
    for attempt in range(10):
        page_source = sb.get_page_source()
        if "有效期至" in page_source or "Expires" in page_source:
            print("✅ 有效期信息已加载")
            break
        time.sleep(1)
    else:
        print("⚠️ 未检测到有效期信息，但继续执行")
        sb.save_screenshot("no_expiry_info.png")

    # ---------- 3. 点击续期按钮 ----------
    print("🔍 查找续期按钮...")
    renew_texts = [
        "增加 6 小时有效期",
        "Add 6 hours",
        "Dodaj 6 godzin",
        "Przedłuż o 6 godzin",
        "+6 godzin",
        "Extend by 6 hours"
    ]

    renew_clicked = False
    for text in renew_texts:
        try:
            xpath = f'//*[contains(text(), "{text}")]'
            elements = sb.find_elements(xpath)
            if elements:
                print(f"✅ 找到续期按钮: {text}")
                sb.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                time.sleep(1)
                elements[0].click()
                renew_clicked = True
                print("🔘 已点击续期按钮")
                time.sleep(3)
                try:
                    alert = sb.driver.switch_to.alert
                    print(f"📢 弹窗: {alert.text}")
                    alert.accept()
                except:
                    try:
                        confirm = sb.find_element('button:contains("确认"), button:contains("OK"), button:contains("Tak")', timeout=2)
                        confirm.click()
                        print("✅ 确认了续期")
                    except:
                        pass
                break
        except Exception as e:
            print(f"尝试'{text}'失败: {e}")

    if not renew_clicked:
        print("❌ 未找到续期按钮")
        sb.save_screenshot("no_renew_button.png")
        return False

    # ---------- 4. 等待并检查结果 ----------
    print("⏳ 等待续期结果...")
    time.sleep(3)
    sb.refresh()
    time.sleep(5)

    page_after = sb.get_page_source()
    sb.save_screenshot("after_renew.png")

    # 检查成功信息
    if "成功您已延长" in page_after or ("成功" in page_after and "延长" in page_after):
        print("🎉 续期成功！服务器有效期已延长6小时")
        return True
    # 检查频率限制错误
    elif "您不能再将服务器时间延长" in page_after or "cannot extend" in page_after.lower():
        print("ℹ️ 服务器提示最近已续期过，无需再次延长（视为成功）")
        return True
    else:
        print("⚠️ 未检测到成功或禁止提示，续期可能未生效")
        # 还可以尝试对比有效期，但为了简便，返回失败以便人工介入
        return False


def login_icehost():
    options = {
        "uc": True,
        "headless2": True,
        "headless": True,
        "agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
    }
    if PROXY:
        print(f"🌐 使用代理: {PROXY}")
        options["proxy"] = PROXY

    print("🚀 启动浏览器...")
    with SB(**options) as sb:
        print("🚀 打开 IceHost 登录页...")
        try:
            sb.uc_open_with_reconnect(LOGIN_URL, 5)
        except:
            sb.open(LOGIN_URL)
        time.sleep(5)
        sb.save_screenshot("login_page.png")

        print("📝 填写账号密码...")
        email_selectors = [
            'input[name="email"]', 'input[name="username"]',
            'input[type="email"]', 'input[placeholder*="mail" i]',
            'input[placeholder*="email" i]', 'input[placeholder*="Adres" i]',
            'input[type="text"]', 'input:first-of-type'
        ]
        email_ok = False
        for sel in email_selectors:
            try:
                if sb.is_element_visible(sel):
                    sb.type(sel, EMAIL)
                    email_ok = True
                    print(f"✅ 找到邮箱框: {sel}")
                    break
            except:
                pass
        if not email_ok:
            sb.type(sb.find_element('input'), EMAIL)
            print("✅ 使用第一个输入框")

        pwd_selectors = [
            'input[type="password"]', 'input[name="password"]',
            'input[placeholder*="hasło" i]'
        ]
        pwd_ok = False
        for sel in pwd_selectors:
            try:
                if sb.is_element_visible(sel):
                    sb.type(sel, PASSWORD)
                    pwd_ok = True
                    print(f"✅ 找到密码框: {sel}")
                    break
            except:
                pass
        if not pwd_ok:
            sb.type(sb.find_elements('input')[1], PASSWORD)
            print("✅ 使用第二个输入框")

        print("🔐 提交登录...")
        btn_selectors = [
            'button[type="submit"]',
            'button:contains("Załoguj się")',
            'button:contains("Login")',
            'button'
        ]
        clicked = False
        for sel in btn_selectors:
            try:
                if sb.is_element_visible(sel):
                    sb.click(sel)
                    clicked = True
                    print(f"✅ 点击登录按钮: {sel}")
                    break
            except:
                pass
        if not clicked:
            sb.press_enter('input[type="password"]')
            print("✅ 使用回车提交")

        print("⏳ 等待登录...")
        time.sleep(8)

        page_source = sb.get_page_source()
        current_url = sb.get_current_url()
        print(f"📍 当前页面: {current_url}")

        success_keywords = ["Serwery", "账户余额", "服务器", "Konto", "余额"]
        login_ok = any(kw in page_source for kw in success_keywords) or ("/auth/login" not in current_url)

        sb.save_screenshot("after_login.png")
        if not login_ok:
            print("❌ 登录失败")
            with open("login_failed.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            return False

        print("🎉 登录成功！")
        return renew_server(sb)


if __name__ == "__main__":
    try:
        result = login_icehost()
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
