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
            'input[placeholder*="Adres" i]',  # 波兰语
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
            # 尝试直接找第一个输入框
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
            'input[placeholder*="hasło" i]',  # 波兰语
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
            # 找第二个输入框
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
                    # SeleniumBase 特殊语法
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
            # 尝试按回车
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
        
        # 正确判断是否登录成功：检查仪表盘特有元素
        page_source = sb.get_page_source()
        current_url = sb.get_current_url()
        print(f"📍 当前页面: {current_url}")
        
        # 成功标志：出现"账户余额"、"服务器"、"Konto"、"Serwery" 或 不包含登录表单
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
        
        login_failure_indicators = [
            "Załoguj się",  # 波兰语“登录”
            "błędny login",
            "invalid credentials"
        ]
        
        is_logged_in = False
        
        # 检查页面是否包含成功标志
        for indicator in success_indicators:
            if indicator.lower() in page_source.lower():
                is_logged_in = True
                print(f"✅ 检测到成功标志: {indicator}")
                break
        
        # 如果没找到成功标志但也没找到失败标志，根据URL判断
        if not is_logged_in:
            # 如果当前URL不是登录页，可能也成功
            if "/auth/login" not in current_url and "/login" not in current_url:
                is_logged_in = True
                print("✅ URL不是登录页，假定成功")
            else:
                # 检查是否有失败标志
                for indicator in login_failure_indicators:
                    if indicator.lower() in page_source.lower():
                        print(f"❌ 登录失败标志: {indicator}")
                        break
        
        sb.save_screenshot("after_login.png")
        print("📸 截图: after_login.png")
        
        if is_logged_in:
            print("🎉 登录成功！")
            # 执行续期
            renew_success = renew_server(sb)
            return renew_success
        else:
            print("❌ 登录失败，请检查账号密码或代理")
            # 保存页面源码
            with open("login_failed.html", "w", encoding="utf-8") as f:
                f.write(sb.get_page_source())
            print("📄 已保存页面源码: login_failed.html")
            return False


def renew_server(sb):
    """执行服务器续期操作"""
    print("\n🔄 开始检查并续期服务器...")
    
    # 等待页面完全加载
    time.sleep(3)
    
    # 滚动页面确保按钮可见
    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    sb.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 方法1：通过精确文本查找按钮
    button_texts = [
        "增加 6 小时有效期",
        "Add 6 hours",
        "Dodaj 6 godzin",  # 波兰语
        "+6 godzin",
        "Przedłuż o 6 godzin"
    ]
    
    for text in button_texts:
        try:
            # 使用XPath查找包含该文本的元素
            xpath = f'//*[contains(text(), "{text}")]'
            elements = sb.find_elements(xpath)
            if elements:
                print(f"✅ 找到续期按钮: {text}")
                elements[0].click()
                print("🔘 已点击续期按钮")
                time.sleep(3)
                
                # 处理可能的确认对话框
                try:
                    alert = sb.driver.switch_to.alert
                    print(f"📢 弹窗: {alert.text}")
                    alert.accept()
                    time.sleep(1)
                except:
                    pass
                
                sb.refresh()
                time.sleep(2)
                sb.save_screenshot("after_renew.png")
                print("✅ 续期操作完成")
                return True
        except Exception as e:
            print(f"方法1失败 ({text}): {e}")
    
    # 方法2：查找所有按钮，匹配关键词
    try:
        buttons = sb.find_elements('button, a')
        print(f"🔍 共找到 {len(buttons)} 个按钮/链接")
        for idx, btn in enumerate(buttons):
            try:
                btn_text = btn.text
                if btn_text and any(kw in btn_text.lower() for kw in ["增加", "add", "dodaj", "przedłuż", "小时", "hour", "godzin"]):
                    print(f"✅ 找到候选按钮 {idx}: '{btn_text}'")
                    btn.click()
                    time.sleep(3)
                    sb.refresh()
                    print("✅ 续期完成")
                    return True
            except:
                pass
    except Exception as e:
        print(f"方法2失败: {e}")
    
    # 方法3：通过类名或ID
    try:
        renew_ids = ['renew', 'extend', 'add-time']
        for rid in renew_ids:
            selector = f'[id*="{rid}"], [class*="{rid}"]'
            elements = sb.find_elements(selector)
            if elements:
                print(f"✅ 通过属性找到元素: {selector}")
                elements[0].click()
                time.sleep(3)
                sb.refresh()
                return True
    except Exception as e:
        print(f"方法3失败: {e}")
    
    print("❌ 未能找到续期按钮")
    sb.save_screenshot("renew_failed.png")
    with open("page_source_renew.html", "w", encoding="utf-8") as f:
        f.write(sb.get_page_source())
    print("📸 已保存调试文件")
    return False


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
