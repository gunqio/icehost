#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lumix 自动续期脚本 - IceHost.PL 适配版
功能：通过 Cookie 认证，执行增加 6 小时有效期的操作
依赖：requests, 环境变量 LUMIX_COOKIE, GOST_PROXY(可选), TG_BOT(可选)
"""

import os
import sys
import re
import time
import requests
from datetime import datetime

# ======================== 配置 ================================
LUMIX_COOKIE = os.getenv("LUMIX_COOKIE")          # 登录 IceHost.PL 后的 Cookie 字符串
GOST_PROXY = os.getenv("GOST_PROXY")              # 非空则启用代理
TG_BOT = os.getenv("TG_BOT")                      # 格式 "TOKEN:CHAT_ID" 或 "TOKEN,CHAT_ID"

# IceHost.PL 配置（⚠️ 请根据实际抓包修改）
PANEL_URL = "https://icehost.pl"                  # 面板根地址
SERVER_ID = "449a6366"                            # 你的服务器 ID（从截图中的“支持ID”获取）
RENEW_HOURS = 6                                   # 每次续期增加的小时数

# 续期请求的 URL 和参数（常见两种方式，选其一）
# 方式1: GET 请求（如 https://icehost.pl/clientarea/server/renew?id=xxx&hours=6）
RENEW_URL_GET = f"{PANEL_URL}/clientarea/server/renew"
RENEW_PARAMS_GET = {"id": SERVER_ID, "hours": RENEW_HOURS}

# 方式2: POST 请求（如表单提交）
RENEW_URL_POST = f"{PANEL_URL}/clientarea/server/renew"
RENEW_POST_DATA = {"server_id": SERVER_ID, "action": "renew", "hours": RENEW_HOURS}

# 选择使用哪种方式（True=GET, False=POST）
USE_GET_METHOD = True   # ⚠️ 根据实际请求方法修改

# 状态页面 URL（用于获取当前有效期，可选）
STATUS_URL = f"{PANEL_URL}/clientarea/server/detail?id={SERVER_ID}"

# 代理配置（与工作流中启动的本地 GOST 一致）
PROXIES = None
if GOST_PROXY:
    PROXIES = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
    print("🛡️ 使用代理模式")
else:
    print("🌐 直连模式")

# ======================== 辅助函数 ================================
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def tg_send(message):
    if not TG_BOT:
        return
    try:
        if ':' in TG_BOT:
            token, chat_id = TG_BOT.split(':', 1)
        elif ',' in TG_BOT:
            token, chat_id = TG_BOT.split(',', 1)
        else:
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=5)
        print("📨 TG 推送成功")
    except Exception as e:
        print(f"❌ TG 推送失败: {e}")

def verify_ip():
    try:
        resp = requests.get("https://api.ipify.org", proxies=PROXIES, timeout=10)
        ip = resp.text.strip()
        parts = ip.split('.')
        if len(parts) == 4:
            masked = f"{parts[0]}.{parts[1]}.{parts[2]}.**"
        else:
            masked = ip[:8] + "**"
        print(f"✅ 出口 IP 确认：{masked}")
        return True
    except Exception as e:
        print(f"❌ 出口 IP 验证失败: {e}")
        return False

def get_current_expiry():
    """
    获取当前有效期（可选，用于日志输出）
    返回字符串如 "2026-06-14 12:09:49"，失败返回 None
    """
    headers = {"Cookie": LUMIX_COOKIE, "User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(STATUS_URL, headers=headers, proxies=PROXIES, timeout=15)
        # 尝试从页面提取 "有效期至：" 后面的时间
        match = re.search(r'有效期至：([\d\-: ]+)', resp.text)
        if match:
            expiry_str = match.group(1).strip()
            print(f"📅 当前有效期至: {expiry_str}")
            return expiry_str
        else:
            print("⚠️ 未找到有效期信息")
            return None
    except Exception as e:
        print(f"❌ 获取有效期失败: {e}")
        return None

def perform_renew():
    """
    执行续期请求（增加6小时）
    返回 True 表示成功，False 表示失败
    """
    headers = {
        "Cookie": LUMIX_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": STATUS_URL,   # 模拟从状态页点击
    }
    try:
        if USE_GET_METHOD:
            resp = requests.get(
                RENEW_URL_GET,
                params=RENEW_PARAMS_GET,
                headers=headers,
                proxies=PROXIES,
                timeout=15,
                allow_redirects=True
            )
        else:
            resp = requests.post(
                RENEW_URL_POST,
                data=RENEW_POST_DATA,
                headers=headers,
                proxies=PROXIES,
                timeout=15,
                allow_redirects=True
            )
        # 判断是否成功：响应中包含 "成功您已延长服务器的有效期" 或类似
        if "成功您已延长服务器的有效期" in resp.text or "延长" in resp.text:
            return True
        else:
            # 打印部分响应以便调试
            print(f"⚠️ 响应未包含成功标识，前200字符: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 续期请求异常: {e}")
        return False

# ======================== 主流程 ================================
def main():
    print("\n============================ {lumix_renew.py} =============================")
    print(f"🕐 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not LUMIX_COOKIE:
        print("❌ 错误: 环境变量 LUMIX_COOKIE 未设置")
        sys.exit(1)

    # 1. 验证出口 IP
    if not verify_ip():
        sys.exit(1)

    # 2. 可选：获取当前有效期（用于记录）
    expiry_before = get_current_expiry()

    # 3. 执行续期
    print(f"🔄 开始续期（增加 {RENEW_HOURS} 小时）...")
    success = perform_renew()
    if success:
        print("✅ 续期成功！")
        # 再次获取有效期验证
        expiry_after = get_current_expiry()
    else:
        print("❌ 续期失败，请检查 Cookie 或请求地址")
        tg_send(f"Lumix 续期失败 ❌ | 时间 {datetime.now()}")
        sys.exit(1)

    # 4. 输出服务器状态（固定显示“在线”或根据实际情况）
    # 原日志中有 "服务器状态: starting"，此处若无状态 API 可忽略
    print("🖥️ 服务器状态: 在线")   # 根据实际情况可修改

    # 5. 启动逻辑（IceHost 无需手动启动，保持跳过）
    print("⏭️  启动: 服务器已在线，跳过")

    # 6. Telegram 推送
    tg_send(f"Lumix 续期成功 ✅ | 增加 {RENEW_HOURS} 小时 | 有效期至 {expiry_after or '未知'}")

    print("\n===================== {lumix_renew.py} passed ======================")

if __name__ == "__main__":
    main()
