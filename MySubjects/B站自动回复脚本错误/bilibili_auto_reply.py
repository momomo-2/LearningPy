#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站自动回复脚本
功能：监控指定UID用户的新回复，并自动逐一回复自定义列表内容
作者：AI Assistant
版本：1.0.0
Python版本：3.12.3
"""

import os
import sys
import json
import time
import re
import threading
import logging
from datetime import datetime
from tkinter import Tk, StringVar, BooleanVar, Menu, END, LEFT, INSERT
from tkinter import ttk, messagebox, scrolledtext
from tkinter import WORD as TK_WORD
import requests
from urllib.parse import urlencode

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 默认DEBUG级别，文件会记录所有日志
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bilibili_auto_reply.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # 控制台默认INFO级别

# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 配置文件路径
CONFIG_FILE = 'config.json'
REPLIED_FILE = 'replied.json'


class BilibiliAPI:
    """B站API交互类"""
    
    def __init__(self, sessdata: str = '', csrf: str = ''):
        self.sessdata = sessdata
        self.csrf = csrf
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.update_cookies()
    
    def update_cookies(self):
        """更新Cookie"""
        if self.sessdata:
            self.session.cookies.set('SESSDATA', self.sessdata)
        if self.csrf:
            self.session.cookies.set('bili_jct', self.csrf)
    
    def set_credentials(self, sessdata: str, csrf: str):
        """设置认证信息"""
        self.sessdata = sessdata
        self.csrf = csrf
        self.update_cookies()
    
    def get_reply_messages(self, last_id: int = 0) -> dict:
        """
        获取"回复我的"消息列表
        API: https://api.bilibili.com/x/msgfeed/reply
        """
        url = 'https://api.bilibili.com/x/msgfeed/reply'
        params = {}
        if last_id:
            params['id'] = last_id
        
        try:
            response = self.session.get(url, params=params, headers=self.headers, timeout=30)
            
            # 记录调试信息
            logger.debug(f"获取消息响应状态: {response.status_code}")
            
            # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                response_text = response.text[:500]
                logger.error(f"获取消息返回非JSON: {response_text}")
                return {'success': False, 'message': f'服务器返回非JSON数据，可能被风控拦截', 'raw_response': response_text[:200]}
            
            data = response.json()
            if data.get('code') == 0:
                return {'success': True, 'data': data.get('data', {})}
            else:
                return {'success': False, 'message': data.get('message', '未知错误'), 'code': data.get('code')}
        except json.JSONDecodeError as e:
            logger.error(f"解析消息响应JSON失败: {str(e)}")
            return {'success': False, 'message': f'JSON解析失败: {str(e)}'}
        except Exception as e:
            logger.error(f"获取回复消息失败: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def _generate_dm_params(self) -> dict:
        """生成B站风控参数 (dm_img_list等)"""
        import random
        import base64
        
        # 生成鼠标轨迹数据
        dm_img_list = []
        base_x, base_y = 2000, 1000
        base_z, base_ts = 0, 700000
        
        for i in range(10):
            dm_img_list.append({
                "x": base_x + random.randint(-500, 500),
                "y": base_y + random.randint(-500, 500),
                "z": base_z + i * 50,
                "timestamp": base_ts + i * 100,
                "k": random.randint(60, 130),
                "type": 0
            })
        
        # WebGL 指纹 (使用固定的常见值)
        dm_img_str = "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ"
        
        # 显卡信息
        dm_cover_img_str = "QU5HTEUgKEludGVsLCBJbnRlbChSKSBJcmlzKFIpIFhlIEdyYXBoaWNz"
        
        # 交互数据
        dm_img_inter = {
            "ds": [{"t": 0, "c": "", "p": [1274, 92, 2008], "s": [139, 9825, -12414]}],
            "wh": [3479, 3243, 45],
            "of": [1880, 2760, 380]
        }
        
        return {
            'dm_img_list': json.dumps(dm_img_list, separators=(',', ':')),
            'dm_img_str': dm_img_str,
            'dm_cover_img_str': dm_cover_img_str,
            'dm_img_inter': json.dumps(dm_img_inter, separators=(',', ':'))
        }
    
    def reply_to_comment(self, oid: int, type_id: int, root: int, parent: int, message: str) -> dict:
        """
        回复评论
        API: https://api.bilibili.com/x/v2/reply/add
        
        Args:
            oid: 对象ID（视频aid/动态id等）
            type_id: 评论区类型（1=视频, 11=动态, 17=动态评论）
            root: 根评论ID
            parent: 父评论ID（回复谁）
            message: 回复内容
        """
        url = 'https://api.bilibili.com/x/v2/reply/add'
        
        # 基础数据
        data = {
            'oid': oid,
            'type': type_id,
            'root': root,
            'parent': parent,
            'message': message,
            'plat': 1,
            'csrf': self.csrf,
            'at_name_to_mid': '{}',
            'gaia_source': 'main_web',
            'statistics': json.dumps({"appId": 100, "platform": 5}, separators=(',', ':'))
        }
        
        # 添加风控参数
        dm_params = self._generate_dm_params()
        data.update(dm_params)
        
        # 更新请求头
        headers = self.headers.copy()
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.bilibili.com',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        response = None
        try:
            response = self.session.post(url, data=data, headers=headers, timeout=30)
            
            # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            
            # 记录原始响应用于调试
            logger.debug(f"回复API响应状态: {response.status_code}")
            logger.debug(f"回复API响应头: {dict(response.headers)}")
            
            # 检查是否是JSON响应
            if 'application/json' in content_type:
                result = response.json()
                if result.get('code') == 0:
                    return {'success': True, 'data': result.get('data', {})}
                else:
                    return {'success': False, 'message': result.get('message', '未知错误'), 'code': result.get('code')}
            else:
                # 非JSON响应，可能是被拦截了
                response_text = response.text[:500]  # 只记录前500字符
                logger.error(f"回复API返回非JSON: {response_text}")
                return {'success': False, 'message': f'服务器返回非JSON数据，可能被风控拦截。状态码: {response.status_code}', 'raw_response': response_text[:200]}
                
        except json.JSONDecodeError as e:
            logger.error(f"解析回复响应JSON失败: {str(e)}")
            try:
                if response is not None:
                    raw_text = response.text[:500]
                    return {'success': False, 'message': f'JSON解析失败，响应内容: {raw_text}', 'raw_response': raw_text}
                else:
                    return {'success': False, 'message': f'JSON解析失败，无法获取响应内容: {str(e)}'}
            except:
                return {'success': False, 'message': f'JSON解析失败，无法获取响应内容: {str(e)}'}
        except Exception as e:
            logger.error(f"发送回复失败: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def get_user_info(self, uid: int) -> dict:
        """获取用户信息"""
        url = f'https://api.bilibili.com/x/space/acc/info?mid={uid}'
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)
            data = response.json()
            if data.get('code') == 0:
                return {'success': True, 'data': data.get('data', {})}
            else:
                return {'success': False, 'message': data.get('message', '未知错误')}
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return {'success': False, 'message': str(e)}


class AutoReplyManager:
    """自动回复管理器"""
    
    def __init__(self, gui=None):
        self.api = BilibiliAPI()
        self.gui = gui
        self.running = False
        self.monitor_thread = None
        self.target_uid = None
        self.reply_list = []
        self.reply_index = 0
        self.check_interval = 30  # 默认30秒检查一次
        self.replied_ids = set()  # 已回复的评论ID集合
        self.load_replied_ids()
    
    def load_replied_ids(self):
        """加载已回复的评论ID"""
        if os.path.exists(REPLIED_FILE):
            try:
                with open(REPLIED_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.replied_ids = set(data.get('replied_ids', []))
            except Exception as e:
                logger.error(f"加载已回复ID失败: {str(e)}")
                self.replied_ids = set()
    
    def save_replied_ids(self):
        """保存已回复的评论ID"""
        try:
            with open(REPLIED_FILE, 'w', encoding='utf-8') as f:
                json.dump({'replied_ids': list(self.replied_ids)}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存已回复ID失败: {str(e)}")
    
    def set_credentials(self, sessdata: str, csrf: str):
        """设置认证信息"""
        self.api.set_credentials(sessdata, csrf)
    
    def set_target_uid(self, uid: int):
        """设置目标用户UID"""
        self.target_uid = uid
    
    def set_reply_list(self, replies: list):
        """设置回复内容列表"""
        self.reply_list = [r.strip() for r in replies if r.strip()]
        self.reply_index = 0
    
    def set_check_interval(self, interval: int):
        """设置检查间隔（秒）"""
        self.check_interval = max(10, interval)  # 最少10秒
    
    def get_next_reply(self) -> str:
        """获取下一条回复内容（循环使用）"""
        if not self.reply_list:
            return "感谢回复~"
        reply = self.reply_list[self.reply_index]
        self.reply_index = (self.reply_index + 1) % len(self.reply_list)
        return reply
    
    def start_monitoring(self):
        """开始监控"""
        if self.running:
            return
        
        if not self.api.sessdata or not self.api.csrf:
            self.log("错误: 请先设置Cookie信息", 'error')
            return
        
        if not self.target_uid:
            self.log("错误: 请设置目标用户UID", 'error')
            return
        
        if not self.reply_list:
            self.log("错误: 请设置回复内容列表", 'error')
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.log(f"开始监控用户UID {self.target_uid} 的新回复...")
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        self.log("监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        last_id = 0  # 上次获取的最新消息ID，初始为0表示获取最新的消息列表
        
        while self.running:
            try:
                result = self.api.get_reply_messages(last_id)
                
                if not result['success']:
                    error_msg = result.get('message', '未知错误')
                    self.log(f"获取消息失败: {error_msg}", 'error')
                    if '登录' in error_msg or result.get('code') == -101:
                        self.log("Cookie可能已过期，请重新设置", 'error')
                        self.stop_monitoring()
                        break
                    time.sleep(self.check_interval)
                    continue
                
                items = result['data'].get('items', [])
                
                if items:
                    # 更新last_id为最新的ID
                    last_id = items[0].get('id', last_id)
                    
                    for item in items:
                        if not self.running:
                            break
                        
                        # 检查是否是目标用户的回复
                        user_info = item.get('user', {})
                        sender_uid = user_info.get('mid', 0)
                        
                        if sender_uid != self.target_uid:
                            continue
                        
                        # 获取评论信息
                        item_detail = item.get('item', {})
                        reply_id = item.get('id', '')
                        
                        # 检查是否已经回复过
                        if reply_id in self.replied_ids:
                            continue
                        
                        # 获取必要参数
                        oid = item_detail.get('subject_id', 0)
                        type_id = item_detail.get('type', 1)
                        root = item_detail.get('root_id', 0)
                        parent = item_detail.get('target_id', 0)
                        source_content = item_detail.get('source_content', '')
                        target_reply_content = item_detail.get('target_reply_content', '')
                        
                        # 如果root为0，说明是回复主评论
                        if root == 0:
                            root = parent
                        
                        user_name = user_info.get('nickname', '未知用户')
                        
                        self.log(f"检测到来自 {user_name}(UID:{sender_uid}) 的新回复: {target_reply_content[:50]}...")
                        
                        # 发送自动回复
                        reply_message = self.get_next_reply()
                        reply_result = self.api.reply_to_comment(oid, type_id, root, parent, reply_message)
                        
                        if reply_result['success']:
                            self.replied_ids.add(reply_id)
                            self.save_replied_ids()
                            self.log(f"自动回复成功: {reply_message}", 'success')
                        else:
                            error_msg = reply_result.get('message', '未知错误')
                            raw_response = reply_result.get('raw_response', '')
                            self.log(f"自动回复失败: {error_msg}", 'error')
                            if raw_response:
                                self.log(f"原始响应: {raw_response}", 'error')
                            if '频繁' in error_msg or reply_result.get('code') == -509:
                                self.log("触发频率限制，等待60秒...", 'warning')
                                time.sleep(60)
                            # 如果是风控相关错误，给出提示
                            if '风控' in error_msg or '拦截' in error_msg or '非JSON' in error_msg:
                                self.log("提示: 可能是B站风控拦截，请尝试：", 'warning')
                                self.log("  1. 检查Cookie是否有效", 'warning')
                                self.log("  2. 等待一段时间再试", 'warning')
                                self.log("  3. 在浏览器中手动回复一次", 'warning')
                        
                        # 每次回复后等待一段时间，避免触发频率限制
                        time.sleep(5)
                
                # 等待下一次检查
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"监控循环异常: {str(e)}")
                self.log(f"监控异常: {str(e)}", 'error')
                time.sleep(self.check_interval)
    
    def log(self, message: str, level: str = 'info'):
        """输出日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        if self.gui:
            self.gui.add_log(log_message, level)
        
        if level == 'error':
            logger.error(message)
        elif level == 'warning':
            logger.warning(message)
        else:
            logger.info(message)


class BilibiliAutoReplyGUI:
    """B站自动回复GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("B站自动回复工具 v1.0")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 设置窗口图标（如果有的话）
        # self.root.iconbitmap('icon.ico')
        
        # 初始化管理器
        self.manager = AutoReplyManager(self)
        
        # 加载配置
        self.config = self.load_config()
        
        # 创建界面
        self.create_widgets()
        
        # 应用配置
        self.apply_config()
        
        # 设置关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky='nsew')
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # ===== Cookie设置区域 =====
        cookie_frame = ttk.LabelFrame(main_frame, text="Cookie设置", padding="10")
        cookie_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=5)
        cookie_frame.columnconfigure(1, weight=1)
        
        # SESSDATA
        ttk.Label(cookie_frame, text="SESSDATA:").grid(row=0, column=0, sticky='w', padx=5)
        self.sessdata_var = StringVar()
        self.sessdata_entry = ttk.Entry(cookie_frame, textvariable=self.sessdata_var, show='*')
        self.sessdata_entry.grid(row=0, column=1, sticky='ew', padx=5)
        
        # CSRF Token
        ttk.Label(cookie_frame, text="CSRF Token:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.csrf_var = StringVar()
        self.csrf_entry = ttk.Entry(cookie_frame, textvariable=self.csrf_var, show='*')
        self.csrf_entry.grid(row=1, column=1, sticky='ew', padx=5)
        
        # 显示/隐藏按钮
        self.show_cookie_var = BooleanVar(value=False)
        ttk.Checkbutton(cookie_frame, text="显示", variable=self.show_cookie_var, 
                       command=self.toggle_cookie_visibility).grid(row=0, column=2, rowspan=2)
        
        # 获取Cookie帮助按钮
        ttk.Button(cookie_frame, text="如何获取Cookie?", command=self.show_cookie_help).grid(row=0, column=3, rowspan=2, padx=5)
        
        # ===== 监控设置区域 =====
        monitor_frame = ttk.LabelFrame(main_frame, text="监控设置", padding="10")
        monitor_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
        monitor_frame.columnconfigure(1, weight=1)
        monitor_frame.columnconfigure(3, weight=1)
        
        # 目标UID
        ttk.Label(monitor_frame, text="目标用户UID:").grid(row=0, column=0, sticky='w', padx=5)
        self.uid_var = StringVar()
        self.uid_entry = ttk.Entry(monitor_frame, textvariable=self.uid_var)
        self.uid_entry.grid(row=0, column=1, sticky='ew', padx=5)
        
        # 检查间隔
        ttk.Label(monitor_frame, text="检查间隔(秒):").grid(row=0, column=2, sticky='w', padx=5)
        self.interval_var = StringVar(value="30")
        self.interval_entry = ttk.Entry(monitor_frame, textvariable=self.interval_var, width=10)
        self.interval_entry.grid(row=0, column=3, sticky='w', padx=5)
        
        # 调试模式
        self.debug_mode_var = BooleanVar(value=False)
        ttk.Checkbutton(monitor_frame, text="调试模式(显示详细日志)", variable=self.debug_mode_var, 
                       command=self.toggle_debug_mode).grid(row=1, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        # ===== 回复内容区域 =====
        reply_frame = ttk.LabelFrame(main_frame, text="回复内容列表（每行一条，将按顺序循环使用）", padding="10")
        reply_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
        reply_frame.columnconfigure(0, weight=1)
        reply_frame.rowconfigure(0, weight=1)
        
        self.reply_text = scrolledtext.ScrolledText(reply_frame, height=6, wrap=TK_WORD)
        self.reply_text.grid(row=0, column=0, sticky='nsew')
        
        # 回复按钮区域
        reply_btn_frame = ttk.Frame(reply_frame)
        reply_btn_frame.grid(row=0, column=1, sticky='ns', padx=5)
        
        ttk.Button(reply_btn_frame, text="添加示例", command=self.add_example_replies).pack(pady=2)
        ttk.Button(reply_btn_frame, text="清空", command=self.clear_replies).pack(pady=2)
        
        # ===== 控制按钮区域 =====
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(control_frame, text="开始监控", command=self.start_monitoring, width=15)
        self.start_btn.pack(side=LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="停止监控", command=self.stop_monitoring, width=15, state='disabled')
        self.stop_btn.pack(side=LEFT, padx=5)
        
        ttk.Button(control_frame, text="保存配置", command=self.save_config, width=15).pack(side=LEFT, padx=5)
        ttk.Button(control_frame, text="测试连接", command=self.test_connection, width=15).pack(side=LEFT, padx=5)
        
        # ===== 状态区域 =====
        status_frame = ttk.LabelFrame(main_frame, text="运行状态", padding="10")
        status_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=5)
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w')
        
        # ===== 日志区域 =====
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.grid(row=5, column=0, columnspan=2, sticky='nsew', pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=TK_WORD, state='disabled')
        self.log_text.grid(row=0, column=0, sticky='nsew')
        
        # 日志按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.grid(row=0, column=1, sticky='ns', padx=5)
        
        ttk.Button(log_btn_frame, text="清空日志", command=self.clear_log).pack(pady=2)
        ttk.Button(log_btn_frame, text="保存日志", command=self.save_log).pack(pady=2)
        
        # 添加右键菜单
        self.create_context_menu()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="复制", command=self.copy_selection)
        self.context_menu.add_command(label="粘贴", command=self.paste_selection)
        
        # 绑定右键事件
        for widget in [self.log_text, self.reply_text]:
            widget.bind('<Button-3>', self.show_context_menu)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def copy_selection(self):
        """复制选中的文本"""
        try:
            selected = self.root.focus_get().selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
        except:
            pass
    
    def paste_selection(self):
        """粘贴文本"""
        try:
            widget = self.root.focus_get()
            text = self.root.clipboard_get()
            widget.insert(INSERT, text)
        except:
            pass
    
    def toggle_cookie_visibility(self):
        """切换Cookie显示/隐藏"""
        show = self.show_cookie_var.get()
        char = '' if show else '*'
        self.sessdata_entry.config(show=char)
        self.csrf_entry.config(show=char)
    
    def toggle_debug_mode(self):
        """切换调试模式"""
        debug_mode = self.debug_mode_var.get()
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        if debug_mode:
            self.add_log("调试模式已开启，将显示详细日志", 'warning')
        else:
            self.add_log("调试模式已关闭", 'info')
    
    def show_cookie_help(self):
        """显示获取Cookie的帮助"""
        help_text = """如何获取Cookie：

1. 使用Chrome/Edge浏览器登录B站
2. 按F12打开开发者工具
3. 切换到"网络/Network"标签
4. 刷新页面，找到任意一个api请求
5. 在请求头中找到"Cookie"字段
6. 复制其中的SESSDATA和bili_jct值

注意：
- Cookie有效期约1-2个月，过期后需要重新获取
- 请勿泄露Cookie给他人，以免账号被盗
- 建议定期更换密码以保证安全"""
        
        messagebox.showinfo("获取Cookie帮助", help_text)
    
    def add_example_replies(self):
        """添加示例回复"""
        examples = """感谢回复~
收到你的消息啦！
谢谢支持！
欢迎常来交流~
已收到，感谢互动！"""
        
        current = self.reply_text.get('1.0', END).strip()
        if current:
            self.reply_text.insert(END, '\n' + examples)
        else:
            self.reply_text.insert('1.0', examples)
    
    def clear_replies(self):
        """清空回复内容"""
        if messagebox.askyesno("确认", "确定要清空所有回复内容吗？"):
            self.reply_text.delete('1.0', END)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', END)
        self.log_text.config(state='disabled')
    
    def save_log(self):
        """保存日志到文件"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if filename:
                log_content = self.log_text.get('1.0', END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("成功", f"日志已保存到: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存日志失败: {str(e)}")
    
    def add_log(self, message: str, level: str = 'info'):
        """添加日志到文本框"""
        self.log_text.config(state='normal')
        
        # 根据级别设置标签颜色
        tag = level
        if level == 'error':
            self.log_text.tag_config('error', foreground='red')
        elif level == 'warning':
            self.log_text.tag_config('warning', foreground='orange')
        elif level == 'success':
            self.log_text.tag_config('success', foreground='green')
        
        self.log_text.insert(END, message + '\n', tag)
        self.log_text.see(END)  # 自动滚动到底部
        self.log_text.config(state='disabled')
    
    def apply_config(self):
        """应用配置到界面"""
        self.sessdata_var.set(self.config.get('sessdata', ''))
        self.csrf_var.set(self.config.get('csrf', ''))
        self.uid_var.set(self.config.get('target_uid', ''))
        self.interval_var.set(str(self.config.get('interval', 30)))
        
        replies = self.config.get('replies', [])
        if replies:
            self.reply_text.delete('1.0', END)
            self.reply_text.insert('1.0', '\n'.join(replies))
    
    def get_current_config(self) -> dict:
        """获取当前配置"""
        return {
            'sessdata': self.sessdata_var.get().strip(),
            'csrf': self.csrf_var.get().strip(),
            'target_uid': self.uid_var.get().strip(),
            'interval': int(self.interval_var.get() or 30),
            'replies': [r.strip() for r in self.reply_text.get('1.0', END).strip().split('\n') if r.strip()]
        }
    
    def save_config(self):
        """保存配置"""
        try:
            config = self.get_current_config()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", "配置已保存")
            self.add_log("配置已保存", 'success')
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
    
    def load_config(self) -> dict:
        """加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载配置失败: {str(e)}")
        return {}
    
    def test_connection(self):
        """测试连接"""
        sessdata = self.sessdata_var.get().strip()
        csrf = self.csrf_var.get().strip()
        
        if not sessdata or not csrf:
            messagebox.showwarning("警告", "请先填写Cookie信息")
            return
        
        self.manager.set_credentials(sessdata, csrf)
        
        # 在新线程中测试
        def test():
            self.add_log("正在测试连接...")
            result = self.manager.api.get_reply_messages()
            
            if result['success']:
                self.add_log("连接成功！Cookie有效", 'success')
                # 获取用户信息
                user_result = self.manager.api.get_user_info(0)  # 0表示获取自己的信息
                if user_result['success']:
                    user_data = user_result['data']
                    self.add_log(f"当前登录用户: {user_data.get('name', '未知')}", 'success')
            else:
                self.add_log(f"连接失败: {result.get('message', '未知错误')}", 'error')
        
        threading.Thread(target=test, daemon=True).start()
    
    def start_monitoring(self):
        """开始监控"""
        # 获取并验证输入
        sessdata = self.sessdata_var.get().strip()
        csrf = self.csrf_var.get().strip()
        uid_str = self.uid_var.get().strip()
        interval_str = self.interval_var.get().strip()
        replies = self.reply_text.get('1.0', END).strip()
        
        # 验证
        if not sessdata or not csrf:
            messagebox.showwarning("警告", "请填写Cookie信息")
            return
        
        if not uid_str:
            messagebox.showwarning("警告", "请填写目标用户UID")
            return
        
        try:
            uid = int(uid_str)
        except ValueError:
            messagebox.showerror("错误", "UID必须是数字")
            return
        
        if not replies:
            messagebox.showwarning("警告", "请填写至少一条回复内容")
            return
        
        try:
            interval = int(interval_str)
            if interval < 10:
                messagebox.showwarning("警告", "检查间隔不能小于10秒")
                return
        except ValueError:
            interval = 30
        
        # 设置管理器参数
        self.manager.set_credentials(sessdata, csrf)
        self.manager.set_target_uid(uid)
        self.manager.set_reply_list(replies.split('\n'))
        self.manager.set_check_interval(interval)
        
        # 更新UI状态
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_var.set("监控中...")
        
        # 开始监控
        self.manager.start_monitoring()
    
    def stop_monitoring(self):
        """停止监控"""
        self.manager.stop_monitoring()
        
        # 更新UI状态
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_var.set("已停止")
    
    def on_close(self):
        """关闭窗口"""
        if self.manager.running:
            if messagebox.askyesno("确认", "监控正在运行，确定要退出吗？"):
                self.manager.stop_monitoring()
            else:
                return
        
        self.save_config()
        self.root.destroy()


def main():
    """主函数"""
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 创建主窗口
    root = Tk()
    
    # 设置DPI感知（Windows）
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    # 创建应用
    app = BilibiliAutoReplyGUI(root)
    
    # 运行主循环
    root.mainloop()


if __name__ == '__main__':
    main()
