#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lumix 自动续期脚本
根据实际日志重构：
- 最多续期 3 次，每次增加 1 天，上限 14 天
- 代理模式、TG 通知、出口 IP 验证
"""

import os
import sys
import time
import requests
from datetime import datetime

# ======================== 配置（环境变量）========================
LUMIX_COOKIE = os.getenv("LUMIX_COOKIE")
GOST_PROXY = os.getenv("GOST_PROXY")      # 非空即启用代理模式
TG_BOT = os.getenv("TG_BOT")              # 格式 "token:chat_id" 或 "token,chat_id"

# 业务常量
MAX_DAYS = 14          # 服务器最大天数限制
MAX_RENEW_ATTEMPTS = 3 # 最多续期次数（与日志中的3次对应）

# 代理配置（工作流中已启动本地 GOST，监听 127.0.0.1:8080）
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
    """发送 Telegram 通知（如果配置了）"""
    if not TG_BOT:
        return
    try:
        # 分离 token 和 chat_id
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
    """验证出口 IP，输出掩码格式"""
    try:
        resp = requests.get("https://api.ipify.org", proxies=PROXIES, timeout=10)
        ip = resp.text.strip()
        # 掩码最后一段（兼容 IPv4）
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

# ======================== API 接口（需根据实际服务修改）===============
def get_server_status():
    """
    获取服务器状态和剩余天数
    返回: (status, days_left)
    """
    # 示例接口，请替换为实际 URL
    url = "https://www.lumixgame.com/api/server/status"
    headers = {
        "Cookie": LUMIX_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        # 假设返回格式: {"code":0, "data":{"status":"starting", "expire_days":11}}
        if data.get("code") == 0:
            info = data.get("data", {})
            return info.get("status"), info.get("expire_days")
        else:
            print(f"❌ API 返回错误: {data}")
            return None, None
    except Exception as e:
        print(f"❌ 获取状态失败: {e}")
        return None, None

def perform_renew():
    """
    执行一次续期请求
    返回新的剩余天数，失败返回 None
    """
    url = "https://www.lumixgame.com/api/server/renew"
    headers = {"Cookie": LUMIX_COOKIE, "User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.post(url, headers=headers, proxies=PROXIES, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            new_days = data.get("data", {}).get("expire_days")
            return new_days
        else:
            print(f"❌ 续期失败: {data.get('msg')}")
            return None
    except Exception as e:
        print(f"❌ 续期异常: {e}")
        return None

def start_server():
    """启动服务器（如果脚本决定需要启动）"""
    url = "https://www.lumixgame.com/api/server/start"
    headers = {"Cookie": LUMIX_COOKIE}
    try:
        resp = requests.post(url, headers=headers, proxies=PROXIES, timeout=10)
        return resp.status_code == 200
    except:
        return False

# ======================== 主逻辑 ================================
def main():
    print("\n============================ {lumix_renew.py} =============================")
    print(f"🕐 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 出口 IP 验证
    if not verify_ip():
        sys.exit(1)

    # 2. 获取当前状态和剩余天数
    status, days_left = get_server_status()
    if status is None:
        print("❌ 无法获取服务器状态，退出")
        sys.exit(1)

    print(f"🖥️ 服务器状态: {status}")
    print(f"📅 剩余天数: {days_left} 天")

    # 3. 续期逻辑（最多 MAX_RENEW_ATTEMPTS 次，上限 MAX_DAYS 天）
    renew_count = 0
    current_days = days_left

    if current_days < MAX_DAYS:
        print(f"🔄 开始续期 ({current_days} → {MAX_DAYS} 天)...")
        for attempt in range(MAX_RENEW_ATTEMPTS):
            # 如果已经达到上限，停止续期
            if current_days >= MAX_DAYS:
                break
            new_days = perform_renew()
            if new_days is None:
                print("⚠️ 续期请求失败，停止续期")
                break
            renew_count += 1
            current_days = new_days
            print(f"  → 第 {renew_count} 次续期后剩余 {current_days} 天")
            time.sleep(1)  # 避免请求过快
        print(f"✅ 续期完成！共续期 {renew_count} 次，当前 {current_days} 天")
    else:
        print("✅ 无需续期")

    # 4. 启动服务器（根据日志：只有状态为 online 时才跳过启动，其他状态均跳过，但注释保留）
    # 日志输出：⏭️  启动: 服务器已在线，跳过
    if status == "online":
        print("⏭️  启动: 服务器已在线，跳过")
    else:
        # 若需要自动启动，取消下方注释；否则保持“跳过”行为
        print("⏭️  启动: 服务器未在线，脚本设置为跳过（如需自动启动请修改代码）")
        # 可选：取消注释以下代码以自动启动
        # if start_server():
        #     print("✅ 启动成功")
        # else:
        #     print("❌ 启动失败")

    # 5. Telegram 推送
    tg_send(f"Lumix 续期完成 | 剩余 {current_days} 天 | 续期 {renew_count} 次")

    print("\n===================== {lumix_renew.py} passed ======================")

if __name__ == "__main__":
    if not LUMIX_COOKIE:
        print("❌ 错误: 环境变量 LUMIX_COOKIE 未设置")
        sys.exit(1)
    main()
