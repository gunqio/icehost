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


def renew_server(sb):
    """执行服务器续期操作 - 进入服务器详情页后点击续期，并验证是否真的成功"""
    print("\n🔄 开始检查并续期服务器...")
    time.sleep(3)

    current_url = sb.get_current_url()
    if "/server/" in current_url:
        print("📍 已在服务器详情页")
    else:
        print("📍 当前在仪表盘首页，需要进入服务器详情页")

        # 尝试展开服务器列表（即使找不到按钮也可能已展开）
        try:
            show_btn = sb.find_element('//*[contains(text(), "POKAŻ MOJE SERWERY")]', timeout=3)
            if show_btn.is_displayed():
                sb.execute_script("arguments[0].scrollIntoView(true);", show_btn)
                time.sleep(0.5)
                show_btn.click()
                print("✅ 点击了'POKAŻ MOJE SERWERY'")
                time.sleep(2)
        except:
            print("⚠️ 未找到'POKAŻ MOJE SERWERY'按钮，可能已展开")

        # 点击服务器条目
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
        print(f"📍 跳转后URL: {sb.get_current_url()}")

    # 当前在详情页
    sb.save_screenshot("server_detail_page.png")
    print("🔍 查找续期按钮...")

    # 先检查是否已有错误提示（比如刚续期过）
    page_source_before = sb.get_page_source()
    if "您不能再将服务器时间延长" in page_source_before or "cannot extend" in page_source_before.lower():
        print("⚠️ 检测到提示：您最近已续期过，无法再次延长")
        # 但仍尝试找按钮，若按钮存在且可点，则尝试点击（也许服务器允许）
        # 但根据业务逻辑，大概率点完还是失败，这里直接返回成功？不，应返回失败（因为实际未延长）
        # 但任务可能已完成（因为已经续期过），视为成功？取决于需求。这里假设只要没有真正执行延长，就算失败
        # 为保险，继续尝试点击，如果点击后出现同样的错误，则最终失败；若意外成功则成功。
        pass

    # 续期按钮文本
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

                # 处理可能的确认弹窗
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
        sb.save_screenshot("renew_button_not_found.png")
        return False

    # 等待页面更新，检查续期是否成功
    time.sleep(2)
    sb.refresh()
    time.sleep(3)

    # 检查是否出现错误提示
    page_source_after = sb.get_page_source()
    sb.save_screenshot("after_renew_attempt.png")

    error_keywords = [
        "您不能再将服务器时间延长",
        "cannot extend",
        "already extended",
        "błąd",  # 波兰语错误
        "nie można przedłużyć"
    ]

    success_keywords = [
        "有效期至",
        "Expires",
        "nowa data ważności"
    ]

    # 判断续期是否成功
    has_error = any(kw in page_source_after for kw in error_keywords)
    has_success = any(kw in page_source_after for kw in success_keywords)

    if has_error:
        print("❌ 续期失败：服务器拒绝了延长请求（可能是频率限制）")
        # 尝试提取具体错误信息
        try:
            error_elem = sb.find_element('//*[contains(@class, "error") or contains(@class, "alert")]', timeout=2)
            print(f"错误详情: {error_elem.text}")
        except:
            pass
        return False
    elif has_success or "06:09:49" not in page_source_after:  # 简单判断截止日期是否有变化
        print("✅ 续期成功！")
        return True
    else:
        print("⚠️ 续期状态不明，请检查截图")
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
        # 邮箱/用户名
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

        # 密码
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

        # 判断登录成功
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
