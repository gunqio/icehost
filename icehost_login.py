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
    
    # 等待页面加载
    time.sleep(3)
    
    # 先检查当前页面是否是服务器详情页（URL包含 /server/）
    current_url = sb.get_current_url()
    if "/server/" in current_url:
        print("📍 已在服务器详情页")
    else:
        print("📍 当前在仪表盘首页，需要进入服务器详情页")
        
        # 方法1：点击"POKAŻ MOJE SERWERY" (Show my servers) 展开列表
        try:
            show_servers_btn = sb.find_elements('//*[contains(text(), "POKAŻ MOJE SERWERY") or contains(text(), "Show my servers")]')
            if show_servers_btn and show_servers_btn[0].is_displayed():
                show_servers_btn[0].click()
                print("✅ 点击了'POKAŻ MOJE SERWERY'")
                time.sleep(2)
        except Exception as e:
            print(f"展开服务器列表失败: {e}")
        
        # 查找服务器链接/按钮
        server_selectors = [
            '//a[contains(text(), "free-servers-4.icehost.pl")]',
            '//a[contains(text(), "Amelie")]',
            '//div[contains(text(), "free-servers-4")]/parent::a',
            '//*[contains(@href, "/server/")]',
        ]
        
        clicked = False
        for selector in server_selectors:
            try:
                elements = sb.find_elements(selector)
                if elements:
                    print(f"✅ 找到服务器条目: {elements[0].text if elements[0].text else selector}")
                    elements[0].click()
                    clicked = True
                    print("✅ 已点击进入服务器详情页")
                    break
            except Exception:
                pass
        
        if not clicked:
            # 尝试查找所有href包含"/server/"的链接
            try:
                all_links = sb.find_elements('a[href*="/server/"]')
                if all_links:
                    print(f"✅ 通过href找到服务器链接: {all_links[0].get_attribute('href')}")
                    all_links[0].click()
                    clicked = True
            except:
                pass
        
        if not clicked:
            print("❌ 未能找到服务器条目，无法进入详情页")
            sb.save_screenshot("no_server_entry.png")
            return False
        
        # 等待详情页加载
        time.sleep(5)
    
    # 现在应该在服务器详情页了
    current_url = sb.get_current_url()
    print(f"📍 当前详情页URL: {current_url}")
    sb.save_screenshot("server_detail_page.png")
    
    # 查找并点击续期按钮
    print("🔍 查找续期按钮...")
    
    # 首先检查是否已经无法续期（根据截图中的提示）
    page_text = sb.get_page_source()
    if "您不能再将服务器时间延长6小时" in page_text or "cannot extend" in page_text.lower():
        print("⚠️ 检测到提示：最近已续期过，无法再次延长")
        # 但还是尝试找按钮
    elif "Brak daty ważności" in page_text or "No expiry date" in page_text:
        print("ℹ️ 服务器没有有效期，可能无需续期")
    
    # 续期按钮文本可能性
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
                # 滚动到按钮可见
                sb.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                time.sleep(1)
                elements[0].click()
                print("🔘 已点击续期按钮")
                time.sleep(3)
                
                # 处理可能的确认弹窗
                try:
                    alert = sb.driver.switch_to.alert
                    print(f"📢 弹窗内容: {alert.text}")
                    alert.accept()
                    time.sleep(1)
                except:
                    # 也可能有自定义确认对话框
                    try:
                        confirm_btn = sb.find_elements('button:contains("确认"), button:contains("OK"), button:contains("Tak")')
                        if confirm_btn:
                            confirm_btn[0].click()
                            print("✅ 确认了续期")
                    except:
                        pass
                
                time.sleep(2)
                sb.refresh()
                sb.save_screenshot("after_renew.png")
                print("✅ 续期操作完成")
                return True
        except Exception as e:
            print(f"尝试文本 '{text}' 失败: {e}")
    
    # 如果没有找到特定文本，尝试找所有按钮中含有相关关键词的
    try:
        buttons = sb.find_elements('button, a')
        print(f"🔍 共找到 {len(buttons)} 个按钮/链接，查找续期相关...")
        for idx, btn in enumerate(buttons):
            try:
                btn_text = btn.text
                if btn_text and any(kw in btn_text.lower() for kw in ["增加", "add", "dodaj", "przedłuż", "extend", "小时", "hour", "godzin"]):
                    print(f"✅ 找到候选续期按钮 {idx}: '{btn_text}'")
                    btn.click()
                    time.sleep(3)
                    sb.refresh()
                    print("✅ 续期完成")
                    return True
            except:
                pass
    except Exception as e:
        print(f"查找关键词按钮失败: {e}")
    
    # 滚动到底部再试一次
    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    try:
        elem = sb.find_element('//*[contains(text(), "增加") or contains(text(), "Add")]', timeout=3)
        if elem:
            elem.click()
            print("✅ 滚动后找到并点击")
            return True
    except:
        pass
    
    print("❌ 未找到续期按钮，可能是：")
    print("   1. 服务器已到期无法续期")
    print("   2. 最近刚续期过，按钮不可用")
    print("   3. 页面结构变化")
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
        except Exception:
            sb.open(LOGIN_URL)
        
        time.sleep(5)
        sb.save_screenshot("login_page.png")
        print("📸 截图: login_page.png")
        
        print("📝 填写账号密码...")
        
        # 更通用的邮箱/用户名输入框选择器
        email_selectors = [
            'input[name="email"]',
            'input[name="username"]',
            'input[type="email"]',
            'input[placeholder*="mail" i]',
            'input[placeholder*="email" i]',
            'input[placeholder*="E-mail" i]',
            'input[placeholder*="Adres" i]',
            'input[type="text"]',
            'input:first-of-type'
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
            try:
                first_input = sb.find_element('input')
                sb.type(first_input, EMAIL)
                email_ok = True
                print("✅ 使用第一个输入框填写邮箱")
            except:
                raise Exception("未找到邮箱输入框")
        
        # 密码框选择器
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="hasło" i]',
            'input[placeholder*="password" i]'
        ]
        
        pwd_ok = False
        for selector in password_selectors:
            try:
                if sb.is_element_visible(selector):
                    sb.type(selector, PASSWORD)
                    pwd_ok = True
                    print(f"✅ 找到密码框: {selector}")
                    break
            except Exception:
                pass
        
        if not pwd_ok:
            try:
                inputs = sb.find_elements('input')
                if len(inputs) >= 2:
                    sb.type(inputs[1], PASSWORD)
                    pwd_ok = True
                    print("✅ 使用第二个输入框填写密码")
            except:
                raise Exception("未找到密码输入框")
        
        print("🔐 提交登录...")
        
        # 登录按钮选择器
        button_selectors = [
            'button[type="submit"]',
            'button:contains("Załoguj się")',
            'button:contains("Login")',
            'button:contains("Sign in")',
            'button',
            'input[type="submit"]'
        ]
        
        clicked = False
        for selector in button_selectors:
            try:
                if selector.startswith('button:contains'):
                    if sb.is_element_visible(selector):
                        sb.click(selector)
                        clicked = True
                        print(f"✅ 点击登录按钮: {selector}")
                        break
                else:
                    if sb.is_element_visible(selector):
                        sb.click(selector)
                        clicked = True
                        print(f"✅ 点击登录按钮: {selector}")
                        break
            except Exception:
                pass
        
        if not clicked:
            try:
                sb.press_enter('input[type="password"]')
                print("✅ 使用回车键提交")
                clicked = True
            except:
                pass
        
        if not clicked:
            raise Exception("未找到登录按钮且回车无效")
        
        print("⏳ 等待登录跳转...")
        time.sleep(8)
        
        # 判断是否登录成功
        page_source = sb.get_page_source()
        current_url = sb.get_current_url()
        print(f"📍 当前页面: {current_url}")
        
        success_indicators = [
            "账户余额",
            "服务器",
            "Serwery",
            "Konto",
            "余额",
            "截止日期",
            "有效期至",
            "delete date"
        ]
        
        is_logged_in = False
        for indicator in success_indicators:
            if indicator.lower() in page_source.lower():
                is_logged_in = True
                print(f"✅ 检测到成功标志: {indicator}")
                break
        
        if not is_logged_in and "/auth/login" not in current_url and "/login" not in current_url:
            is_logged_in = True
            print("✅ URL不是登录页，假定成功")
        
        sb.save_screenshot("after_login.png")
        print("📸 截图: after_login.png")
        
        if not is_logged_in:
            print("❌ 登录失败，请检查账号密码或代理")
            with open("login_failed.html", "w", encoding="utf-8") as f:
                f.write(sb.get_page_source())
            return False
        
        print("🎉 登录成功！")
        # 执行续期
        renew_success = renew_server(sb)
        return renew_success


if __name__ == "__main__":
    try:
        result = login_icehost()
        if result:
            print("🏁 任务完成 - 服务器已成功续期")
            exit(0)
        else:
            print("💥 任务失败")
            exit(1)
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
