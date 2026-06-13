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
    """执行服务器续期操作 - 进入服务器详情页后点击续期"""
    print("\n🔄 开始检查并续期服务器...")
    time.sleep(3)

    current_url = sb.get_current_url()
    if "/server/" in current_url:
        print("📍 已在服务器详情页")
    else:
        print("📍 当前在仪表盘首页，需要进入服务器详情页")

        # 1. 展开"POKAŻ MOJE SERWERY"
        try:
            show_btn = sb.find_element('//*[contains(text(), "POKAŻ MOJE SERWERY")]', timeout=5)
            if show_btn.is_displayed():
                sb.execute_script("arguments[0].scrollIntoView(true);", show_btn)
                time.sleep(0.5)
                show_btn.click()
                print("✅ 点击了'POKAŻ MOJE SERWERY'")
                time.sleep(2)
            else:
                sb.execute_script("arguments[0].click();", show_btn)
                print("✅ 强制点击了'POKAŻ MOJE SERWERY'")
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ 点击展开按钮异常: {e}")

        # 2. 等待服务器列表出现
        try:
            sb.wait_for_element_visible('//*[contains(text(), "free-servers")]', timeout=5)
            print("✅ 服务器列表已展开")
        except:
            print("⚠️ 未明确检测到服务器列表，继续尝试查找")

        # 3. 🔥 关键修复：直接点击服务器条目文本 "free-servers-4.icehost.pl:30159"
        clicked = False
        server_texts = [
            "free-servers-4.icehost.pl:30159",
            "free-servers-4.icehost.pl",
            "Amelie Serwer testowy"
        ]
        
        for text in server_texts:
            try:
                # 尝试直接点击包含该文本的元素（无论是什么标签）
                elem = sb.find_element(f'//*[contains(text(), "{text}")]', timeout=3)
                if elem:
                    # 先滚动到可见
                    sb.execute_script("arguments[0].scrollIntoView(true);", elem)
                    time.sleep(0.5)
                    # 尝试点击元素本身（如果是<div>或<span>，往往可点击）
                    elem.click()
                    clicked = True
                    print(f"✅ 直接点击服务器条目文本: {text}")
                    break
            except:
                # 如果直接点击失败，尝试找父级的<a>链接
                try:
                    elem = sb.find_element(f'//*[contains(text(), "{text}")]/ancestor::a', timeout=2)
                    if elem:
                        elem.click()
                        clicked = True
                        print(f"✅ 通过父级链接点击: {text}")
                        break
                except:
                    pass
        
        # 备用方法：查找所有包含/server/的链接（如未成功）
        if not clicked:
            try:
                links = sb.find_elements('a[href*="/server/"]')
                if links:
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '/server/' in href:
                            print(f"找到服务器链接: {href}")
                            link.click()
                            clicked = True
                            print("✅ 点击了服务器链接")
                            break
            except Exception as e:
                print(f"备用方法失败: {e}")

        if not clicked:
            print("❌ 未能找到服务器条目，无法进入详情页")
            sb.save_screenshot("no_server_entry.png")
            return False

        # 等待详情页加载
        time.sleep(5)
        print(f"📍 跳转后URL: {sb.get_current_url()}")

    # 当前应处于服务器详情页
    sb.save_screenshot("server_detail_page.png")

    # 查找并点击续期按钮
    print("🔍 查找续期按钮...")
    page_text = sb.get_page_source()
    if "您不能再将服务器时间延长6小时" in page_text or "cannot extend" in page_text.lower():
        print("⚠️ 检测到提示：最近已续期过，无法再次延长")
    elif "Brak daty ważności" in page_text or "No expiry date" in page_text:
        print("ℹ️ 服务器没有有效期，无需续期")

    renew_texts = [
        "增加 6 小时有效期",
        "Add 6 hours",
        "Dodaj 6 godzin",
        "Przedłuż o 6 godzin",
        "+6 godzin",
        "Extend by 6 hours"
    ]

    for text in renew_texts:
        try:
            xpath = f'//*[contains(text(), "{text}")]'
            elements = sb.find_elements(xpath)
            if elements:
                print(f"✅ 找到续期按钮: {text}")
                sb.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                time.sleep(1)
                elements[0].click()
                print("🔘 已点击续期按钮")
                time.sleep(3)

                # 处理弹窗
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

                time.sleep(2)
                sb.refresh()
                sb.save_screenshot("after_renew.png")
                print("✅ 续期操作完成")
                return True
        except Exception as e:
            print(f"尝试'{text}'失败: {e}")

    # 备用：关键词查找所有按钮
    try:
        buttons = sb.find_elements('button, a')
        print(f"🔍 共找到 {len(buttons)} 个可点击元素")
        for btn in buttons:
            btn_text = btn.text
            if btn_text and any(kw in btn_text.lower() for kw in ["增加", "add", "dodaj", "przedłuż", "extend", "小时", "hour", "godzin"]):
                print(f"✅ 候选按钮: {btn_text}")
                btn.click()
                time.sleep(3)
                sb.refresh()
                return True
    except Exception as e:
        print(f"关键词查找失败: {e}")

    # 最后滚动到底部
    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    try:
        elem = sb.find_element('//*[contains(text(), "增加") or contains(text(), "Add")]', timeout=3)
        if elem:
            elem.click()
            print("✅ 滚动后找到续期按钮")
            return True
    except:
        pass

    print("❌ 未找到续期按钮")
    sb.save_screenshot("renew_not_found.png")
    with open("detail_page_source.html", "w", encoding="utf-8") as f:
        f.write(sb.get_page_source())
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
