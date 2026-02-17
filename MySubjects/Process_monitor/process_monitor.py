import psutil
import time
import logging
import os
from datetime import datetime

# 配置日志，记录监测状态到文件
log_file = os.path.join(os.path.dirname(__file__), 'wechat_monitor.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

def is_wechat_running():
    """
    检查微信进程是否正在运行
    """
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == 'WeChat.exe':
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def main() :
    logging.info("开始监测 WeChat.exe 是否启动...")
    wechat_found = False
    
    while True:
        if is_wechat_running():
            if not wechat_found:
                # 第一次检测到微信启动
                logging.info("✅ WeChat 已启动！")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] WeChat 已启动！")
                wechat_found = True
            # 微信仍在运行，继续等待
        else:
            if wechat_found:
                # 微信曾启动但现在关闭了
                logging.info("❌ WeChat 已关闭。")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] WeChat 已关闭。")
                wechat_found = False
        
        time.sleep(3)  # 每3秒检查一次

if __name__ == "__main__":
    main()