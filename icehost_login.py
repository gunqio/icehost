#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
from datetime import datetime, timedelta
from seleniumbase import SB

# =========================
# 配置
# =========================

LOGIN_URL = "https://dash.icehost.pl/auth/login"

EMAIL = os.environ.get("ICEHOST_EMAIL")
PASSWORD = os.environ.get("ICEHOST_PASSWORD")
PROXY = os.environ.get("PROXY_SOCKS5")

# 续期阈值（小时）：剩余有效期大于此值则不续期
RENEW_THRESHOLD_HOURS = 5

if not EMAIL:
    raise Exception("缺少环境变量 ICEHOST_EMAIL")
if not PASSWORD:
    raise Exception("缺少环境变量 ICEHOST_PASSWORD")


def parse_expiry_date(page_text):
    """
    从页面文本中解析有效期至日期
    支持: "有效期至：2026年6月14日 06:09:49"
         "Expires: 2026-06-14 06:09:49"
         "Ważność do: 2026-06-14 06:09:49"
    返回 datetime 对象，未找到返回 None
    """
    patterns = [
        r'有效期至[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{1,2}):(\d{1,2})',
        r'Expires?[：:]\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{1,2}):(\d{1,2})',
        r'Ważność do[：:]\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{1,2}):(\d{1,2})',
        r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})'  # 宽松匹配
    ]
    for pattern in patterns:
        match = re.search(pattern, page_text)
        if match:
            year, month, day, hour, minute, second = map(int, match.groups())
            # 简单校验
            if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                return datetime(year, month, day, hour, minute, second)
    return None


def get_expiry_from_page(sb):
    """获取当前页面的有效期，重试几次"""
    for _ in range(3):
        page_source = sb.get_page_source()
        expiry = parse_expiry_date(page_source)
        if expiry:
            return expiry
        time.sleep(1)
    return None


def renew_server(sb):
    """执行服务器续期操作 - 进入详情页，检查有效期，必要时点击续期"""
    print("\n🔄 开始检查并续期服务器...")
    time.sleep(3)

    # ---------- 1. 确保在详情页 ----------
    current_url = sb.get_current_url()
    if "/server/" not in current_url:
        print("📍 当前在仪表盘首页，需要进入服务器详情页")
        # 展开服务器列表（如果按钮存在）
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

    # ---------- 2. 获取当前有效期 ----------
    sb.save_screenshot("server_detail_page.png")
    old_expiry = get_expiry_from_page(sb)
    if old_expiry:
        print(f"📅 当前服务器有效期至: {old_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
        remaining_hours = (old_expiry - datetime.now()).total_seconds() / 3600
        print(f"⏳ 距离到期剩余: {remaining_hours:.2f} 小时")
        if remaining_hours > RENEW_THRESHOLD_HOURS:
            print(f"✅ 剩余有效期充足（>{RENEW_THRESHOLD_HOURS}小时），无需续期")
            return True
    else:
        print("⚠️ 未能解析有效期，将尝试续期")

    # ---------- 3. 查找并点击续期按钮 ----------
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

                # 处理可能的确认弹窗
                try:
                    alert = sb.driver.switch_to.alert
                    print(f"📢 弹窗内容: {alert.text}")
                    alert.accept()
                    print("✅ 已确认弹窗")
                except:
                    # 尝试自定义确认按钮
                    try:
                        confirm = sb.find_element('button:contains("确认"), button:contains("OK"), button:contains("Tak")', timeout=2)
                        confirm.click()
                        print("✅ 点击了确认按钮")
                    except:
                        pass
                break
        except Exception as e:
            print(f"尝试文本 '{text}' 失败: {e}")

    if not renew_clicked:
        print("❌ 未找到续期按钮，无法续期")
        sb.save_screenshot("renew_button_not_found.png")
        return False

    # ---------- 4. 等待页面刷新并验证结果 ----------
    print("⏳ 等待续期处理...")
    time.sleep(2)
    sb.refresh()
    time.sleep(5)  # 等待页面完全加载

    # 检查是否有禁止续期的错误消息
    page_after = sb.get_page_source()
    if "您不能再将服务器时间延长" in page_after or "cannot extend" in page_after.lower():
        print("ℹ️ 提示：您最近已续期过，无法再次延长（视为已完成）")
        sb.save_screenshot("already_renewed.png")
        return True

    # 获取新的有效期
    new_expiry = get_expiry_from_page(sb)
    sb.save_screenshot("after_renew_attempt.png")

    if old_expiry and new_expiry:
        print(f"📅 新有效期至: {new_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
        if new_expiry > old_expiry:
            print(f"✅ 续期成功！增加了 {(new_expiry - old_expiry).total_seconds() / 3600:.1f} 小时")
            return True
        else:
            print("❌ 续期失败：有效期未发生变化")
            return False
    elif not old_expiry and new_expiry:
        print("✅ 续期后获得有效期，可能成功")
        return True
    else:
        print("⚠️ 无法解析有效期，请检查截图")
        # 尝试判断是否出现其他成功标志（例如“操作成功”）
        if "成功" in page_after or "success" in page_after.lower():
            print("✅ 检测到成功提示，假定成功")
            return True
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
