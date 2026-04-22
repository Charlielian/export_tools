# -*- coding: utf-8 -*-
"""
通用数据提取工具 - GUI版本
支持多种数据表：4G干扰小区、5G干扰小区、5G小区容量报表等

使用方法：
    python universal_extractor_gui.py

特点：所有依赖模块已内嵌，可独立运行
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import sys
import time
from datetime import datetime, timedelta
import calendar
import queue
import logging
import io

# ==================== 全局日志系统 ====================
class TeeLogger:
    """同时输出到控制台和日志文件的日志系统"""
    _instance = None
    _log_file = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.handlers = []
        
    def add_file_handler(self, filepath):
        """添加文件日志处理器"""
        self._log_file = filepath
        # 创建文件handler
        handler = logging.FileHandler(filepath, encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logging.root.addHandler(handler)
        self.handlers.append(handler)
        
    def write(self, message):
        """同时输出到控制台和日志文件"""
        # 输出到控制台
        sys.__stdout__.write(message)
        # 输出到日志文件
        if self._log_file:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(message)

# 全局print替换函数
_original_print = print
_log_file_path = None

def set_log_file(filepath):
    """设置日志文件路径并启用日志记录"""
    global _log_file_path
    _log_file_path = filepath
    TeeLogger.get_instance().add_file_handler(filepath)

def debug_print(*args, **kwargs):
    """增强的print函数，同时输出到控制台和日志文件"""
    # 获取调用栈信息来确定日志级别标签
    import traceback
    stack = traceback.extract_stack()
    caller = stack[-2] if len(stack) >= 2 else None
    
    # 构建输出字符串
    output = io.StringIO()
    kwargs['file'] = output
    kwargs['end'] = kwargs.get('end', '\n')
    _original_print(*args, **kwargs)
    message = output.getvalue()
    output.close()
    
    # 添加标签前缀
    prefix = ""
    if caller:
        filename = os.path.basename(caller.filename)
        # 根据print内容判断日志级别
        msg_str = str(args[0]) if args else ""
        if '[ERROR' in msg_str or '失败' in msg_str or '异常' in msg_str:
            prefix = ""
        elif '[WARNING' in msg_str or '警告' in msg_str:
            prefix = ""
        elif '[SUCCESS' in msg_str:
            prefix = ""
        elif '[DEBUG' in msg_str:
            prefix = ""
    
    # 输出到控制台（重置file参数，使用默认的sys.stdout）
    _print_kwargs = {k: v for k, v in kwargs.items() if k != 'file'}
    _original_print(*args, **_print_kwargs)
    
    # 同时写入日志文件
    if _log_file_path:
        with open(_log_file_path, 'a', encoding='utf-8') as f:
            f.write(message)

# 替换全局print函数
print = debug_print

# ==================== 第三方依赖 ====================
import requests
import pandas as pd
from lxml import etree
try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    from Crypto.Cipher import AES as AES_Cipher
    from Crypto.Util.Padding import pad, unpad
except ModuleNotFoundError:
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Cipher import PKCS1_v1_5
    from Cryptodome.Cipher import AES as AES_Cipher
    from Cryptodome.Util.Padding import pad, unpad
import base64
from urllib.parse import quote
import random
import pickle
import json
import yaml


# ==================== 授权配置 ====================
LICENSE_FILE = "license.dat"
LICENSE_TIME_FILE = ".license_time"  # 存储上次验证时间的隐藏文件

# RSA 公钥（自动生成，请勿修改）
RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyCA2xeazcnBg2eFXryZx
SqAlLlNFzM2wArRttt5gze2ZlxMISAz74sQJ5vh7gbXZPzG+ogT5mfxrhJT4OS5d
EHvwD5O1HP52i0jTO8mGZGUem9TN7Z7VQOaknjbn83+mEY86s5atjClcs4ZwJxBt
aDyI71rpeyh4kx6C2GrJqmFoPNiGUBBhWfhRSIEA1A67AR9o7K0Fuzkk48BNbQ2V
so9ZffObodjrPpKwS56cX7FonBxb34ffJFQIe3MHxrQw4vp+SilkEJGyvYb8AUNh
VNaNG/n0A+OIX3z14GogNBUwENSKIZTTTQUc6RTLNHD4U9feMM93xNM3KNvPPfRn
nwIDAQAB
-----END PUBLIC KEY-----"""

# AES 密钥（用于加密授权时间，16字节）
LICENSE_AES_KEY = b"GMCCLicenseV2Key"  # 16字节


# ==================== 配置文件加载 ====================
def load_config():
    """从 YAML 文件加载配置"""
    config = {
        'auth': {
            'username': 'XXXXX',
            'password': 'XXXX'
        },
        'paths': {
            'output_dir': './data_output',
            'cookie_dir': './cookies',
            'captcha_dir': './captcha_images',
            'log_dir': './logs'
        },
        'server': {
            'base_url': 'https://nqi.gmcc.net:20443'
        }
    }

    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    config.update(yaml_config)
        except Exception as e:
            print(f"警告：加载配置文件失败 ({config_file}): {e}")

    return config


# ==================== 配置区域 ====================
_config = load_config()

DEFAULT_USERNAME = _config['auth']['username']
DEFAULT_PASSWORD = _config['auth']['password']
OUTPUT_DIR = _config['paths']['output_dir']
COOKIE_DIR = _config['paths']['cookie_dir']
CAPTCHA_DIR = _config['paths']['captcha_dir']
LOG_DIR = _config['paths']['log_dir']

BASE_URL = _config['server']['base_url']
LOGIN_URL = f'{BASE_URL}/cas/login?service={BASE_URL}/pro-portal/'
CAPTCHA_URL = f'{BASE_URL}/cas/captcha.jpg'
GET_CONFIG_URL = f'{BASE_URL}/cas/getConfig'
SEND_CODE_URL = f'{BASE_URL}/cas/sendCode1'
JXCX_URL = f'{BASE_URL}/pro-adhoc/adhocquery/getTable'
JXCX_COUNT_URL = f'{BASE_URL}/pro-adhoc/adhocquery/getTableCount'
JXCX_SEARCH_URL = f'{BASE_URL}/pro-adhoc/adhocquery/search'
JXCX_TABLE_URL = f'{BASE_URL}/pro-adhoc/adhocquery/getSelectTable'

# 分批查询配置
MAX_SINGLE_QUERY = 500000  # 超过此数量自动分批

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
}

HEADERS_JSON = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'Content-Type': 'application/json'
}


# ==================== 工具函数 ====================
def ensure_dirs():
    """确保必要的目录存在"""
    for dir_path in [OUTPUT_DIR, COOKIE_DIR, CAPTCHA_DIR, LOG_DIR]:
        os.makedirs(dir_path, exist_ok=True)


def save_cookie(cookie, username):
    """保存cookie到文件"""
    ensure_dirs()
    filepath = os.path.join(COOKIE_DIR, f'{username}.pkl')
    with open(filepath, 'wb') as f:
        pickle.dump(cookie, f)


def load_cookie(username):
    """从文件加载cookie"""
    filepath = os.path.join(COOKIE_DIR, f'{username}.pkl')
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    return None


def rsa_encrypt(data, public_key):
    """RSA加密"""
    public_key = '-----BEGIN PUBLIC KEY-----\n' + public_key + '\n-----END PUBLIC KEY-----'
    rsa_key = RSA.importKey(public_key)
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted_data = base64.b64encode(cipher.encrypt(data.encode(encoding="utf-8")))
    return encrypted_data.decode('utf-8')


def captcha_handle(img_content, attempt=1):
    """验证码处理（OCR识别）"""
    try:
        from PIL import Image, ImageFilter
        import pytesseract
        from io import BytesIO
        
        bytes_stream = BytesIO(img_content)
        img = Image.open(bytes_stream)
        img_gray = img.convert('L')
        img_black_white = img_gray.point(lambda x: 255 if x > 85 else 0)
        img_qucao = img_black_white.filter(ImageFilter.SMOOTH_MORE)
        img = img_qucao.convert('RGB')
        
        config = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        result = pytesseract.image_to_string(img, config=config)[0:4].replace('\n', '')
        return result
    except Exception as e:
        print(f"验证码OCR识别失败: {e}")
        ensure_dirs()
        img_path = os.path.join(CAPTCHA_DIR, f'captcha_{attempt}.jpg')
        with open(img_path, 'wb') as f:
            f.write(img_content)
        return None


# ==================== 登录模块 ====================
class LoginDialog:
    """登录对话框 - 处理验证码和短信验证"""

    def __init__(self, parent, username, password, session):
        self.username = username
        self.password = password
        self.sess = session
        self.result = False
        self.msg_code = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("登录验证")
        self.dialog.geometry("400x480")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (480 // 2)
        self.dialog.geometry(f'400x480+{x}+{y}')

        self._create_widgets()
        self._fetch_captcha()

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        """创建对话框组件"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(main_frame, text="请完成安全验证",
                 font=("Arial", 12, "bold")).pack(pady=(0, 15))

        # 验证码图片区域
        captcha_frame = ttk.LabelFrame(main_frame, text="图形验证码", padding="10")
        captcha_frame.pack(fill=tk.X, pady=10)

        self.captcha_label = ttk.Label(captcha_frame)
        self.captcha_label.pack()

        captcha_input_frame = ttk.Frame(captcha_frame)
        captcha_input_frame.pack(fill=tk.X, pady=10)

        ttk.Label(captcha_input_frame, text="验证码:").pack(side=tk.LEFT)
        self.captcha_var = tk.StringVar()
        self.captcha_entry = ttk.Entry(captcha_input_frame, textvariable=self.captcha_var, width=10)
        self.captcha_entry.pack(side=tk.LEFT, padx=10)
        self.captcha_entry.focus()

        ttk.Button(captcha_input_frame, text="刷新",
                  command=self._fetch_captcha).pack(side=tk.LEFT, padx=5)
        ttk.Button(captcha_input_frame, text="验证图形码",
                  command=self._verify_captcha).pack(side=tk.LEFT)

        self.captcha_msg = ttk.Label(captcha_frame, text="", foreground="blue")
        self.captcha_msg.pack(pady=5)

        # 短信验证码区域
        sms_frame = ttk.LabelFrame(main_frame, text="短信验证码", padding="10")
        sms_frame.pack(fill=tk.X, pady=10)

        self.sms_var = tk.StringVar()
        sms_input_frame = ttk.Frame(sms_frame)
        sms_input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(sms_input_frame, text="短信码:").pack(side=tk.LEFT)
        self.sms_entry = ttk.Entry(sms_input_frame, textvariable=self.sms_var, width=15)
        self.sms_entry.pack(side=tk.LEFT, padx=10)
        self.sms_entry.bind('<Return>', lambda e: self._submit())

        self.send_sms_btn = ttk.Button(sms_input_frame, text="发送短信",
                                       command=self._send_sms, state=tk.DISABLED)
        self.send_sms_btn.pack(side=tk.LEFT, padx=5)

        self.sms_msg = ttk.Label(sms_frame, text="请先验证图形验证码", foreground="gray")
        self.sms_msg.pack(pady=5)

        self.countdown_label = ttk.Label(sms_frame, text="", foreground="red")
        self.countdown_label.pack()

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)

        self.submit_btn = ttk.Button(btn_frame, text="确认登录",
                                    command=self._submit, width=15)
        self.submit_btn.pack(side=tk.LEFT, padx=10)

        ttk.Button(btn_frame, text="取消",
                  command=self._on_close, width=10).pack(side=tk.LEFT)

        # 状态显示
        self.status_var = tk.StringVar(value="请先输入图形验证码，点击【验证图形码】")
        ttk.Label(main_frame, textvariable=self.status_var,
                 foreground="green").pack(pady=10)

    def _verify_captcha(self):
        """验证图形验证码"""
        captcha_code = self.captcha_var.get().strip()

        if not captcha_code:
            self.captcha_msg.config(text="请输入图形验证码", foreground="red")
            self.status_var.set("请先输入图形验证码")
            return

        self.status_var.set("正在验证图形验证码...")
        self.captcha_msg.config(text="验证中...")

        try:
            public_key = None
            html_res = self.sess.get(LOGIN_URL, headers=HEADERS)
            html_res.encoding = 'utf-8'
            html = etree.HTML(html_res.text)
            public_key = html.xpath('//*[@type="text/javascript"]/text()')[0].split('setPublicKey("')[1].split('")')[0]

            username_e = rsa_encrypt(self.username, public_key)
            password_e = rsa_encrypt(self.password, public_key)

            data = {
                'password': password_e,
                'loginId': username_e,
                'captcha': captcha_code,
            }
            res = self.sess.post(GET_CONFIG_URL, data=json.dumps(data), headers=HEADERS_JSON)

            if res.status_code == 200:
                result = json.loads(res.text)
                if result.get('code') == '1':
                    self.captcha_msg.config(text="图形验证码正确 ✓", foreground="green")
                    self.captcha_entry.config(state=tk.DISABLED)
                    self.send_sms_btn.config(state=tk.NORMAL)
                    self.status_var.set("图形验证码正确！请点击【发送短信】")
                    # 保存加密后的密码供后续使用
                    self._encrypted_username = username_e
                    self._encrypted_password = password_e
                else:
                    self.captcha_msg.config(text="图形验证码错误，请重试", foreground="red")
                    self.status_var.set("图形验证码错误，请重新输入")
                    self.captcha_entry.select_clear()
                    self.captcha_entry.focus()
            else:
                self.status_var.set("验证请求失败")
        except Exception as e:
            self.status_var.set(f"验证失败: {e}")
            self.captcha_msg.config(text=f"错误: {e}", foreground="red")

    def _fetch_captcha(self):
        """获取图形验证码"""
        try:
            captcha_res = self.sess.get(CAPTCHA_URL)
            if captcha_res.status_code == 200:
                from PIL import Image, ImageTk
                from io import BytesIO

                bytes_stream = BytesIO(captcha_res.content)
                img = Image.open(bytes_stream)
                img = img.resize((200, 80), Image.Resampling.LANCZOS)
                self.captcha_photo = ImageTk.PhotoImage(img)
                self.captcha_label.config(image=self.captcha_photo)

                self.captcha_img_data = captcha_res.content
                self.captcha_var.set('')  # 清空验证码输入
                self.captcha_entry.config(state=tk.NORMAL)  # 启用输入框
                self.send_sms_btn.config(state=tk.DISABLED)
                self.status_var.set("请输入图形验证码，点击【验证图形码】")
                self.captcha_msg.config(text="请输入图片中的验证码")
                self.sms_msg.config(text="请先验证图形验证码")
                self.captcha_entry.focus()
            else:
                self.status_var.set("获取验证码失败")
        except Exception as e:
            self.status_var.set(f"获取验证码失败: {e}")

    def _send_sms(self):
        """发送短信验证码"""
        if not hasattr(self, '_encrypted_username') or not hasattr(self, '_encrypted_password'):
            self.captcha_msg.config(text="请先验证图形验证码", foreground="red")
            self.status_var.set("请先完成图形验证码验证")
            return

        self.status_var.set("正在发送短信验证码...")
        self.send_sms_btn.config(state=tk.DISABLED)

        try:
            # 发送短信
            data_sms = {'loginId': self._encrypted_username, 'password': self._encrypted_password}
            res_sms = self.sess.post(SEND_CODE_URL, data=json.dumps(data_sms), headers=HEADERS_JSON)
            result_sms = json.loads(res_sms.text)

            if result_sms.get('msg') == 'success':
                self.sms_msg.config(text="短信验证码已发送，请查收 ✓", foreground="green")
                self.status_var.set("短信已发送，请在下方输入短信验证码后按回车或点击【确认登录】")
                self._start_countdown(60)
                self.sms_entry.focus()
            else:
                self.sms_msg.config(text="短信发送失败，请重试", foreground="red")
                self.status_var.set("短信发送失败")
                self.send_sms_btn.config(state=tk.NORMAL)

        except Exception as e:
            self.sms_msg.config(text=f"发送失败: {e}", foreground="red")
            self.status_var.set(f"短信发送失败: {e}")
            self.send_sms_btn.config(state=tk.NORMAL)

    def _start_countdown(self, seconds):
        """倒计时"""
        if seconds > 0:
            self.countdown_label.config(text=f"请在 {seconds} 秒内输入")
            self.dialog.after(1000, lambda: self._start_countdown(seconds - 1))
        else:
            self.countdown_label.config(text="验证码可能已过期")

    def _submit(self):
        """提交验证"""
        msg_code = self.sms_var.get().strip()

        if not msg_code:
            self.sms_msg.config(text="请输入短信验证码", foreground="red")
            self.status_var.set("请输入短信验证码")
            return

        if not hasattr(self, '_encrypted_username') or not hasattr(self, '_encrypted_password'):
            self.sms_msg.config(text="请先完成图形验证码验证", foreground="red")
            self.status_var.set("请先完成图形验证码验证")
            return

        self.status_var.set("正在验证短信验证码...")
        self.submit_btn.config(state=tk.DISABLED)

        try:
            html_res = self.sess.get(LOGIN_URL, headers=HEADERS)
            html_res.encoding = 'utf-8'
            html = etree.HTML(html_res.text)
            execution = html.xpath('//*[@id="fm1"]/div[4]/input[1]')[0].attrib.get('value')

            login_data = {
                'password': self._encrypted_password,
                'username': self._encrypted_username,
                'msgCode': msg_code,
                'captcha': self.captcha_var.get().strip(),
                'uuid': '',
                'execution': execution,
                '_eventId': 'submit',
                'geolocation': ''
            }

            res_login = self.sess.post(LOGIN_URL, data=login_data, headers=HEADERS)

            if self.sess.cookies.get('CASTGC'):
                self.msg_code = msg_code
                self.result = True
                self.status_var.set("登录成功！")
                self.sms_msg.config(text="登录成功 ✓", foreground="green")
                self.dialog.after(500, self.dialog.destroy)
            else:
                self.sms_msg.config(text="短信验证码错误", foreground="red")
                self.status_var.set("短信验证码错误，请重试")
                self.submit_btn.config(state=tk.NORMAL)

        except Exception as e:
            self.status_var.set(f"验证失败: {e}")
            self.sms_msg.config(text=f"错误: {e}", foreground="red")
            self.submit_btn.config(state=tk.NORMAL)

    def _on_close(self):
        """关闭窗口"""
        self.result = False
        self.dialog.destroy()

    def show(self):
        """显示对话框并返回结果"""
        self.dialog.wait_window()
        return self.result


class LoginManager:
    """登录管理器"""

    def __init__(self, username=None, password=None, parent=None):
        self.username = username or DEFAULT_USERNAME
        self.password = password or DEFAULT_PASSWORD
        self.parent = parent  # GUI 父窗口
        self.sess = requests.Session()

    def login(self, try_times=3):
        """执行登录"""
        print("=" * 60)
        print("开始登录大数据平台...")
        print(f"账号: {self.username}")
        print("=" * 60)

        saved_cookie = load_cookie(self.username)
        if saved_cookie:
            self.sess.cookies = saved_cookie
            if self._check_session():
                print("✓ 使用保存的Cookie登录成功！")
                return True
            else:
                print("⚠ 保存的Cookie已失效，重新登录...")
                self.sess = requests.Session()

        for i in range(try_times):
            if self._login_once(i):
                print(f"✓ 登录成功！（尝试次数: {i+1}）")
                save_cookie(self.sess.cookies, self.username)
                return True
            else:
                print(f"⚠ 登录失败，尝试次数: {i+1}/{try_times}")

        print("✗ 登录失败，已达到最大尝试次数")
        return False

    def _check_session(self):
        """检查session是否有效"""
        try:
            url = f'{BASE_URL}/pro-wfm-biz-server/cas/login/info'
            res = self.sess.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = json.loads(res.text)
                return data.get('data', {}).get('loginId') == self.username
        except:
            pass
        return False

    def _login_once(self, attempt=0):
        """执行一次完整的登录流程"""
        try:
            # 如果有父窗口，使用 GUI 对话框
            if self.parent:
                return self._login_with_gui()

            # 否则使用命令行模式
            return self._login_with_input(attempt)

        except Exception as e:
            print(f"✗ 登录过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _login_with_gui(self):
        """使用 GUI 对话框进行登录验证"""
        dialog = LoginDialog(self.parent, self.username, self.password, self.sess)
        result = dialog.show()
        return result

    def _login_with_input(self, attempt=0):
        """使用命令行输入进行登录验证"""
        try:
            res = self.sess.get(LOGIN_URL, headers=HEADERS)
            res.encoding = 'utf-8'
            html = etree.HTML(res.text)

            execution = html.xpath('//*[@id="fm1"]/div[4]/input[1]')[0].attrib.get('value')
            public_key = html.xpath('//*[@type="text/javascript"]/text()')[0].split('setPublicKey("')[1].split('")')[0]

            username_e = rsa_encrypt(self.username, public_key)
            password_e = rsa_encrypt(self.password, public_key)

            captcha_code = None
            for i in range(10):
                captcha_res = self.sess.get(CAPTCHA_URL)

                if i < 5:
                    captcha_code = captcha_handle(captcha_res.content, attempt * 10 + i)

                if not captcha_code:
                    ensure_dirs()
                    img_path = os.path.join(CAPTCHA_DIR, f'captcha_{attempt}_{i}.jpg')
                    with open(img_path, 'wb') as f:
                        f.write(captcha_res.content)
                    captcha_code = input(f'请查看图片 {img_path} 并输入验证码: ')

                data = {
                    'password': password_e,
                    'loginId': username_e,
                    'captcha': captcha_code,
                }
                res = self.sess.post(GET_CONFIG_URL, data=json.dumps(data), headers=HEADERS_JSON)

                if res.status_code == 200:
                    result = json.loads(res.text)
                    if result.get('code') == '1':
                        print(f"✓ 图形验证码验证通过（尝试次数: {i+1}）")
                        break
                    else:
                        print(f"⚠ 图形验证码错误，重试...")
                        captcha_code = None
            else:
                print("✗ 图形验证码验证失败次数过多")
                return False

            if attempt == 0:
                data_sms = {'loginId': username_e, 'password': password_e}
                res_sms = self.sess.post(SEND_CODE_URL, data=json.dumps(data_sms), headers=HEADERS_JSON)
                result_sms = json.loads(res_sms.text)
                if result_sms.get('msg') == 'success':
                    print("✓ 短信验证码已发送")
                else:
                    print("⚠ 短信验证码发送失败")

            msg_code = input('请输入短信验证码: ')

            login_data = {
                'password': password_e,
                'username': username_e,
                'msgCode': msg_code,
                'captcha': captcha_code,
                'uuid': '',
                'execution': execution,
                '_eventId': 'submit',
                'geolocation': ''
            }

            res_login = self.sess.post(LOGIN_URL, data=login_data, headers=HEADERS)

            if self.sess.cookies.get('CASTGC'):
                return True
            else:
                print("⚠ 短信验证码错误")
                return False

        except Exception as e:
            print(f"✗ 登录过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False


# ==================== 即席查询模块 ====================
class JXCXQuery:
    """即席查询类"""
    
    def __init__(self, session):
        self.sess = session
        self.enabled = False
        self._field_config_cache = {}
    
    def get_field_config(self, table_key, fieldtype, api_type='search'):
        """动态获取表字段配置（从API获取，而非硬编码）
        
        Args:
            table_key: API查询关键字
            fieldtype: 字段类型过滤条件
            api_type: API类型，'search'使用adhocquery/search接口，'table'使用adhocquery/getSelectTable接口
        """
        cache_key = f"{table_key}_{fieldtype}_{api_type}"
        if cache_key in self._field_config_cache:
            print(f"[DEBUG-FIELD] 使用缓存的字段配置: {cache_key}")
            return self._field_config_cache[cache_key]
        
        print(f"[DEBUG-FIELD] 动态获取字段配置: table_key={table_key}, fieldtype={fieldtype}, api_type={api_type}")
        
        try:
            if api_type == 'table':
                # 5G/4G KPI报表使用getSelectTable接口
                data = {'tablename': table_key}
                res = self.sess.post(JXCX_TABLE_URL, data=data, headers=HEADERS, timeout=30)
                
                if res.status_code == 200:
                    result = json.loads(res.content)
                    configs = result.get('CFG_ADHOC_CONF_TABLE', [])
                    print(f"[DEBUG-FIELD] 从getSelectTable接口获取到 {len(configs)} 个字段配置")
                    
                    self._field_config_cache[cache_key] = configs
                    return configs
                else:
                    print(f"[ERROR-FIELD] 获取字段配置失败: {res.status_code}")
                    return None
            else:
                # VoLTE/EPSFB/VONR使用search接口
                data = {
                    'key': table_key,
                    'field': 'columnname_cn',
                    'field': 'columnname',
                    'field': 'fieldtype',
                    'field': 'datatype',
                    'field': 'tablename',
                    'field': 'tablename_cn',
                    'field': 'columntype',
                    'field': 'sort'
                }
                res = self.sess.post(JXCX_SEARCH_URL, data=data, headers=HEADERS, timeout=30)
                
                if res.status_code == 200:
                    result = json.loads(res.content)
                    configs = result.get('CFG_ADHOC_CONF_SEARCH', [])
                    print(f"[DEBUG-FIELD] 从search接口获取到 {len(configs)} 个字段配置")
                    
                    self._field_config_cache[cache_key] = configs
                    return configs
                else:
                    print(f"[ERROR-FIELD] 获取字段配置失败: {res.status_code}")
                    return None
        except Exception as e:
            print(f"[ERROR-FIELD] 获取字段配置异常: {e}")
            return None
    
    def build_payload_from_config(self, table_key, fieldtype, where_conditions, api_type='search'):
        """从动态获取的字段配置构建payload
        
        Args:
            table_key: API查询关键字
            fieldtype: 字段类型过滤条件
            where_conditions: 查询条件列表
            api_type: API类型，'search'使用adhocquery/search接口，'table'使用adhocquery/getSelectTable接口
        """
        configs = self.get_field_config(table_key, fieldtype, api_type)
        if not configs:
            return None
        
        print(f"[DEBUG-PAYLOAD] API返回的字段配置数量: {len(configs)}")
        print(f"[DEBUG-PAYLOAD] API返回的字段名(前10个): {[c.get('columnname', '') for c in configs[:10]]}")
        print(f"[DEBUG-PAYLOAD] API返回的fieldtype(前3个): {list(set(c.get('fieldtype', '') for c in configs[:3]))}")
        
        # 按sort排序
        sorted_configs = sorted(configs, key=lambda x: x.get('sort', 0))
        
        # 从配置中获取维度参数（第一个配置项包含这些信息）
        first_config = sorted_configs[0]
        geographicdimension = first_config.get('geographicdimension', '小区')
        timedimension = first_config.get('timedimension', '天')
        enodeb_field = first_config.get('enodeb_field', 'enodeb_id')
        cgi_field = first_config.get('cgi_field', 'cgi')
        time_field = first_config.get('time_field', 'starttime')
        cell_field = first_config.get('cell_field', 'cell')
        city_field = first_config.get('city_field', 'city')
        
        print(f"[DEBUG-PAYLOAD] 从API获取维度参数:")
        print(f"  geographicdimension: {geographicdimension}")
        print(f"  timedimension: {timedimension}")
        print(f"  enodebField: {enodeb_field}")
        print(f"  cgiField: {cgi_field}")
        print(f"  timeField: {time_field}")
        print(f"  cellField: {cell_field}")
        print(f"  cityField: {city_field}")
        
        # 构建字段列表
        field_list = [c['columnname'] for c in sorted_configs]
        
        # 构建columns参数
        columns = []
        for field in field_list:
            columns.append({
                'data': field,
                'name': '',
                'searchable': True,
                'orderable': True,
                'search': {'value': '', 'regex': False}
            })
        
        # 构建result参数
        table_name = first_config.get('tablename', '')
        table_name_cn = first_config.get('tablename_cn', '')
        supporteddimension = first_config.get('supporteddimension')
        supportedtimedimension = first_config.get('supportedtimedimension', '')
        
        result_list = []
        for c in sorted_configs:
            result_list.append({
                'feildtype': c.get('fieldtype', ''),
                'table': c.get('tablename', ''),
                'tableName': c.get('tablename_cn', ''),
                'datatype': c.get('datatype', 'character varying'),
                'columntype': c.get('columntype', 1),
                'feildName': c.get('columnname_cn', ''),
                'feild': c.get('columnname', ''),
                'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'
            })
        
        result = {
            'result': result_list,
            'tableParams': {
                'supporteddimension': supporteddimension,
                'supportedtimedimension': supportedtimedimension
            },
            'columnname': ''
        }
        
        payload = {
            'draw': 1,
            'start': 0,
            'length': 200,
            'total': 0,
            'geographicdimension': geographicdimension,
            'timedimension': timedimension,
            'enodebField': enodeb_field,
            'cgiField': cgi_field,
            'timeField': time_field,
            'cellField': cell_field,
            'cityField': city_field,
            'columns': columns,
            'order': [{'column': 0, 'dir': 'desc'}],
            'search': {'value': '', 'regex': False},
            'result': result,
            'where': where_conditions,
            'indexcount': 0
        }
        
        print(f"[DEBUG-PAYLOAD] 构建的payload包含 {len(columns)} 个字段")
        return payload
    
    def enter_jxcx(self, retry_times=3, timeout=60):
        """进入即席查询模块"""
        print("\n[DEBUG-JXCX] ========== 进入即席查询模块 ==========")

        for attempt in range(retry_times):
            if attempt > 0:
                print(f"\n[DEBUG-JXCX] 重试第 {attempt} 次...")

            try:
                castgc = self.sess.cookies.get('CASTGC', domain='nqi.gmcc.net')
                if not castgc:
                    castgc = self.sess.cookies.get('CASTGC')

                if not castgc:
                    print("[ERROR-JXCX] 未找到CASTGC cookie")
                    continue

                print(f"[DEBUG-JXCX] CASTGC获取成功: {castgc[:20]}...")

                url = f'{BASE_URL}/pro-portal/pure/urlAction.action'
                params = {
                    'url': 'pro-adhoc/index',
                    'random': random.random(),
                    '__PID': 'JXCX',
                    'token': castgc
                }

                url_with_params = f"{url}?url={params['url']}&__PID={params['__PID']}&random={params['random']}&token={params['token']}"
                print(f"[DEBUG-JXCX] 请求URL: {url_with_params[:200]}...")

                start_time = time.time()
                res = self.sess.get(url_with_params, headers=HEADERS, timeout=timeout)
                elapsed_time = time.time() - start_time

                print(f"[DEBUG-JXCX] 响应状态码: {res.status_code}, 耗时: {elapsed_time:.2f}秒")

                if res.status_code == 200:
                    self.enabled = True
                    print("[SUCCESS-JXCX] 即席查询模块初始化成功！")
                    return True
                else:
                    print(f"[ERROR-JXCX] 进入即席查询失败，状态码: {res.status_code}")
                    continue

            except requests.exceptions.Timeout:
                print(f"[ERROR-JXCX] 请求超时 (timeout={timeout}s)")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"[ERROR-JXCX] 网络连接错误: {e}")
                continue
            except Exception as e:
                print(f"[ERROR-JXCX] 未知错误: {e}")
                continue

        print(f"[ERROR-JXCX] 进入即席查询失败，已尝试 {retry_times} 次")
        return False
    
    def get_table_count(self, payload):
        """获取查询结果行数"""
        if not self.enabled:
            self.enter_jxcx()

        key_list = ['geographicdimension', 'timedimension', 'enodebField', 'cgiField',
                    'timeField', 'cellField', 'cityField', 'result', 'where', 'indexcount',
                    'columns', 'order', 'search']
        payload_count = {key: value for key, value in payload.items() if key in key_list}
        payload_encoded = self._encode_payload(payload_count)

        print(f"[DEBUG-COUNT] 查询总数 URL: {JXCX_COUNT_URL}")
        print(f"[DEBUG-COUNT] 查询参数 (前500字符): {payload_encoded[:500]}...")

        try:
            res = self.sess.post(JXCX_COUNT_URL, data=payload_encoded, headers=HEADERS, timeout=30)
            print(f"[DEBUG-COUNT] 响应状态码: {res.status_code}")

            if res.status_code == 200:
                result = json.loads(res.content)
                print(f"[DEBUG-COUNT] 响应内容: {result}")

                # 检查是否有错误消息
                if 'message' in result and result['message']:
                    msg = str(result['message'])
                    print(f"[WARNING-COUNT] 服务器返回消息: {msg}")
                    if '不存在' in msg:
                        print(f"[WARNING-COUNT] 数据不存在，返回0")
                        return 0

                count = result.get('count', result.get('data', {}).get('total', 1000000))
                print(f"[DEBUG-COUNT] 查询到的数据行数: {count}")
                return count
        except Exception as e:
            print(f"[ERROR-COUNT] 查询异常: {e}")
            import traceback
            traceback.print_exc()
            pass
        return 1000000

    
    def get_table(self, payload, to_df=True):
        """获取查询数据（支持分批查询）"""
        import copy
        
        if not self.enabled:
            print("[DEBUG-TABLE] JXCX 未启用，尝试进入...")
            if not self.enter_jxcx():
                print("[ERROR-TABLE] 无法进入即席查询模块")
                return pd.DataFrame() if to_df else {}

        print(f"[DEBUG-TABLE] ========== 开始查询数据 ==========")
        print(f"[DEBUG-TABLE] 请求URL: {JXCX_URL}")

        # 打印表名
        if 'result' in payload and 'result' in payload['result']:
            table_names = [r.get('table', '') for r in payload['result']['result']]
            print(f"[DEBUG-TABLE] 查询表名: {set(table_names)}")

        # 打印 where 条件
        if 'where' in payload:
            print(f"[DEBUG-TABLE] 查询条件 (where): {json.dumps(payload['where'], ensure_ascii=False)}")

        # 验证 session 有效性
        castgc = self.sess.cookies.get('CASTGC', domain='nqi.gmcc.net')
        if not castgc:
            castgc = self.sess.cookies.get('CASTGC')
        print(f"[DEBUG-TABLE] CASTGC cookie 状态: {'有效' if castgc else '无效或过期'}")

        # 先获取总数
        print(f"[DEBUG-TABLE] 调用 get_table_count 获取数据总数...")
        total_count = self.get_table_count(copy.deepcopy(payload))
        print(f"[DEBUG-TABLE] 返回的总数: {total_count}")

        # 执行第一批查询或分批查询
        if total_count > MAX_SINGLE_QUERY:
            # 大数据量：使用分批查询策略获取全部数据
            print(f"[DEBUG-TABLE] 数据量{total_count}>MAX_SINGLE_QUERY({MAX_SINGLE_QUERY})，使用分批查询策略")
            data_list = self._fetch_data_batch(payload, total_count)
        else:
            # 小数据量或数据总数<=100000，直接查询
            if total_count == 0:
                print(f"[WARNING-TABLE] 数据总数为0，尝试直接查询不限制条数...")
                payload['length'] = 5000
                payload['start'] = 0
            else:
                payload['length'] = total_count
                payload['start'] = 0
                print(f"[DEBUG-TABLE] 数据量{total_count}<=MAX_SINGLE_QUERY({MAX_SINGLE_QUERY})，直接查询")
            
            data_list = self._fetch_data(payload)
            
            # 如果直接查询返回空数据但总数>0，尝试分批查询
            if not data_list and total_count > 0:
                print(f"[WARNING-TABLE] 直接查询返回空数据，尝试分批查询策略...")
                data_list = self._fetch_data_batch(payload, total_count)
        
        if to_df:
            en_zh_df = self._get_field_mapping(payload)
            res_df = pd.DataFrame(data_list)

            if res_df.empty:
                print(f"[WARNING-TABLE] DataFrame为空")
                return pd.DataFrame()

            print(f"[DEBUG-TABLE] 字段映射: {en_zh_df.to_dict()}")
            res_df = pd.concat([en_zh_df, res_df], ignore_index=True)
            index_first = res_df.index.tolist()[0]
            to_colname = list(res_df.loc[index_first])
            res_df.columns = to_colname
            res_df.drop(index=index_first, inplace=True)

            print(f"[SUCCESS-TABLE] 最终返回 DataFrame, shape: {res_df.shape}")
            return res_df
        else:
            return {'data': data_list}

    def _fetch_data(self, payload):
        """发送请求获取数据"""
        payload_encoded = self._encode_payload(payload)
        print(f"[DEBUG-TABLE] 编码后的参数 (前800字符): {payload_encoded[:800]}...")
        print(f"[DEBUG-TABLE] start={payload.get('start', 0)}, length={payload.get('length', 'N/A')}")

        try:
            print(f"[DEBUG-TABLE] 开始发送请求 (timeout=120s)...")
            start_request_time = time.time()
            res = self.sess.post(JXCX_URL, data=payload_encoded, headers=HEADERS, timeout=120)
            elapsed = time.time() - start_request_time
            print(f"[DEBUG-TABLE] 请求完成，耗时: {elapsed:.2f}秒，状态码: {res.status_code}")

            if res.status_code != 200:
                print(f"[ERROR-TABLE] 请求失败，状态码: {res.status_code}")
                print(f"[ERROR-TABLE] 响应内容: {res.text[:500]}")
                return []

            result = json.loads(res.content)
            print(f"[DEBUG-TABLE] 响应JSON keys: {result.keys()}")

            # 打印 recordsFiltered 和 recordsTotal（DataTables 分页信息）
            records_filtered = result.get('recordsFiltered', 'N/A')
            records_total = result.get('recordsTotal', 'N/A')
            print(f"[DEBUG-TABLE] recordsFiltered: {records_filtered}, recordsTotal: {records_total}")

            # 打印可能的错误信息
            if 'msg' in result:
                print(f"[DEBUG-TABLE] 响应消息: {result['msg']}")
            if 'message' in result and result['message']:
                print(f"[DEBUG-TABLE] 响应消息: {result['message']}")

            # 检查是否有错误
            if 'message' in result and result['message']:
                if '不存在' in str(result['message']):
                    print(f"[WARNING-TABLE] 服务器返回: 数据不存在")
                    return []

            data_list = result.get('data') or []
            print(f"[DEBUG-TABLE] 返回数据条数: {len(data_list)}")
            if data_list:
                print(f"[DEBUG-TABLE] 数据样例 (第一条): {data_list[0]}")
            else:
                # data 为空时，也打印完整响应以便排查问题
                print(f"[DEBUG-TABLE] data为空，打印完整响应以便分析: {json.dumps(result, ensure_ascii=False)[:3000]}")

            return data_list

        except Exception as e:
            print(f"[ERROR-TABLE] 请求异常: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _fetch_data_batch(self, original_payload, total_count):
        """分批查询数据（支持自动调整批次大小）"""
        import copy
        
        # 尝试确定服务器支持的批次大小
        BATCH_SIZES = [50000, 10000, 5000, 2000, 1000, 500, 200]  # 从大到小尝试
        BATCH_SIZE = BATCH_SIZES[0]
        
        all_data = []
        start = 0
        
        print(f"[DEBUG-BATCH] 开始分批查询，总数: {total_count}")
        
        # 先测试服务器支持的批次大小
        for test_size in BATCH_SIZES:
            test_payload = copy.deepcopy(original_payload)
            test_payload['start'] = 0
            test_payload['length'] = test_size
            test_data = self._fetch_data(test_payload)
            
            if test_data:
                BATCH_SIZE = test_size
                all_data.extend(test_data)
                start = test_size
                print(f"[DEBUG-BATCH] 服务器支持批次大小: {BATCH_SIZE}，已获取 {len(all_data)} 条数据")
                break
            else:
                print(f"[DEBUG-BATCH] 批次大小 {test_size} 返回空数据，尝试更小的批次...")
        
        if not all_data:
            print(f"[WARNING-BATCH] 所有批次大小测试均返回空数据")
            return []
        
        # 继续分批获取剩余数据
        while start < total_count:
            payload = copy.deepcopy(original_payload)
            payload['start'] = start
            payload['length'] = BATCH_SIZE
            
            print(f"[DEBUG-BATCH] 查询批次: start={start}, length={BATCH_SIZE}")
            batch_data = self._fetch_data(payload)
            
            if not batch_data:
                print(f"[WARNING-BATCH] 批次 {start}~{start+BATCH_SIZE} 返回空数据，停止分批查询")
                break
            
            all_data.extend(batch_data)
            print(f"[DEBUG-BATCH] 已获取 {len(all_data)}/{total_count} 条数据")
            
            # 如果返回数据少于请求数量，说明已经是最后一批
            if len(batch_data) < BATCH_SIZE:
                print(f"[DEBUG-BATCH] 返回数据 {len(batch_data)} < 请求数量 {BATCH_SIZE}，视为最后一页")
                break
                
            start += BATCH_SIZE
            
            # 防止无限循环
            if start >= total_count:
                break
        
        print(f"[SUCCESS-BATCH] 分批查询完成，共获取 {len(all_data)} 条数据")
        return all_data
    
    def _encode_payload(self, payload):
        """编码payload为URL格式"""
        out_list = []
        for key in payload:
            # columns, order, search 使用DataTables标准的扁平URL编码格式（不是JSON）
            # result, where 使用JSON序列化
            if key == 'columns':
                # 调试：检查columns类型
                col_val = payload[key]
                if isinstance(col_val, str):
                    print(f"[DEBUG-ENCODE] columns是字符串（可能是JSON序列化后的），长度: {len(col_val)}")
                    # 如果columns是字符串（JSON序列化后的），直接使用
                    out_list.append(quote(key) + '=' + quote(col_val))
                    continue
                elif not isinstance(col_val, list):
                    print(f"[DEBUG-ENCODE] columns类型异常: {type(col_val)}")
                    out_list.append(quote(key) + '=' + quote(str(col_val)))
                    continue
                    
                # DataTables标准格式: columns[0][data]=field&columns[0][name]=&...
                col_parts = []
                for i, col in enumerate(payload[key]):
                    # 调试：检查col类型
                    if isinstance(col, str):
                        col_parts.append(f'columns[{i}]={quote(col)}')
                        continue
                    try:
                        for sub_key, sub_val in col.items():
                            if isinstance(sub_val, dict):
                                # 处理嵌套对象如 search: {'value': '', 'regex': False}
                                for ss_key, ss_val in sub_val.items():
                                    col_parts.append(f'columns[{i}][{sub_key}][{ss_key}]={quote(str(ss_val))}')
                            else:
                                col_parts.append(f'columns[{i}][{sub_key}]={quote(str(sub_val))}')
                    except AttributeError as e:
                        print(f"[DEBUG-ENCODE] columns[{i}]类型异常: {type(col)}, 值: {str(col)[:100]}")
                        continue
                out_list.append('&'.join(col_parts))
            elif key == 'order':
                # DataTables标准格式: order[0][column]=0&order[0][dir]=desc
                order_parts = []
                for i, ord_item in enumerate(payload[key]):
                    for sub_key, sub_val in ord_item.items():
                        order_parts.append(f'order[{i}][{sub_key}]={quote(str(sub_val))}')
                out_list.append('&'.join(order_parts))
            elif key == 'search':
                # DataTables标准格式: search[value]=&search[regex]=false
                search_parts = []
                for sub_key, sub_val in payload[key].items():
                    search_parts.append(f'search[{sub_key}]={quote(str(sub_val))}')
                out_list.append('&'.join(search_parts))
            elif key in ['result', 'where']:
                right = quote(json.dumps(payload[key]))
                out_list.append(quote(key) + '=' + right)
            elif type(payload[key]) is int:
                right = str(payload[key])
                out_list.append(quote(key) + '=' + right)
            else:
                right = quote(str(payload[key]))
                out_list.append(quote(key) + '=' + right)
        return '&'.join(out_list)
    
    def _get_field_mapping(self, payload):
        """获取字段中英文映射"""
        result_list = payload['result']['result']
        result_df = pd.DataFrame(result_list)
        zn = list(result_df['feildName'])
        en = list(result_df['feild'])
        en_zh_dict = dict(zip(en, zn))
        return pd.DataFrame([en_zh_dict])


# ==================== Payload模板 ====================
def get_5g_interference_payload():
    """获取5G干扰小区查询payload"""
    return {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'gnodeb_id', 'cgiField': 'cgi', 'timeField': 'starttime',
        'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '数据时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '结束时间', 'feild': 'endtime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': 'CGI', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '小区名', 'feild': 'cell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '频段', 'feild': 'freq', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '微网格标识', 'feild': 'micro_grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '全频段均值', 'feild': 'averagevalue', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': 'D1均值', 'feild': 'averagevalued1', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': 'D2均值', 'feild': 'averagevalued2', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_nr_cell_zb2_d',
             'tableName': '5G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '是否干扰小区', 'feild': 'is_interfere_5g', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'}
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=',
             'val': '2025-01-13 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<',
             'val': '2025-01-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in',
             'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }


def get_4g_interference_payload():
    """获取4G干扰小区查询payload"""
    return {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi', 'timeField': 'starttime',
        'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': '1', 'feildName': '数据时间',
             'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': '1', 'feildName': '结束时间',
             'feild': 'endtime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': '1', 'feildName': 'CGI',
             'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '小区名', 'feild': 'cell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '频段', 'feild': 'freq', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '微网格标识', 'feild': 'micro_grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '系统带宽', 'feild': 'bandwidth', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '平均干扰电平', 'feild': 'averagevalue', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G干扰报表（忙时）', 'table': 'appdbv3.a_interfere_lte_cell_zb2_d',
             'tableName': '4G干扰报表（忙时）', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '是否干扰小区', 'feild': 'is_interfere', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'}
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=',
             'val': '2025-01-13 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<',
             'val': '2025-01-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in',
             'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }


def get_5g_capacity_payload():
    """获取5G小区容量报表payload - 基于浏览器HAR抓包的实际请求"""
    print("[DEBUG-PAYLOAD] 生成 5G小区容量报表 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'enodeb_id', 'cgiField': 'ncgi',
        'timeField': 'starttime', 'cellField': 'nrcell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': '2', 'feildName': '记录开始时间',
             'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': '2', 'feildName': '记录结束时间',
             'feild': 'endtime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': '1', 'feildName': '地市',
             'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': '1', 'feildName': '责任网格',
             'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '2',
             'feildName': '小区名称', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '2',
             'feildName': 'NCGI', 'feild': 'ncgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'timestamp', 'columntype': '1',
             'feildName': '忙时', 'feild': 'busy_hour', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '网元状态', 'feild': 'state', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '厂家', 'feild': 'vendor', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '详细使用频段', 'feild': 'frequency_band_detail', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '使用频段', 'feild': 'freq', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '覆盖类型', 'feild': 'cover_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '覆盖场景', 'feild': 'cover_scene', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'boolean', 'columntype': '1',
             'feildName': '是否拉远', 'feild': 'is_remote', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '所属基站', 'feild': 'station_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '经度', 'feild': 'longitude', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '纬度', 'feild': 'latitude', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'bigint', 'columntype': '1',
             'feildName': '忙时PDCCH信道CCE占用个数', 'feild': 'bh_rru_pdcchcceutil', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '共站同覆盖小区名称', 'feild': 'sectors_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'bigint', 'columntype': '1',
             'feildName': '忙时PDCCH信道CCE可用个数', 'feild': 'bh_rru_pdcchcceavail', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时PDCCH信道CCE占用率(%)', 'feild': 'bh_pdcchcceoccupancyrate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时上行PUSCH PRB占用个数', 'feild': 'bh_rru_puschprbassn', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时上行PUSCH PRB可用个数', 'feild': 'bh_rru_puschprbtot', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时上行PRB平均利用率(%)', 'feild': 'bh_prbassnrateul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时下行PDSCH PRB占用个数', 'feild': 'bh_rru_pdschprbassn', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时下行PDSCH PRB可用个数', 'feild': 'bh_rru_pdschprbtot', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时下行PRB平均利用率(%)', 'feild': 'bh_prbassnratedl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时RLC层上行业务字节数(G)', 'feild': 'bh_rlc_upoctul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时RLC层下行业务字节数(G)', 'feild': 'bh_rlc_upoctdl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时MAC层上行业务流量(G)', 'feild': 'bh_mac_cpoctul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时MAC层下行业务流量(G)', 'feild': 'bh_mac_cpoctdl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时PDCP上行业务字节数(G)', 'feild': 'bh_pdcp_upoctul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '忙时PDCP下行业务字节数(G)', 'feild': 'bh_pdcp_upoctdl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '日RLC层上行业务字节数(G)', 'feild': 'rlc_upoctul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '日RLC层下行业务字节数(G)', 'feild': 'rlc_upoctdl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '日RLC层上下行总流量(G)', 'feild': 'rlc_upoctudl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '日MAC层上下行总流量(G)', 'feild': 'mac_cpoctudl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': '日PDCP层上下行总流量(G)', 'feild': 'pdcp_upoctudl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '2',
             'feildName': 'RRC连接平均数-忙时', 'feild': 'bh_rrc_connmean', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'boolean', 'columntype': '1',
             'feildName': '是否高负荷待扩容小区', 'feild': 'is_highload', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '2',
             'feildName': 'RRC连接最大数-忙时', 'feild': 'bh_rrc_connmax', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '2',
             'feildName': 'Flow建立请求数-忙时', 'feild': 'bh_flow_nbrattestab', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '2',
             'feildName': 'Flow建立成功数-忙时', 'feild': 'bh_flow_nbrsuccestab', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '2',
             'feildName': 'QoS Flow建立成功率-忙时', 'feild': 'bh_kpi_flowsuccconnrate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '路测网格', 'feild': 'grid_road', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '二级场景细化', 'feild': 'second_scene_detail', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时上行PRB可用空分层数', 'feild': 'bh_puschprbtot_reuse', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时上行PRB占用空分层数', 'feild': 'bh_puschprbassn_reuse', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时上行业务信道平均空分层数', 'feild': 'bh_avgdtchmimolayerul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时下行PRB可用空分层数', 'feild': 'bh_pdschprbtot_reuse', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时下行PRB占用空分层数', 'feild': 'bh_pdschprbassn_reuse', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时下行业务信道平均空分层数', 'feild': 'bh_avgdtchmimolayerdl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '上行业务信道最大空分层数', 'feild': 'maxdtchmimolayerul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '下行业务信道最大空分层数', 'feild': 'maxdtchmimolayerdl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时上行业务信道空分PRB占用率', 'feild': 'bh_dtchmimoprbassnrateul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时下行业务信道空分PRB占用率', 'feild': 'bh_dtchmimoprbassnratedl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时小区PRB利用率', 'feild': 'bh_cellprbrate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时切换进入Flow数', 'feild': 'bh_flow_nbrhoinc', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '忙时每Flow流量', 'feild': 'bh_upoctudl_perflow', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '小区带宽', 'feild': 'band_width', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '中心载频号', 'feild': 'ssbfrequenc', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '射频通道数', 'feild': 'txrxmode', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '区域类型', 'feild': 'area_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '微网格标识', 'feild': 'micro_grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '覆盖场景1', 'feild': 'cover_scene1', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '覆盖场景2', 'feild': 'cover_scene2', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '覆盖场景3', 'feild': 'cover_scene3', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'character varying', 'columntype': '1',
             'feildName': '覆盖场景4', 'feild': 'cover_scene4', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=',
             'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<',
             'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in',
             'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 1
    }
    print(f"[DEBUG-PAYLOAD] 5G小区容量报表 payload 生成完成，表名: appdbv3.a_adhoc_capacity_nr_nrcell_d，字段数: {len(payload['result']['result'])}")
    return payload


def get_important_scene_payload():
    """获取重要场景-天报表payload - 基于浏览器HAR抓包的实际请求"""
    print("[DEBUG-PAYLOAD] 生成 重要场景-天 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': '1',
             'feildName': '记录开始时间', 'feild': 'starttime',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': '1',
             'feildName': '记录结束时间', 'feild': 'endtime',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': '1',
             'feildName': '所属地市', 'feild': 'city',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': '1',
             'feildName': 'CGI', 'feild': 'cgi',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'timestamp', 'columntype': 1,
             'feildName': '自忙时', 'feild': 'busy_hour',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '详细频段', 'feild': 'freq_name',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '小区名称', 'feild': 'cell_name',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '网元状态', 'feild': 'state',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '场景', 'feild': 'scene',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '场景具体名称', 'feild': 'scene_name',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '日4G流量（GB）', 'feild': 'upoctudl',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '日峰值上行PRB平均利用率', 'feild': 'ul_prbuse_rate_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '日峰值下行PRB平均利用率', 'feild': 'dl_prbuse_rate_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '日峰值PDCCH信道CCE占用率', 'feild': 'pdcchcceutilratio_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时有效RRC连接最大数', 'feild': 'bh_effectiveconnmax',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时RRC连接最大数', 'feild': 'bh_connmax',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '自忙时有效RRC连接平均数', 'feild': 'bh_effectiveconnmean',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '自忙时空口上行业务字节数', 'feild': 'bh_upoctul',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '自忙时空口下行业务字节数', 'feild': 'bh_upoctdl',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '自忙时上行PRB平均利用率', 'feild': 'bh_ul_prbuse_rate',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '自忙时下行PRB平均利用率', 'feild': 'bh_dl_prbuse_rate',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '自忙时PDCCH信道CCE占用率', 'feild': 'bh_pdcchcceutilratio',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '无线接通率', 'feild': 'radio_succ_rate',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '无线掉线率(小区级)', 'feild': 'radio_drop_rate_cell',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '呼叫接通率(MTC+MOC)', 'feild': 'call_connect_rate',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'VOLTE掉话率', 'feild': 'volte_drop_rate',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'ESRVCC切换成功率', 'feild': 'esrvcc_ho_succ_rate',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'VOLTE语音话务量', 'feild': 'volte_voice_traffic',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '小区自忙时平均E-RAB流量', 'feild': 'bh_avg_erab',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '自忙时峰值利用率', 'feild': 'bh_peak_use_rate',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时E-RAB建立成功数', 'feild': 'bh_nbrsuccestab',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '是否高流量预警小区（集团高负荷预警）', 'feild': 'is_highflow',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '是否高负荷待扩容小区', 'feild': 'is_highload',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时PDCCH信道CCE占用个数', 'feild': 'bh_pdcchcceutil',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时PDCCH信道CCE可用个数', 'feild': 'bh_pdcchcceavail',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时下行PDSCH_PRB占用数', 'feild': 'bh_pdschprbassn',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时下行PDSCH_PRB可用数', 'feild': 'bh_pdschprbtot',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时上行PUSCH_PRB占用数', 'feild': 'bh_puschprbassn',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '自忙时上行PUSCH_PRB可用数', 'feild': 'bh_puschprbtot',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '日峰值PDCCH信道CCE占用个数', 'feild': 'pdcchcceutil_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '日峰值PDCCH信道CCE可用个数', 'feild': 'pdcchcceavail_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '日峰值下行PDSCH_PRB占用数', 'feild': 'pdschprbassn_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '日峰值下行PDSCH_PRB可用数', 'feild': 'pdschprbtot_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '日峰值上行PUSCH_PRB占用数', 'feild': 'puschprbassn_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '日峰值上行PUSCH_PRB可用数', 'feild': 'puschprbtot_max',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '设备厂家', 'feild': 'vendor',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '使用频段', 'feild': 'freq',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '流量系数', 'feild': 'flow_coefficient',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '小区带宽', 'feild': 'bandwidth',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '是否拉远', 'feild': 'is_remote',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '所属站点名称', 'feild': 'station_name',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'TCP二三次握手时延（ms)', 'feild': 'lte_soc_tcpsetup_c_007',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '大包速率(>500KB)', 'feild': 'lte_soc_http_cell_c_055',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'TCP二三次握手成功率', 'feild': 'lte_soc_tcpsetup_c_003',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '是否高流量感知问题小区', 'feild': 'is_highflow_perceive',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '等效TDD_20M载波数', 'feild': 'equivalent_20m_carrier',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '三次握手成功次数(HTTP)', 'feild': 'lte_soc_tcpsetup_021',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '三次握手成功次数(S1U)', 'feild': 'lte_soc_tcpsetup_023',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': 'TCP一、二次握手成功次数(HTTP)', 'feild': 'lte_soc_tcpsetup_027',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': 'TCP一、二次握手成功次数(S1U)', 'feild': 'lte_soc_tcpsetup_029',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'TCP建立总延时（HTTP)', 'feild': 'lte_soc_tcpsetup_030',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'TCP建立总延时(S1U)', 'feild': 'lte_soc_tcpsetup_032',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'TCP一、二次握手总延时(HTTP)', 'feild': 'lte_soc_tcpsetup_033',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': 'TCP一、二次握手总延时(S1U)', 'feild': 'lte_soc_tcpsetup_035',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '大包流量(>500KB)', 'feild': 'lte_soc_http_cell_078',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '大包总时延(>500KB)', 'feild': 'lte_soc_http_cell_079',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '所属共站同覆盖区域编号', 'feild': 'sectors_no',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '所属共站同覆盖区域名', 'feild': 'sectors_name',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'integer', 'columntype': 1,
             'feildName': '小区自忙时5M感知需求能力-用户数', 'feild': 'aim_user',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '小区自忙时5M感知需求能力-流量（GB）', 'feild': 'aim_flow',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'decimal', 'columntype': 1,
             'feildName': '小区自忙时5M感知需求能力-利用率（%）', 'feild': 'aim_utilization',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '覆盖类型', 'feild': 'cover',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '覆盖层标识', 'feild': 'coverlayer',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '容量层标识', 'feild': 'capacitylayer',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '扇区宽度', 'feild': 'sectors_width',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '小区所属区域', 'feild': 'cell_scene_name',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '经度', 'feild': 'longitude',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '维度', 'feild': 'latitude',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '天线通道数', 'feild': 'channel_numbers',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '是否扩容小区+', 'feild': 'is_dilatation',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '是否纳入载波调度', 'feild': 'is_carry',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '网络结构属性', 'feild': 'network_structure',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '小区所属区域类型', 'feild': 'cell_scene_type',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '是否本地市尾部小区', 'feild': 'is_city_tail',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '重要场景-小区天', 'table': 'appdbv3.a_overview_ispm_lte_cell_d',
             'tableName': '[管理视图]重要场景-小区天粒度', 'datatype': 'character varying', 'columntype': 1,
             'feildName': '是否全省尾部小区', 'feild': 'is_province_tail',
             'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=',
             'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<',
             'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in',
             'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    print(f"[DEBUG-PAYLOAD] 重要场景-天 payload 生成完成，表名: appdbv3.a_overview_ispm_lte_cell_d")
    return payload


def get_5g_cfg_payload():
    """获取5G小区工参报表payload"""
    print("[DEBUG-PAYLOAD] 生成 5G小区工参报表 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区，网格，地市，分公司', 'timedimension': '天粒度',
        'enodebField': 'gnodeb_id', 'cgiField': 'ncgi',
        'timeField': 'starttime', 'cellField': 'nrcell_name', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区NCGI', 'feild': 'ncgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'CGI', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名称', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '纬度', 'feild': 'latitude', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '经度', 'feild': 'longitude', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '人力区县分公司', 'feild': 'branch', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '厂家', 'feild': 'vendor', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网元状态', 'feild': 'state', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '覆盖类型', 'feild': 'cover_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '使用频段', 'feild': 'frequency_band', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '详细使用频段', 'feild': 'frequency_band_detail', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属基站id', 'feild': 'gnodeb_id', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属基站名称', 'feild': 'gnodeb_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'TAC', 'feild': 'tac', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'PCI', 'feild': 'pci', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '方位角', 'feild': 'azimuth', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '电下倾角', 'feild': 'tilt', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '挂高', 'feild': 'height', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '设备维护单位', 'feild': 'maintain_department', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '入网时间', 'feild': 'setup_time', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '一级标签', 'feild': 'cover_scene1', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '二级标签', 'feild': 'cover_scene2', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '三级标签', 'feild': 'cover_scene3', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '四级标签', 'feild': 'cover_scene4', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 网络/频段配置
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网络制式', 'feild': 'network_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '关联频段', 'feild': 'aau_freq', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区宽带', 'feild': 'bschannelbwdl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 天线配置
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '天线名称', 'feild': 'ant_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '天线类型', 'feild': 'ant_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '机械下倾角', 'feild': 'elcontroldecline', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 站点/机房信息
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '机房名称', 'feild': 'room_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属局站', 'feild': 'station_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '省内机房产品类型', 'feild': 'custowerroom_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '站点类型', 'feild': 'site_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '是否拉远', 'feild': 'is_remote', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '共享类型', 'feild': 'sharing_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 网格/地理信息
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '微网格标识', 'feild': 'micro_grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '乡镇街道', 'feild': 'town', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '路测网格', 'feild': 'grid_road', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '市场部网格责任田', 'feild': 'marketduty', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '市场部综合网格', 'feild': 'marketgrid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 其他配置
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'VIP级别', 'feild': 'vip_level', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属规划ID', 'feild': 'plan_id', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'OMC中小区名称', 'feild': 'omc_nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 资源ID
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属基站资源ID', 'feild': 'gnodeb_cuid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区资源ID', 'feild': 'nrcell_cuid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属机房资源ID', 'feild': 'room_cuid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属局站ID', 'feild': 'station_cuid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 时间戳
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '记录有效时间', 'feild': 'eff_from_date', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区工参', 'table': 'appdbv3.a_common_cfg_nr_cellant_d', 'tableName': '5G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '记录失效时间', 'feild': 'eff_to_date', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'character', 'feild': 'curr_flag', 'feildName': '', 'symbol': '=', 'val': '1', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True},
        ],
        'indexcount': 0
    }
    return payload


def get_4g_cfg_payload():
    """获取4G小区工参报表payload"""
    print("[DEBUG-PAYLOAD] 生成 4G小区工参报表 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区，网格，地市，分公司', 'timedimension': '天粒度',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'CGI', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名称', 'feild': 'cell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '纬度', 'feild': 'latitude', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '经度', 'feild': 'longitude', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '人力区县分公司', 'feild': 'branch', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '厂家', 'feild': 'vendor', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网元状态', 'feild': 'state', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '覆盖类型', 'feild': 'cover_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '使用频段', 'feild': 'frequency_band', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属基站id', 'feild': 'enodeb_id', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属基站名称', 'feild': 'enodeb_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '物理小区识别码', 'feild': 'ltecell_pci', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '跟踪区码TAC', 'feild': 'tac', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '方位角', 'feild': 'azimuth', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '电下倾角', 'feild': 'tilt', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '挂高', 'feild': 'height', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '设备维护单位', 'feild': 'maintain_department', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '入网时间', 'feild': 'usetime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '一级标签', 'feild': 'cover_scene1', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '二级标签', 'feild': 'cover_scene2', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '三级标签', 'feild': 'cover_scene3', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '四级标签', 'feild': 'cover_scene4', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 网络/频段配置
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网络制式', 'feild': 'network_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区下行带宽', 'feild': 'bandwidthdl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '中心载频的信道号', 'feild': 'ltecell_earfcn', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '上行中心载频的信道号', 'feild': 'earfcnul', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '下行中心载频的信道号', 'feild': 'earfcndl', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '功率', 'feild': 'referencesignalpower', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 天线配置
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '天线名称', 'feild': 'ant_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '天线类型', 'feild': 'ant_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '机械下倾角', 'feild': 'elcontroldecline', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '型号', 'feild': 'model', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '天线入网时间', 'feild': 'ant_usetime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '天线厂家', 'feild': 'ant_vendor', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '天线ID', 'feild': 'ant_cuid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 站点/机房信息
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属机房', 'feild': 'room_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属站点名称', 'feild': 'station_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '省内机房产品类型', 'feild': 'custowerroom_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '站点类型', 'feild': 'site_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '是否拉远', 'feild': 'is_remote', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '是否小站', 'feild': 'is_nc_cell', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '共享类型', 'feild': 'sharing_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '铁塔类型', 'feild': 'tower_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '区域类型', 'feild': 'region_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '站点新增工单流水号', 'feild': 'newsite_sn', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 网格/地理信息
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '乡镇街道', 'feild': 'town', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '路测网格', 'feild': 'grid_road', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '市场网格责任田', 'feild': 'marketduty', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '市场网格ID', 'feild': 'marketgrid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 状态/维护
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '状态', 'feild': 'status', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '维护级别', 'feild': 'maintain_level', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - OMC信息
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'OMC中小区名称', 'feild': 'omc_cellname', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'OMC中基站名称', 'feild': 'omc_site_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 规划/资源ID
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属规划ID', 'feild': 'plan_id', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '机房Cuid', 'feild': 'room_cuid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '站点ID', 'feild': 'station_cuid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            # 新增字段 - 时间戳
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '记录开始时间', 'feild': 'eff_from_date', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '记录结束时间', 'feild': 'eff_to_date', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True},
        ],
        'indexcount': 0
    }
    return payload


def _build_columns_param(field_list):
    """构建DataTables格式的columns参数"""
    columns = []
    for field in field_list:
        columns.append({
            'data': field,
            'name': '',
            'searchable': True,
            'orderable': True,
            'search': {'value': '', 'regex': False}
        })
    return columns


def get_volte_warning_payload():
    """获取VoLTE小区监控预警payload"""
    print("[DEBUG-PAYLOAD] 生成 VoLTE小区监控预警 payload")
    
    # VoLTE表完整字段列表（89个字段）
    volte_fields = [
        'starttime', 'city', 'cgi', 'grid', 'area', 'nrcell_name',
        'cs_reg1_suss_rate', 'cs_reg_suss_rate', 'cs_reg_sbc_suss_rate',
        'cs_moc_sbc_suss_rate', 'cs_moc_sbc_180_suss_rate', 'cs_mtc_sbc_suss_rate', 'cs_mtc_sbc_180_suss_rate',
        'cs_sbc_suss_rate', 'cs_sbc_180_suss_rate', 'cs_moc_sbc_net_suss_rate', 'cs_sbc_net_suss_rate',
        'cs_sbc_drops_rate', 'cs_xsrvcc_ho_suss_rate', 'cs_ho_len_avg', 'cs_ho_rtp_delay_avg',
        'cs_alert_delay_vf_avg', 'cs_alert_delay_vv_avg', 'cs_alert_delay_vall_rate', 'cs_mt_alert_delay_avg',
        'mconv_rtp_ul_mos_avg', 'mconv_rtp_dl_mos_avg', 'mconv_mos_300_nok_rate',
        'mconv_rtcp_ul_mos_avg', 'mconv_rtcp_dl_mos0', 'mconv_rtp_ul_pkts_lost_rate',
        'mconv_rtp_dl_pkts_lost_rate', 'mconv_rtcp_ul_pkts_lost_rate', 'mconv_rtcp_dl_pkts_lost_rate',
        'mconv_single_voice_call_rate', 'mconv_dx_call_rate', 'mconv_rtp_ul_delay_avg', 'mconv_rtp_dl_delay_avg',
        'mconv_rtcp_ul_delay_avg', 'mconv_rtcp_dl_delay_avg', 'mconv_dl_mos_300_nok_rate',
        'msli_ul_tunzi_len_rate', 'msli_ul_duanxu_len_rate', 'msli_ul_dantong_len_rate', 'msli_ul_mos_poor_len_rate',
        'msli_dl_tunzi_len_rate', 'msli_dl_duanxu_len_rate', 'msli_dl_dantong_len_rate', 'msli_dl_mos_poor_len_rate',
        'msli_ul_mos_v2v_avg', 'msli_ul_mos_v2f_avg', 'msli_ul_mos_v2n_avg', 'msli_ul_mos_v2cs_avg', 'msli_ul_mos_v2all_avg',
        'msli_dl_mos_v2v_avg', 'msli_dl_mos_v2f_avg', 'msli_dl_mos_v2n_avg', 'msli_dl_mos_v2cs_avg', 'msli_dl_mos_v2all_avg',
        'msli_ul_rtp_lost_rate', 'msli_dl_rtp_lost_rate',
        'volte_sbc_net_suss', 'volte_sbc_net_sums', 'volte_sbc_drops', 'volte_sbc_ans',
        'volte_local_radio_single_voice_call', 'volte_local_radio_dx_call', 'volte_ans_voice_call',
        'volte_local_radio_dtdx_rate', 'volte_ul_tunzi_len', 'volte_ul_dantong_len', 'volte_ul_duanxu_len', 'volte_ul_voice_sum_len',
        'volte_dl_tunzi_len', 'volte_dl_dantong_len', 'volte_dl_duanxu_len', 'volte_dl_voice_sum_len',
        'micro_grid', 'cover_scene1', 'cover_scene2', 'cover_scene3', 'cover_scene4',
        'grid_road', 'marketduty', 'vendor', 'state', 'coverage_type', 'network_type', 'freq'
    ]
    
    # result中的字段定义（关键字段）
    result_fields = [
        {'feild': 'starttime', 'feildName': '时间', 'datatype': '1'},
        {'feild': 'city', 'feildName': '地市', 'datatype': 'character varying'},
        {'feild': 'cgi', 'feildName': '小区', 'datatype': 'character varying'},
        {'feild': 'grid', 'feildName': '责任网格', 'datatype': 'character varying'},
        {'feild': 'area', 'feildName': '区县', 'datatype': 'character varying'},
        {'feild': 'nrcell_name', 'feildName': '小区名称', 'datatype': 'character varying'},
        {'feild': 'cs_reg1_suss_rate', 'feildName': '初始注册成功率（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_reg_suss_rate', 'feildName': 'VoLTE注册成功率（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_reg_sbc_suss_rate', 'feildName': 'SBC注册成功率（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_moc_sbc_suss_rate', 'feildName': '始呼接通率（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_moc_sbc_180_suss_rate', 'feildName': '始呼接通率(180)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_mtc_sbc_suss_rate', 'feildName': '终呼接通率（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_mtc_sbc_180_suss_rate', 'feildName': '终呼接通率(180)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_sbc_suss_rate', 'feildName': '呼叫接通率(MOC+MTC)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_sbc_180_suss_rate', 'feildName': '呼叫接通率(180_MOC+MTC)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_moc_sbc_net_suss_rate', 'feildName': '始呼网络接通率（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_sbc_net_suss_rate', 'feildName': '网络接通率(MOC+MTC)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_sbc_drops_rate', 'feildName': 'VOLTE+掉话率（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_xsrvcc_ho_suss_rate', 'feildName': 'xSRVCC切换成功率（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_ho_len_avg', 'feildName': 'SRVCC平均切换时长(ms)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_ho_rtp_delay_avg', 'feildName': 'SRVCC平均媒体切换时长(ms)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_alert_delay_vf_avg', 'feildName': '呼叫建立平均时长(V-固网IMS)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_alert_delay_vv_avg', 'feildName': '呼叫建立平均时长(V2V)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_alert_delay_vall_rate', 'feildName': '呼叫建立平均时长(V2ALL)（控制面）', 'datatype': 'numeric'},
        {'feild': 'cs_mt_alert_delay_avg', 'feildName': '终呼平均接续时长(ms)（控制面）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtp_ul_mos_avg', 'feildName': 'RTP上行平均MOS（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtp_dl_mos_avg', 'feildName': 'RTP下行平均MOS（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_mos_300_nok_rate', 'feildName': 'RTP上行MOS 3.0 差占比率（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtcp_ul_mos_avg', 'feildName': 'RTCP上行平均MOS（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtcp_dl_mos0', 'feildName': 'RTCP下行平均MOS（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtp_ul_pkts_lost_rate', 'feildName': 'RTP上行丢包率（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtp_dl_pkts_lost_rate', 'feildName': 'RTP下行丢包率（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtcp_ul_pkts_lost_rate', 'feildName': 'RTCP上行丢包率（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtcp_dl_pkts_lost_rate', 'feildName': 'RTCP下行丢包率（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_single_voice_call_rate', 'feildName': 'VoLTE语音单通率（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_dx_call_rate', 'feildName': 'VoLTE语音断续/掉话率（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtp_ul_delay_avg', 'feildName': 'RTP上行平均时延(us)（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtp_dl_delay_avg', 'feildName': 'RTP下行平均时延(us)（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtcp_ul_delay_avg', 'feildName': 'RTCP上行平均时延(us)（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_rtcp_dl_delay_avg', 'feildName': 'RTCP下行平均时延(us)（会话）', 'datatype': 'numeric'},
        {'feild': 'mconv_dl_mos_300_nok_rate', 'feildName': 'RTP下行MOS 3.0 差占比率（会话）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_tunzi_len_rate', 'feildName': 'VoLTE语音上行质差率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_duanxu_len_rate', 'feildName': 'VoLTE语音上行断续率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_dantong_len_rate', 'feildName': 'VoLTE语音上行单通率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_mos_poor_len_rate', 'feildName': 'VoLTE上行MOS质差率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_tunzi_len_rate', 'feildName': 'VoLTE语音下行质差率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_duanxu_len_rate', 'feildName': 'VoLTE语音下行断续率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_dantong_len_rate', 'feildName': 'VoLTE语音下行单通率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_mos_poor_len_rate', 'feildName': 'VoLTE下行MOS质差率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_mos_v2v_avg', 'feildName': 'VoLTE上行平均MOS（对端VoLTE）（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_mos_v2f_avg', 'feildName': 'VoLTE上行平均MOS（对端EPS FB）（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_mos_v2n_avg', 'feildName': 'VoLTE上行平均MOS（对端VoNR）（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_mos_v2cs_avg', 'feildName': 'VoLTE上行平均MOS（对端CS）（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_mos_v2all_avg', 'feildName': 'VoLTE上行平均MOS(对端ALL)（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_mos_v2v_avg', 'feildName': 'VoLTE下行平均MOS（对端VoLTE）（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_mos_v2f_avg', 'feildName': 'VoLTE下行平均MOS（对端EPS FB）（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_mos_v2n_avg', 'feildName': 'VoLTE下行平均MOS（对端VoNR）（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_mos_v2cs_avg', 'feildName': 'VoLTE下行平均MOS（对端CS）（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_mos_v2all_avg', 'feildName': 'VoLTE下行平均MOS(对端ALL)（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_ul_rtp_lost_rate', 'feildName': '上行RTP丢包率（片段）', 'datatype': 'numeric'},
        {'feild': 'msli_dl_rtp_lost_rate', 'feildName': '下行RTP丢包率（片段）', 'datatype': 'numeric'},
        {'feild': 'volte_sbc_net_suss', 'feildName': 'VoLTE_网络接通次数(MOC+MTC)', 'datatype': 'numeric'},
        {'feild': 'volte_sbc_net_sums', 'feildName': 'VoLTE_网络试呼次数(MOC+MTC)', 'datatype': 'numeric'},
        {'feild': 'volte_sbc_drops', 'feildName': 'VoLTE_掉话次数', 'datatype': 'numeric'},
        {'feild': 'volte_sbc_ans', 'feildName': 'VoLTE_应答复次数(掉话率)', 'datatype': 'numeric'},
        {'feild': 'volte_local_radio_single_voice_call', 'feildName': 'VoLTE_语音本端无线单通通话次数', 'datatype': 'numeric'},
        {'feild': 'volte_local_radio_dx_call', 'feildName': 'VoLTE_语音本端无线断续通话次数', 'datatype': 'numeric'},
        {'feild': 'volte_ans_voice_call', 'feildName': 'VoLTE_语音通话总次数', 'datatype': 'numeric'},
        {'feild': 'volte_local_radio_dtdx_rate', 'feildName': 'VoLTE_单通断续次数占比', 'datatype': 'numeric'},
        {'feild': 'volte_ul_tunzi_len', 'feildName': 'VoLTE_语音上行质差时长(s)', 'datatype': 'numeric'},
        {'feild': 'volte_ul_dantong_len', 'feildName': 'VoLTE_语音上行单通时长(s)', 'datatype': 'numeric'},
        {'feild': 'volte_ul_duanxu_len', 'feildName': 'VoLTE_语音上行断续时长(s)', 'datatype': 'numeric'},
        {'feild': 'volte_ul_voice_sum_len', 'feildName': 'VoLTE_语音上行总时长(s)', 'datatype': 'numeric'},
        {'feild': 'volte_dl_tunzi_len', 'feildName': 'VoLTE_语音下行质差时长(s)', 'datatype': 'numeric'},
        {'feild': 'volte_dl_dantong_len', 'feildName': 'VoLTE_语音下行单通时长(s)', 'datatype': 'numeric'},
        {'feild': 'volte_dl_duanxu_len', 'feildName': 'VoLTE_语音下行断续时长(s)', 'datatype': 'numeric'},
        {'feild': 'volte_dl_voice_sum_len', 'feildName': 'VoLTE_语音下行总时长(s)', 'datatype': 'numeric'},
        {'feild': 'micro_grid', 'feildName': '微网格标识', 'datatype': 'character varying'},
        {'feild': 'cover_scene1', 'feildName': '覆盖场景1', 'datatype': 'character varying'},
        {'feild': 'cover_scene2', 'feildName': '覆盖场景2', 'datatype': 'character varying'},
        {'feild': 'cover_scene3', 'feildName': '覆盖场景3', 'datatype': 'character varying'},
        {'feild': 'cover_scene4', 'feildName': '覆盖场景4', 'datatype': 'character varying'},
        {'feild': 'grid_road', 'feildName': '网格道路', 'datatype': 'character varying'},
        {'feild': 'marketduty', 'feildName': '市场职责', 'datatype': 'character varying'},
        {'feild': 'vendor', 'feildName': '厂商', 'datatype': 'character varying'},
        {'feild': 'state', 'feildName': '网元状态', 'datatype': 'character varying'},
        {'feild': 'coverage_type', 'feildName': '覆盖类型', 'datatype': 'character varying'},
        {'feild': 'network_type', 'feildName': '网络制式', 'datatype': 'character varying'},
        {'feild': 'freq', 'feildName': '频段_无线', 'datatype': 'character varying'},
    ]
    
    # 构建result字段
    result_list = []
    for f in result_fields:
        result_list.append({
            'feildtype': 'VoLTE小区监控预警数据表-天',
            'table': 'csem.f_nk_volte_keykpi_cell_d',
            'tableName': 'VoLTE小区监控预警数据表-天',
            'datatype': f['datatype'],
            'columntype': 1,
            'feildName': f['feildName'],
            'feild': f['feild'],
            'poly': '无',
            'anyWay': '无',
            'chart': '无',
            'chartpoly': '无'
        })
    
    payload = {
        'draw': 1,
        'start': 0,
        'length': 200,
        'total': 0,
        'geographicdimension': '小区',
        'timedimension': '天',
        'enodebField': 'enodeb_id',
        'cgiField': 'cgi',
        'timeField': 'starttime',
        'cellField': 'cell',
        'cityField': 'city',
        'columns': _build_columns_param(volte_fields),
        'order': [{'column': 0, 'dir': 'desc'}],
        'search': {'value': '', 'regex': False},
        'result': {'result': result_list, 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def get_epsfb_warning_payload():
    """获取EPSFB小区监控预警payload"""
    print("[DEBUG-PAYLOAD] 生成 EPSFB小区监控预警 payload")
    
    # EPSFB表完整字段列表（153个字段）
    epsfb_fields = [
        'starttime', 'city', 'cgi', 'grid', 'area', 'nrcell_name',
        'sacs_start_moc_net_succ_rate', 'sacs_start_mtc_net_succ_rate', 'sacs_start_call_net_succ_rate',
        'sacs_start_moc_sbc_180_suss_rate', 'sacs_start_moc_sbc_suss_rate',
        'sacs_start_mtc_sbc_180_suss_rate', 'sacs_start_mtc_sbc_suss_rate',
        'sacs_start_sbc_180_suss_rate', 'sacs_start_sbc_suss_rate',
        'sacs_start_call_drop_rate', 'sacs_start_fb_succ_rate', 'sacs_start_fb_net_succ_rate',
        'sacs_start_fb_ho_succ_rate', 'sacs_start_fb_ho_net_succ_rate',
        'sacs_start_fb_rd_succ_rate', 'sacs_start_fb_rd_net_succ_rate',
        'sacs_start_fb_ho_rd_succ_rate', 'sacs_start_fb_ho_rd_net_succ_rate',
        'sacs_start_rt_succ_rate', 'sacs_start_rt_ho_succ_rate',
        'sacs_start_rt_rd_succ_rate', 'sacs_start_rt_ho_rd_succ_rate',
        'sacs_start_eps_fb_delay_avg', 'sacs_start_fb_ho_delay_avg',
        'sacs_start_fb_rd_delay_avg', 'sacs_start_fb_ho_rd_delay_avg',
        'sacs_start_eps_rt_delay_avg', 'sacs_start_rt_ho_delay_avg',
        'sacs_start_rt_rd_delay_avg', 'sacs_start_rt_ho_rd_delay_avg',
        'sacs_start_rt_25_lt_rate', 'sacs_start_rt_ho_25_lt_rate',
        'sacs_start_rt_rd_25_lt_rate', 'sacs_start_rt_ho_rd_25_lt_rate',
        'sacs_start_alert_delay_f2f_avg', 'sacs_start_alert_delay_f2v_avg',
        'sacs_start_alert_delay_f2n_avg', 'sacs_start_alert_delay_f2a_avg',
        'sacs_start_alert_delay_v2f_avg', 'sacs_start_epsfb_hold_len_avg',
        'sacs_end_moc_net_succ_rate', 'sacs_end_mtc_net_succ_rate',
        'sacs_end_call_net_succ_rate', 'sacs_end_moc_sbc_180_suss_rate',
        'sacs_end_moc_sbc_suss_rate', 'sacs_end_mtc_sbc_180_suss_rate',
        'sacs_end_mtc_sbc_suss_rate', 'sacs_end_sbc_180_suss_rate',
        'sacs_end_sbc_suss_rate', 'sacs_end_call_drop_rate',
        'sacs_end_fb_succ_rate', 'sacs_end_fb_net_succ_rate',
        'sacs_end_fb_ho_succ_rate', 'sacs_end_fb_ho_net_succ_rate',
        'sacs_end_fb_rd_succ_rate', 'sacs_end_fb_rd_net_succ_rate',
        'sacs_end_fb_ho_rd_succ_rate', 'sacs_end_fb_ho_rd_net_succ_rate',
        'sacs_end_rt_succ_rate', 'sacs_end_rt_ho_succ_rate',
        'sacs_end_rt_rd_succ_rate', 'sacs_end_rt_ho_rd_succ_rate',
        'sacs_end_eps_fb_delay_avg', 'sacs_end_fb_ho_delay_avg',
        'sacs_end_fb_rd_delay_avg', 'sacs_end_fb_ho_rd_delay_avg',
        'sacs_end_eps_rt_delay_avg', 'sacs_end_rt_ho_delay_avg',
        'sacs_end_rt_rd_delay_avg', 'sacs_end_rt_ho_rd_delay_avg',
        'sacs_end_rt_25_lt_rate', 'sacs_end_rt_ho_25_lt_rate',
        'sacs_end_rt_rd_25_lt_rate', 'sacs_end_rt_ho_rd_25_lt_rate',
        'sacs_end_alert_delay_f2f_avg', 'sacs_end_alert_delay_f2v_avg',
        'sacs_end_alert_delay_f2n_avg', 'sacs_end_alert_delay_f2a_avg',
        'sacs_end_alert_delay_v2f_avg', 'sacs_end_epsfb_hold_len_avg',
        'mconv_rtp_ul_mos_avg', 'mconv_rtp_dl_mos_avg', 'mconv_mos_300_nok_rate',
        'mconv_rtcp_ul_mos_avg', 'mconv_rtcp_dl_mos0', 'mconv_rtp_ul_pkts_lost_rate',
        'mconv_rtp_dl_pkts_lost_rate', 'mconv_rtcp_ul_pkts_lost_rate',
        'mconv_rtcp_dl_pkts_lost_rate', 'mconv_single_voice_call_rate',
        'mconv_dx_call_rate', 'mconv_rtp_ul_delay_avg', 'mconv_rtp_dl_delay_avg',
        'mconv_rtcp_ul_delay_avg', 'mconv_rtcp_dl_delay_avg', 'mconv_dl_mos_300_nok_rate',
        'msli_ul_tunzi_len_rate', 'msli_ul_duanxu_len_rate', 'msli_ul_dantong_len_rate',
        'msli_ul_mos_poor_len', 'msli_dl_tunzi_len_rate', 'msli_dl_duanxu_len_rate',
        'msli_dl_dantong_len_rate', 'msli_dl_mos_poor_len_rate',
        'msli_ul_mos_f2f_avg', 'msli_ul_mos_f2cs_avg', 'msli_ul_mos_f2all_avg',
        'msli_dl_mos_f2f_avg', 'msli_dl_mos_f2cs0', 'msli_dl_mos_f2all_avg',
        'msli_ul_rtp_lost_rate', 'msli_dl_rtp_lost_rate',
        'msli_ul_mos_f2v_avg', 'msli_ul_mos_f2n_avg',
        'msli_dl_mos_f2v_avg', 'msli_dl_mos_f2n_avg',
        'sacs_start_reg_init_succ_rate', 'sacs_start_reg_sbc_suss_rate', 'sacs_start_reg_suss_rate',
        'epsfb_sbc_net_suss', 'epsfb_sbc_net_sums', 'epsfb_sbc_drops', 'epsfb_sbc_ans',
        'epsfb_local_radio_single_voice_call', 'epsfb_local_radio_dx_call',
        'epsfb_ans_voice_call', 'epsfb_local_radio_dtdx_rate',
        'epsfb_ul_tunzi_len', 'epsfb_ul_dantong_len', 'epsfb_ul_duanxu_len',
        'epsfb_ul_voice_sum_len', 'epsfb_dl_tunzi_len', 'epsfb_dl_dantong_len',
        'epsfb_dl_duanxu_len', 'epsfb_dl_voice_sum_len',
        'micro_grid', 'cover_scene1', 'cover_scene2', 'cover_scene3', 'cover_scene4',
        'grid_road', 'marketduty', 'vendor', 'state', 'coverage_type', 'network_type', 'freq'
    ]
    
    # result中的字段定义（必须包含所有153个字段，和浏览器一致）
    result_fields = [
        {'feild': 'starttime', 'feildName': '时间', 'datatype': '1'},
        {'feild': 'city', 'feildName': '地市', 'datatype': '1'},
        {'feild': 'cgi', 'feildName': '小区', 'datatype': '1'},
        {'feild': 'grid', 'feildName': '责任网格', 'datatype': '1'},
        {'feild': 'area', 'feildName': '区县', 'datatype': '1'},
        {'feild': 'nrcell_name', 'feildName': '小区名称', 'datatype': '1'},
        {'feild': 'sacs_start_moc_net_succ_rate', 'feildName': 'EPSFB始呼网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_mtc_net_succ_rate', 'feildName': 'EPSFB终呼网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_call_net_succ_rate', 'feildName': 'EPSFB呼叫网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_moc_sbc_180_suss_rate', 'feildName': 'EPSFB始呼SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_moc_sbc_suss_rate', 'feildName': 'EPSFB始呼SBC接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_mtc_sbc_180_suss_rate', 'feildName': 'EPSFB终呼SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_mtc_sbc_suss_rate', 'feildName': 'EPSFB终呼SBC接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_sbc_180_suss_rate', 'feildName': 'EPSFB SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_sbc_suss_rate', 'feildName': 'EPSFB SBC接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_call_drop_rate', 'feildName': 'EPSFB掉话率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_succ_rate', 'feildName': 'EPSFB切换成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_net_succ_rate', 'feildName': 'EPSFB切换网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_ho_succ_rate', 'feildName': 'EPSFB切换成功（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_ho_net_succ_rate', 'feildName': 'EPSFB切换网络接通（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_rd_succ_rate', 'feildName': 'EPSFB重定向成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_rd_net_succ_rate', 'feildName': 'EPSFB重定向网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_ho_rd_succ_rate', 'feildName': 'EPSFB切换重定向成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_ho_rd_net_succ_rate', 'feildName': 'EPSFB切换重定向网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_succ_rate', 'feildName': 'EPSFB返回成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_ho_succ_rate', 'feildName': 'EPSFB返回切换成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_rd_succ_rate', 'feildName': 'EPSFB返回重定向成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_ho_rd_succ_rate', 'feildName': 'EPSFB返回切换重定向成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_eps_fb_delay_avg', 'feildName': 'EPSFB平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_ho_delay_avg', 'feildName': 'EPSFB切换平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_rd_delay_avg', 'feildName': 'EPSFB重定向平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_fb_ho_rd_delay_avg', 'feildName': 'EPSFB切换重定向平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_eps_rt_delay_avg', 'feildName': 'EPSFB返回平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_ho_delay_avg', 'feildName': 'EPSFB返回切换平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_rd_delay_avg', 'feildName': 'EPSFB返回重定向平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_ho_rd_delay_avg', 'feildName': 'EPSFB返回切换重定向平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_25_lt_rate', 'feildName': 'EPSFB返回2.5G占比（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_ho_25_lt_rate', 'feildName': 'EPSFB返回切换2.5G占比（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_rd_25_lt_rate', 'feildName': 'EPSFB返回重定向2.5G占比（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_rt_ho_rd_25_lt_rate', 'feildName': 'EPSFB返回切换重定向2.5G占比（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_f2f_avg', 'feildName': '呼叫建立平均时长(F2F)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_f2v_avg', 'feildName': '呼叫建立平均时长(F2V)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_f2n_avg', 'feildName': '呼叫建立平均时长(F2N)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_f2a_avg', 'feildName': '呼叫建立平均时长(F2ALL)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_v2f_avg', 'feildName': '呼叫建立平均时长(V2F)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_epsfb_hold_len_avg', 'feildName': 'EPSFB用户平均驻留时长（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_end_moc_net_succ_rate', 'feildName': 'EPSFB始呼网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_mtc_net_succ_rate', 'feildName': 'EPSFB终呼网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_call_net_succ_rate', 'feildName': 'EPSFB呼叫网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_moc_sbc_180_suss_rate', 'feildName': 'EPSFB始呼SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_moc_sbc_suss_rate', 'feildName': 'EPSFB始呼SBC接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_mtc_sbc_180_suss_rate', 'feildName': 'EPSFB终呼SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_mtc_sbc_suss_rate', 'feildName': 'EPSFB终呼SBC接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_sbc_180_suss_rate', 'feildName': 'EPSFB SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_sbc_suss_rate', 'feildName': 'EPSFB SBC接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_call_drop_rate', 'feildName': 'EPSFB掉话率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_succ_rate', 'feildName': 'EPSFB切换成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_net_succ_rate', 'feildName': 'EPSFB切换网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_ho_succ_rate', 'feildName': 'EPSFB切换成功（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_ho_net_succ_rate', 'feildName': 'EPSFB切换网络接通（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_rd_succ_rate', 'feildName': 'EPSFB重定向成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_rd_net_succ_rate', 'feildName': 'EPSFB重定向网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_ho_rd_succ_rate', 'feildName': 'EPSFB切换重定向成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_ho_rd_net_succ_rate', 'feildName': 'EPSFB切换重定向网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_succ_rate', 'feildName': 'EPSFB返回成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_ho_succ_rate', 'feildName': 'EPSFB返回切换成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_rd_succ_rate', 'feildName': 'EPSFB返回重定向成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_ho_rd_succ_rate', 'feildName': 'EPSFB返回切换重定向成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_eps_fb_delay_avg', 'feildName': 'EPSFB平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_ho_delay_avg', 'feildName': 'EPSFB切换平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_rd_delay_avg', 'feildName': 'EPSFB重定向平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_fb_ho_rd_delay_avg', 'feildName': 'EPSFB切换重定向平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_eps_rt_delay_avg', 'feildName': 'EPSFB返回平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_ho_delay_avg', 'feildName': 'EPSFB返回切换平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_rd_delay_avg', 'feildName': 'EPSFB返回重定向平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_ho_rd_delay_avg', 'feildName': 'EPSFB返回切换重定向平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_25_lt_rate', 'feildName': 'EPSFB返回2.5G占比（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_ho_25_lt_rate', 'feildName': 'EPSFB返回切换2.5G占比（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_rd_25_lt_rate', 'feildName': 'EPSFB返回重定向2.5G占比（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_rt_ho_rd_25_lt_rate', 'feildName': 'EPSFB返回切换重定向2.5G占比（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_f2f_avg', 'feildName': '呼叫建立平均时长(F2F)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_f2v_avg', 'feildName': '呼叫建立平均时长(F2V)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_f2n_avg', 'feildName': '呼叫建立平均时长(F2N)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_f2a_avg', 'feildName': '呼叫建立平均时长(F2ALL)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_v2f_avg', 'feildName': '呼叫建立平均时长(V2F)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_epsfb_hold_len_avg', 'feildName': 'EPSFB用户平均驻留时长（SA控制结束）', 'datatype': '1'},
        {'feild': 'mconv_rtp_ul_mos_avg', 'feildName': 'RTP上行平均MOS', 'datatype': '1'},
        {'feild': 'mconv_rtp_dl_mos_avg', 'feildName': 'RTP下行平均MOS', 'datatype': '1'},
        {'feild': 'mconv_mos_300_nok_rate', 'feildName': 'RTP上行MOS 3.0 差占比率', 'datatype': '1'},
        {'feild': 'mconv_rtcp_ul_mos_avg', 'feildName': 'RTCP上行平均MOS', 'datatype': '1'},
        {'feild': 'mconv_rtcp_dl_mos0', 'feildName': 'RTCP下行平均MOS', 'datatype': '1'},
        {'feild': 'mconv_rtp_ul_pkts_lost_rate', 'feildName': 'RTP上行丢包率', 'datatype': '1'},
        {'feild': 'mconv_rtp_dl_pkts_lost_rate', 'feildName': 'RTP下行丢包率', 'datatype': '1'},
        {'feild': 'mconv_rtcp_ul_pkts_lost_rate', 'feildName': 'RTCP上行丢包率', 'datatype': '1'},
        {'feild': 'mconv_rtcp_dl_pkts_lost_rate', 'feildName': 'RTCP下行丢包率', 'datatype': '1'},
        {'feild': 'mconv_single_voice_call_rate', 'feildName': 'EPSFB语音单通率', 'datatype': '1'},
        {'feild': 'mconv_dx_call_rate', 'feildName': 'EPSFB语音断续/掉话率', 'datatype': '1'},
        {'feild': 'mconv_rtp_ul_delay_avg', 'feildName': 'RTP上行平均时延', 'datatype': '1'},
        {'feild': 'mconv_rtp_dl_delay_avg', 'feildName': 'RTP下行平均时延', 'datatype': '1'},
        {'feild': 'mconv_rtcp_ul_delay_avg', 'feildName': 'RTCP上行平均时延', 'datatype': '1'},
        {'feild': 'mconv_rtcp_dl_delay_avg', 'feildName': 'RTCP下行平均时延', 'datatype': '1'},
        {'feild': 'mconv_dl_mos_300_nok_rate', 'feildName': 'RTP下行MOS 3.0 差占比率', 'datatype': '1'},
        {'feild': 'msli_ul_tunzi_len_rate', 'feildName': 'EPSFB语音上行质差率', 'datatype': '1'},
        {'feild': 'msli_ul_duanxu_len_rate', 'feildName': 'EPSFB语音上行断续率', 'datatype': '1'},
        {'feild': 'msli_ul_dantong_len_rate', 'feildName': 'EPSFB语音上行单通率', 'datatype': '1'},
        {'feild': 'msli_ul_mos_poor_len', 'feildName': 'EPSFB上行MOS质差时长', 'datatype': '1'},
        {'feild': 'msli_dl_tunzi_len_rate', 'feildName': 'EPSFB语音下行质差率', 'datatype': '1'},
        {'feild': 'msli_dl_duanxu_len_rate', 'feildName': 'EPSFB语音下行断续率', 'datatype': '1'},
        {'feild': 'msli_dl_dantong_len_rate', 'feildName': 'EPSFB语音下行单通率', 'datatype': '1'},
        {'feild': 'msli_dl_mos_poor_len_rate', 'feildName': 'EPSFB下行MOS质差率', 'datatype': '1'},
        {'feild': 'msli_ul_mos_f2f_avg', 'feildName': 'EPSFB上行平均MOS（对端VoLTE）', 'datatype': '1'},
        {'feild': 'msli_ul_mos_f2cs_avg', 'feildName': 'EPSFB上行平均MOS（对端CS）', 'datatype': '1'},
        {'feild': 'msli_ul_mos_f2all_avg', 'feildName': 'EPSFB上行平均MOS（对端ALL）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_f2f_avg', 'feildName': 'EPSFB下行平均MOS（对端VoLTE）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_f2cs0', 'feildName': 'EPSFB下行平均MOS（对端CS）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_f2all_avg', 'feildName': 'EPSFB下行平均MOS（对端ALL）', 'datatype': '1'},
        {'feild': 'msli_ul_rtp_lost_rate', 'feildName': '上行RTP丢包率', 'datatype': '1'},
        {'feild': 'msli_dl_rtp_lost_rate', 'feildName': '下行RTP丢包率', 'datatype': '1'},
        {'feild': 'msli_ul_mos_f2v_avg', 'feildName': 'EPSFB上行平均MOS（对端VoNR）', 'datatype': '1'},
        {'feild': 'msli_ul_mos_f2n_avg', 'feildName': 'EPSFB上行平均MOS（对端Vo5GSA）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_f2v_avg', 'feildName': 'EPSFB下行平均MOS（对端VoNR）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_f2n_avg', 'feildName': 'EPSFB下行平均MOS（对端Vo5GSA）', 'datatype': '1'},
        {'feild': 'sacs_start_reg_init_succ_rate', 'feildName': 'EPS+SA+IMS+CSCF初始注册成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_reg_sbc_suss_rate', 'feildName': 'EPS+SA+IMS+SBC注册成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_reg_suss_rate', 'feildName': 'EPS+SA+IMS+CSCF注册成功率[含重注册]（SA控制起始）', 'datatype': '1'},
        {'feild': 'epsfb_sbc_net_suss', 'feildName': 'EPSFB_网络接通次数(MOC+MTC)', 'datatype': '1'},
        {'feild': 'epsfb_sbc_net_sums', 'feildName': 'EPSFB_网络试呼次数(MOC+MTC)', 'datatype': '1'},
        {'feild': 'epsfb_sbc_drops', 'feildName': 'EPSFB_掉话次数', 'datatype': '1'},
        {'feild': 'epsfb_sbc_ans', 'feildName': 'EPSFB_应答复次数(掉话率)', 'datatype': '1'},
        {'feild': 'epsfb_local_radio_single_voice_call', 'feildName': 'EPSFB_语音本端无线单通通话次数', 'datatype': '1'},
        {'feild': 'epsfb_local_radio_dx_call', 'feildName': 'EPSFB_语音本端无线断续通话次数', 'datatype': '1'},
        {'feild': 'epsfb_ans_voice_call', 'feildName': 'EPSFB_语音通话总次数', 'datatype': '1'},
        {'feild': 'epsfb_local_radio_dtdx_rate', 'feildName': 'EPSFB_单通断续次数占比', 'datatype': '1'},
        {'feild': 'epsfb_ul_tunzi_len', 'feildName': 'EPSFB_语音上行质差时长(s)', 'datatype': '1'},
        {'feild': 'epsfb_ul_dantong_len', 'feildName': 'EPSFB_语音上行单通时长(s)', 'datatype': '1'},
        {'feild': 'epsfb_ul_duanxu_len', 'feildName': 'EPSFB_语音上行断续时长(s)', 'datatype': '1'},
        {'feild': 'epsfb_ul_voice_sum_len', 'feildName': 'EPSFB_语音上行总时长(s)', 'datatype': '1'},
        {'feild': 'epsfb_dl_tunzi_len', 'feildName': 'EPSFB_语音下行质差时长(s)', 'datatype': '1'},
        {'feild': 'epsfb_dl_dantong_len', 'feildName': 'EPSFB_语音下行单通时长(s)', 'datatype': '1'},
        {'feild': 'epsfb_dl_duanxu_len', 'feildName': 'EPSFB_语音下行断续时长(s)', 'datatype': '1'},
        {'feild': 'epsfb_dl_voice_sum_len', 'feildName': 'EPSFB_语音下行总时长(s)', 'datatype': '1'},
        {'feild': 'micro_grid', 'feildName': '微网格标识', 'datatype': '1'},
        {'feild': 'cover_scene1', 'feildName': '覆盖场景1', 'datatype': '1'},
        {'feild': 'cover_scene2', 'feildName': '覆盖场景2', 'datatype': '1'},
        {'feild': 'cover_scene3', 'feildName': '覆盖场景3', 'datatype': '1'},
        {'feild': 'cover_scene4', 'feildName': '覆盖场景4', 'datatype': '1'},
        {'feild': 'grid_road', 'feildName': '网格道路', 'datatype': '1'},
        {'feild': 'marketduty', 'feildName': '市场职责', 'datatype': '1'},
        {'feild': 'vendor', 'feildName': '厂商', 'datatype': '1'},
        {'feild': 'state', 'feildName': '网元状态', 'datatype': '1'},
        {'feild': 'coverage_type', 'feildName': '覆盖类型', 'datatype': '1'},
        {'feild': 'network_type', 'feildName': '网络制式', 'datatype': '1'},
        {'feild': 'freq', 'feildName': '频段_无线', 'datatype': '1'},
    ]
    
    # 构建result字段
    result_list = []
    for f in result_fields:
        result_list.append({
            'feildtype': 'EPSFB小区监控预警数据表-天',
            'table': 'csem.f_nk_epsfb_keykpi_cell_d',
            'tableName': 'EPSFB小区监控预警数据表-天',
            'datatype': f['datatype'],
            'columntype': 1,
            'feildName': f['feildName'],
            'feild': f['feild'],
            'poly': '无',
            'anyWay': '无',
            'chart': '无',
            'chartpoly': '无'
        })
    
    payload = {
        'draw': 1,
        'start': 0,
        'length': 200,
        'total': 0,
        'geographicdimension': '小区',
        'timedimension': '天',
        'enodebField': '---',
        'cgiField': 'cgi',
        'timeField': 'starttime',
        'cellField': 'cell',
        'cityField': 'city',
        'columns': _build_columns_param(epsfb_fields),
        'order': [{'column': 0, 'dir': 'desc'}],
        'search': {'value': '', 'regex': False},
        'result': {'result': result_list, 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def get_vonr_warning_payload():
    """获取VONR小区监控预警payload"""
    print("[DEBUG-PAYLOAD] 生成 VONR小区监控预警 payload")
    
    # VONR表完整字段列表（152个字段）
    vonr_fields = [
        'starttime', 'city', 'cgi', 'grid', 'area', 'nrcell_name',
        'sacs_start_reg_init_succ_rate', 'sacs_start_reg_suss_rate', 'sacs_start_reg_sbc_suss_rate',
        'sacs_start_vonr_moc_net_succ_rate', 'sacs_start_vonr_mtc_net_succ_rate',
        'sacs_start_vonr_call_net_succ_rate', 'sacs_start_vonr_moc_sbc_180_suss_rate',
        'sacs_start_vonr_moc_sbc_suss_rate', 'sacs_start_vonr_mtc_sbc_180_suss_rate',
        'sacs_start_vonr_mtc_sbc_suss', 'sacs_start_vonr_sbc_180_suss_rate',
        'sacs_start_vonr_sbc_suss_rate', 'sacs_start_vonr_call_drop_rate',
        'sacs_start_alert_delay_n2n_avg', 'sacs_start_alert_delay_n2v_avg',
        'sacs_start_alert_delay_n2f_avg', 'sacs_start_alert_delay_n2a_avg',
        'sacs_start_alert_delay_v2n_avg',
        'sacs_start_vo5gsa_moc_net_succ_rate', 'sacs_start_vo5gsa_mtc_net_succ_rate',
        'sacs_start_vo5gsa_call_net_succ_rate', 'sacs_start_vo5gsa_moc_sbc_180_suss_rate',
        'sacs_start_vo5gsa_moc_sbc_suss_rate', 'sacs_start_vo5gsa_mtc_sbc_180_suss_rate',
        'sacs_start_vo5gsa_mtc_sbc_suss_rate', 'sacs_start_vo5gsa_sbc_180_suss_rate',
        'sacs_start_vo5gsa_sbc_suss_rate', 'sacs_start_vo5gsa_call_drop_rate',
        'sacs_start_vo5gsa_moc_csfb_rate', 'sacs_start_vo5gsa_mtc_csfb_rate',
        'sacs_start_vo5gsa_call_csfb_rate',
        'sacs_start_vonr_hold_avg', 'sacs_start_vonr_moc_call_drop_rate',
        'sacs_start_vonr_mtc_call_drop_rate', 'sacs_start_vonr_ho_xn_succ_rate',
        'sacs_start_vonr_ho_n2_succ_rate', 'sacs_start_vonr_ho_54_succ_rate',
        'sacs_start_vonr_ho_54_c_delay_avg', 'sacs_start_vonr_ho_54_u_delay_avg',
        'CSretryRate',
        'sacs_end_reg_init_succ_rate', 'sacs_end_reg_suss_rate', 'sacs_end_reg_sbc_suss_rate',
        'sacs_end_vonr_moc_net_succ_rate', 'sacs_end_vonr_mtc_net_succ_rate',
        'sacs_end_vonr_call_net_succ_rate', 'sacs_end_vonr_moc_sbc_180_suss_rate',
        'sacs_end_vonr_moc_sbc_suss_rate', 'sacs_end_vonr_mtc_sbc_180_suss_rate',
        'sacs_end_vonr_mtc_sbc_suss', 'sacs_end_vonr_sbc_180_suss_rate',
        'sacs_end_vonr_sbc_suss_rate', 'sacs_end_vonr_call_drop_rate',
        'sacs_end_alert_delay_n2n_avg', 'sacs_end_alert_delay_n2v_avg',
        'sacs_end_alert_delay_n2f_avg', 'sacs_end_alert_delay_n2a_avg',
        'sacs_end_alert_delay_v2n_avg',
        'sacs_end_vo5gsa_moc_net_succ_rate', 'sacs_end_vo5gsa_mtc_net_succ_rate',
        'sacs_end_vo5gsa_call_net_succ_rate', 'sacs_end_vo5gsa_moc_sbc_180_suss_rate',
        'sacs_end_vo5gsa_moc_sbc_suss_rate', 'sacs_end_vo5gsa_mtc_sbc_180_suss_rate',
        'sacs_end_vo5gsa_mtc_sbc_suss_rate', 'sacs_end_vo5gsa_sbc_180_suss_rate',
        'sacs_end_vo5gsa_sbc_suss_rate', 'sacs_end_vo5gsa_call_drop_rate',
        'sacs_end_vo5gsa_moc_csfb_rate', 'sacs_end_vo5gsa_mtc_csfb_rate',
        'sacs_end_vo5gsa_call_csfb_rate',
        'sacs_end_vonr_hold_avg', 'sacs_end_vonr_moc_call_drop_rate',
        'sacs_end_vonr_mtc_call_drop_rate', 'sacs_end_vonr_ho_xn_succ_rate',
        'sacs_end_vonr_ho_n2_succ_rate', 'sacs_end_vonr_ho_54_succ_rate',
        'sacs_end_vonr_ho_54_c_delay_avg', 'sacs_end_vonr_ho_54_u_delay_avg',
        'sacs_end_vonr_ho_54_attrate',
        'mconv_rtp_ul_mos_avg', 'mconv_rtp_dl_mos_avg',
        'mconv_ul_mos_300_ok_rate', 'mconv_dl_mos_300_ok_rate',
        'mconv_ul_mos_400_ok_rate', 'mconv_dl_mos_400_ok_rate',
        'mconv_rtcp_ul_mos_avg', 'mconv_rtcp_dl_mos0', 'mconv_rtp_ul_pkts_lost_rate',
        'mconv_rtp_dl_pkts_lost_rate', 'mconv_rtcp_ul_pkts_lost_rate',
        'mconv_rtcp_dl_pkts_lost_rate', 'mconv_single_voice_call_rate',
        'mconv_dx_call_rate', 'mconv_rtp_ul_delay_avg', 'mconv_rtp_dl_delay_avg',
        'mconv_rtcp_ul_delay_avg', 'mconv_rtcp_dl_delay_avg',
        'msli_ul_tunzi_len_rate', 'msli_ul_duanxu_len_rate', 'msli_ul_dantong_len_rate',
        'msli_ul_mos_poor_len_rate', 'msli_dl_tunzi_len_rate', 'msli_dl_duanxu_len_rate',
        'msli_dl_dantong_len_rate', 'msli_dl_mos_poor_len_rate',
        'msli_ul_mos_n2n_avg', 'msli_ul_mos_n2v_avg', 'msli_ul_mos_n2f_avg',
        'msli_ul_mos_n2cs_avg', 'msli_ul_mos_n2all_avg',
        'msli_dl_mos_n2n_avg', 'msli_dl_mos_n2v_avg', 'msli_dl_mos_n2f_avg',
        'msli_dl_mos_n2cs_avg', 'msli_dl_mos_n2all_avg',
        'msli_ul_rtp_lost_rate', 'msli_dl_rtp_lost_rate',
        'vonr_sbc_net_suss', 'vonr_sbc_net_sums', 'vonr_sbc_drops', 'vonr_sbc_ans',
        'vonr_local_radio_single_voice_call', 'vonr_local_radio_dx_call',
        'vonr_ans_voice_call', 'vonr_local_radio_dtdx_rate',
        'vonr_ul_tunzi_len', 'vonr_ul_dantong_len', 'vonr_ul_duanxu_len',
        'vonr_ul_voice_sum_len', 'vonr_dl_tunzi_len', 'vonr_dl_dantong_len',
        'vonr_dl_duanxu_len', 'vonr_dl_voice_sum_len',
        'micro_grid', 'cover_scene1', 'cover_scene2', 'cover_scene3', 'cover_scene4',
        'grid_road', 'marketduty', 'vendor', 'state', 'coverage_type', 'network_type', 'freq'
    ]
    
    # result中的字段定义（必须包含所有152个字段，和columns一致）
    result_fields = [
        {'feild': 'starttime', 'feildName': '时间', 'datatype': '1'},
        {'feild': 'city', 'feildName': '地市', 'datatype': '1'},
        {'feild': 'cgi', 'feildName': '小区', 'datatype': '1'},
        {'feild': 'grid', 'feildName': '责任网格', 'datatype': '1'},
        {'feild': 'area', 'feildName': '区县', 'datatype': '1'},
        {'feild': 'nrcell_name', 'feildName': '小区名称', 'datatype': '1'},
        {'feild': 'sacs_start_reg_init_succ_rate', 'feildName': '5G SA IMS CSCF初始注册成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_reg_suss_rate', 'feildName': '5G SA IMS CSCF注册成功率[含重注册]（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_reg_sbc_suss_rate', 'feildName': '5G SA IMS SBC注册成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_moc_net_succ_rate', 'feildName': 'VoNR始呼网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_mtc_net_succ_rate', 'feildName': 'VoNR终呼网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_call_net_succ_rate', 'feildName': 'VoNR呼叫网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_moc_sbc_180_suss_rate', 'feildName': 'VoNR始呼SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_moc_sbc_suss_rate', 'feildName': 'VoNR始呼SBC接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_mtc_sbc_180_suss_rate', 'feildName': 'VoNR终呼SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_mtc_sbc_suss', 'feildName': 'VoNR终呼SBC接通数（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_sbc_180_suss_rate', 'feildName': 'VoNR SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_sbc_suss_rate', 'feildName': 'VoNR SBC接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_call_drop_rate', 'feildName': 'VoNR掉话率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_n2n_avg', 'feildName': '呼叫建立平均时长(N2N)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_n2v_avg', 'feildName': '呼叫建立平均时长(N2V)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_n2f_avg', 'feildName': '呼叫建立平均时长(N2F)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_n2a_avg', 'feildName': '呼叫建立平均时长(N2ALL)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_alert_delay_v2n_avg', 'feildName': '呼叫建立平均时长(V2N)（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_moc_net_succ_rate', 'feildName': 'Vo5GSA始呼网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_mtc_net_succ_rate', 'feildName': 'Vo5GSA终呼网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_call_net_succ_rate', 'feildName': 'Vo5GSA呼叫网络接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_moc_sbc_180_suss_rate', 'feildName': 'Vo5GSA始呼SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_moc_sbc_suss_rate', 'feildName': 'Vo5GSA始呼SBC接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_mtc_sbc_180_suss_rate', 'feildName': 'Vo5GSA终呼SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_mtc_sbc_suss_rate', 'feildName': 'Vo5GSA终呼SBC接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_sbc_180_suss_rate', 'feildName': 'Vo5GSA SBC 180接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_sbc_suss_rate', 'feildName': 'Vo5GSA SBC接通率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_call_drop_rate', 'feildName': 'Vo5GSA掉话率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_moc_csfb_rate', 'feildName': 'Vo5GSA始呼CSFB占比（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_mtc_csfb_rate', 'feildName': 'Vo5GSA终呼CSFB占比（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vo5gsa_call_csfb_rate', 'feildName': 'Vo5GSA呼叫CSFB占比（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_hold_avg', 'feildName': 'VoNR用户平均驻留时长（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_moc_call_drop_rate', 'feildName': 'VoNR始发掉话率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_mtc_call_drop_rate', 'feildName': 'VoNR终端掉话率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_ho_xn_succ_rate', 'feildName': 'VoNR系统间切换成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_ho_n2_succ_rate', 'feildName': 'VoNR系统内切换成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_ho_54_succ_rate', 'feildName': 'VoNR 5G->4G切换成功率（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_ho_54_c_delay_avg', 'feildName': 'VoNR 5G->4G切换控制面平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_start_vonr_ho_54_u_delay_avg', 'feildName': 'VoNR 5G->4G切换用户面平均时延（SA控制起始）', 'datatype': '1'},
        {'feild': 'CSretryRate', 'feildName': 'Csretry占比（%）（SA控制起始）', 'datatype': '1'},
        {'feild': 'sacs_end_reg_init_succ_rate', 'feildName': '5G SA IMS CSCF初始注册成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_reg_suss_rate', 'feildName': '5G SA IMS CSCF注册成功率[含重注册]（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_reg_sbc_suss_rate', 'feildName': '5G SA IMS SBC注册成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_moc_net_succ_rate', 'feildName': 'VoNR始呼网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_mtc_net_succ_rate', 'feildName': 'VoNR终呼网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_call_net_succ_rate', 'feildName': 'VoNR呼叫网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_moc_sbc_180_suss_rate', 'feildName': 'VoNR始呼SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_moc_sbc_suss_rate', 'feildName': 'VoNR始呼SBC接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_mtc_sbc_180_suss_rate', 'feildName': 'VoNR终呼SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_mtc_sbc_suss', 'feildName': 'VoNR终呼SBC接通数（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_sbc_180_suss_rate', 'feildName': 'VoNR SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_sbc_suss_rate', 'feildName': 'VoNR SBC接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_call_drop_rate', 'feildName': 'VoNR掉话率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_n2n_avg', 'feildName': '呼叫建立平均时长(N2N)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_n2v_avg', 'feildName': '呼叫建立平均时长(N2V)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_n2f_avg', 'feildName': '呼叫建立平均时长(N2F)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_n2a_avg', 'feildName': '呼叫建立平均时长(N2ALL)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_alert_delay_v2n_avg', 'feildName': '呼叫建立平均时长(V2N)（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_moc_net_succ_rate', 'feildName': 'Vo5GSA始呼网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_mtc_net_succ_rate', 'feildName': 'Vo5GSA终呼网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_call_net_succ_rate', 'feildName': 'Vo5GSA呼叫网络接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_moc_sbc_180_suss_rate', 'feildName': 'Vo5GSA始呼SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_moc_sbc_suss_rate', 'feildName': 'Vo5GSA始呼SBC接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_mtc_sbc_180_suss_rate', 'feildName': 'Vo5GSA终呼SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_mtc_sbc_suss_rate', 'feildName': 'Vo5GSA终呼SBC接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_sbc_180_suss_rate', 'feildName': 'Vo5GSA SBC 180接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_sbc_suss_rate', 'feildName': 'Vo5GSA SBC接通率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_call_drop_rate', 'feildName': 'Vo5GSA掉话率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_moc_csfb_rate', 'feildName': 'Vo5GSA始呼CSFB占比（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_mtc_csfb_rate', 'feildName': 'Vo5GSA终呼CSFB占比（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vo5gsa_call_csfb_rate', 'feildName': 'Vo5GSA呼叫CSFB占比（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_hold_avg', 'feildName': 'VoNR用户平均驻留时长（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_moc_call_drop_rate', 'feildName': 'VoNR始发掉话率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_mtc_call_drop_rate', 'feildName': 'VoNR终端掉话率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_ho_xn_succ_rate', 'feildName': 'VoNR系统间切换成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_ho_n2_succ_rate', 'feildName': 'VoNR系统内切换成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_ho_54_succ_rate', 'feildName': 'VoNR 5G->4G切换成功率（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_ho_54_c_delay_avg', 'feildName': 'VoNR 5G->4G切换控制面平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_ho_54_u_delay_avg', 'feildName': 'VoNR 5G->4G切换用户面平均时延（SA控制结束）', 'datatype': '1'},
        {'feild': 'sacs_end_vonr_ho_54_attrate', 'feildName': 'VoNR 5G->4G切换邻区TAM进服差占比（SA控制结束）', 'datatype': '1'},
        {'feild': 'mconv_rtp_ul_mos_avg', 'feildName': 'RTP上行平均MOS', 'datatype': '1'},
        {'feild': 'mconv_rtp_dl_mos_avg', 'feildName': 'RTP下行平均MOS', 'datatype': '1'},
        {'feild': 'mconv_ul_mos_300_ok_rate', 'feildName': 'RTP上行MOS 3.0 优占比率', 'datatype': '1'},
        {'feild': 'mconv_dl_mos_300_ok_rate', 'feildName': 'RTP下行MOS 3.0 优占比率', 'datatype': '1'},
        {'feild': 'mconv_ul_mos_400_ok_rate', 'feildName': 'RTP上行MOS 4.0 优占比率', 'datatype': '1'},
        {'feild': 'mconv_dl_mos_400_ok_rate', 'feildName': 'RTP下行MOS 4.0 优占比率', 'datatype': '1'},
        {'feild': 'mconv_rtcp_ul_mos_avg', 'feildName': 'RTCP上行平均MOS', 'datatype': '1'},
        {'feild': 'mconv_rtcp_dl_mos0', 'feildName': 'RTCP下行平均MOS', 'datatype': '1'},
        {'feild': 'mconv_rtp_ul_pkts_lost_rate', 'feildName': 'RTP上行丢包率', 'datatype': '1'},
        {'feild': 'mconv_rtp_dl_pkts_lost_rate', 'feildName': 'RTP下行丢包率', 'datatype': '1'},
        {'feild': 'mconv_rtcp_ul_pkts_lost_rate', 'feildName': 'RTCP上行丢包率', 'datatype': '1'},
        {'feild': 'mconv_rtcp_dl_pkts_lost_rate', 'feildName': 'RTCP下行丢包率', 'datatype': '1'},
        {'feild': 'mconv_single_voice_call_rate', 'feildName': 'VoNR语音单通率', 'datatype': '1'},
        {'feild': 'mconv_dx_call_rate', 'feildName': 'VoNR语音断续/掉话率', 'datatype': '1'},
        {'feild': 'mconv_rtp_ul_delay_avg', 'feildName': 'RTP上行平均时延', 'datatype': '1'},
        {'feild': 'mconv_rtp_dl_delay_avg', 'feildName': 'RTP下行平均时延', 'datatype': '1'},
        {'feild': 'mconv_rtcp_ul_delay_avg', 'feildName': 'RTCP上行平均时延', 'datatype': '1'},
        {'feild': 'mconv_rtcp_dl_delay_avg', 'feildName': 'RTCP下行平均时延', 'datatype': '1'},
        {'feild': 'msli_ul_tunzi_len_rate', 'feildName': 'VoNR语音上行质差率', 'datatype': '1'},
        {'feild': 'msli_ul_duanxu_len_rate', 'feildName': 'VoNR语音上行断续率', 'datatype': '1'},
        {'feild': 'msli_ul_dantong_len_rate', 'feildName': 'VoNR语音上行单通率', 'datatype': '1'},
        {'feild': 'msli_ul_mos_poor_len_rate', 'feildName': 'VoNR上行MOS质差率', 'datatype': '1'},
        {'feild': 'msli_dl_tunzi_len_rate', 'feildName': 'VoNR语音下行质差率', 'datatype': '1'},
        {'feild': 'msli_dl_duanxu_len_rate', 'feildName': 'VoNR语音下行断续率', 'datatype': '1'},
        {'feild': 'msli_dl_dantong_len_rate', 'feildName': 'VoNR语音下行单通率', 'datatype': '1'},
        {'feild': 'msli_dl_mos_poor_len_rate', 'feildName': 'VoNR下行MOS质差率', 'datatype': '1'},
        {'feild': 'msli_ul_mos_n2n_avg', 'feildName': 'VoNR上行平均MOS（对端VoNR）', 'datatype': '1'},
        {'feild': 'msli_ul_mos_n2v_avg', 'feildName': 'VoNR上行平均MOS（对端VoLTE）', 'datatype': '1'},
        {'feild': 'msli_ul_mos_n2f_avg', 'feildName': 'VoNR上行平均MOS（对端Vo5GSA）', 'datatype': '1'},
        {'feild': 'msli_ul_mos_n2cs_avg', 'feildName': 'VoNR上行平均MOS（对端CS）', 'datatype': '1'},
        {'feild': 'msli_ul_mos_n2all_avg', 'feildName': 'VoNR上行平均MOS（对端ALL）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_n2n_avg', 'feildName': 'VoNR下行平均MOS（对端VoNR）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_n2v_avg', 'feildName': 'VoNR下行平均MOS（对端VoLTE）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_n2f_avg', 'feildName': 'VoNR下行平均MOS（对端Vo5GSA）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_n2cs_avg', 'feildName': 'VoNR下行平均MOS（对端CS）', 'datatype': '1'},
        {'feild': 'msli_dl_mos_n2all_avg', 'feildName': 'VoNR下行平均MOS（对端ALL）', 'datatype': '1'},
        {'feild': 'msli_ul_rtp_lost_rate', 'feildName': '上行RTP丢包率', 'datatype': '1'},
        {'feild': 'msli_dl_rtp_lost_rate', 'feildName': '下行RTP丢包率', 'datatype': '1'},
        {'feild': 'vonr_sbc_net_suss', 'feildName': 'VoNR_网络接通次数(MOC+MTC)', 'datatype': '1'},
        {'feild': 'vonr_sbc_net_sums', 'feildName': 'VoNR_网络试呼次数(MOC+MTC)', 'datatype': '1'},
        {'feild': 'vonr_sbc_drops', 'feildName': 'VoNR_掉话次数', 'datatype': '1'},
        {'feild': 'vonr_sbc_ans', 'feildName': 'VoNR_应答复次数(掉话率)', 'datatype': '1'},
        {'feild': 'vonr_local_radio_single_voice_call', 'feildName': 'VoNR_语音本端无线单通通话次数', 'datatype': '1'},
        {'feild': 'vonr_local_radio_dx_call', 'feildName': 'VoNR_语音本端无线断续通话次数', 'datatype': '1'},
        {'feild': 'vonr_ans_voice_call', 'feildName': 'VoNR_语音通话总次数', 'datatype': '1'},
        {'feild': 'vonr_local_radio_dtdx_rate', 'feildName': 'VoNR_单通断续次数占比', 'datatype': '1'},
        {'feild': 'vonr_ul_tunzi_len', 'feildName': 'VoNR_语音上行质差时长(s)', 'datatype': '1'},
        {'feild': 'vonr_ul_dantong_len', 'feildName': 'VoNR_语音上行单通时长(s)', 'datatype': '1'},
        {'feild': 'vonr_ul_duanxu_len', 'feildName': 'VoNR_语音上行断续时长(s)', 'datatype': '1'},
        {'feild': 'vonr_ul_voice_sum_len', 'feildName': 'VoNR_语音上行总时长(s)', 'datatype': '1'},
        {'feild': 'vonr_dl_tunzi_len', 'feildName': 'VoNR_语音下行质差时长(s)', 'datatype': '1'},
        {'feild': 'vonr_dl_dantong_len', 'feildName': 'VoNR_语音下行单通时长(s)', 'datatype': '1'},
        {'feild': 'vonr_dl_duanxu_len', 'feildName': 'VoNR_语音下行断续时长(s)', 'datatype': '1'},
        {'feild': 'vonr_dl_voice_sum_len', 'feildName': 'VoNR_语音下行总时长(s)', 'datatype': '1'},
        {'feild': 'micro_grid', 'feildName': '微网格标识', 'datatype': '1'},
        {'feild': 'cover_scene1', 'feildName': '覆盖场景1', 'datatype': '1'},
        {'feild': 'cover_scene2', 'feildName': '覆盖场景2', 'datatype': '1'},
        {'feild': 'cover_scene3', 'feildName': '覆盖场景3', 'datatype': '1'},
        {'feild': 'cover_scene4', 'feildName': '覆盖场景4', 'datatype': '1'},
        {'feild': 'grid_road', 'feildName': '网格道路', 'datatype': '1'},
        {'feild': 'marketduty', 'feildName': '市场职责', 'datatype': '1'},
        {'feild': 'vendor', 'feildName': '厂商', 'datatype': '1'},
        {'feild': 'state', 'feildName': '网元状态', 'datatype': '1'},
        {'feild': 'coverage_type', 'feildName': '覆盖类型', 'datatype': '1'},
        {'feild': 'network_type', 'feildName': '网络制式', 'datatype': '1'},
        {'feild': 'freq', 'feildName': '频段_无线', 'datatype': '1'},
    ]
    
    # 构建result字段
    result_list = []
    for f in result_fields:
        result_list.append({
            'feildtype': 'VONR小区监控预警数据表-天',
            'table': 'csem.f_nk_vonr_keykpi_cell_d',
            'tableName': 'VONR小区监控预警数据表-天',
            'datatype': f['datatype'],
            'columntype': 1,
            'feildName': f['feildName'],
            'feild': f['feild'],
            'poly': '无',
            'anyWay': '无',
            'chart': '无',
            'chartpoly': '无'
        })
    
    payload = {
        'draw': 1,
        'start': 0,
        'length': 200,
        'total': 0,
        'geographicdimension': '小区',
        'timedimension': '天',
        'enodebField': 'gnodeb_id',
        'cgiField': 'cgi',
        'timeField': 'starttime',
        'cellField': 'cell',
        'cityField': 'city',
        'columns': _build_columns_param(vonr_fields),
        'order': [{'column': 0, 'dir': 'desc'}],
        'search': {'value': '', 'regex': False},
        'result': {'result': result_list, 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def get_5g_kpi_payload():
    """获取5G小区性能KPI报表payload"""
    print("[DEBUG-PAYLOAD] 生成 5G小区性能KPI报表 payload")
    
    # 5G小区KPI字段列表（与result中的字段一致）
    kpi_fields = [
        'starttime', 'ncgi', 'nrcell_name', 'branch', 'grid', 'city', 'area',
        'vendor', 'cover_type',
        'rrc_connmean', 'rrc_connmax',
        'pdcp_up_tput_bytes', 'pdcp_down_tput_bytes',
        'pdcp_up_tput_rate', 'pdcp_down_tput_rate',
        'prb_ul_util_rate', 'prb_dl_util_rate',
        'cqi10_rate', 'pdsch_bler'
    ]
    
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区，网格，地市，分公司', 'timedimension': '小时,天,周,月',
        'enodebField': 'gnodeb_id', 'cgiField': 'ncgi',
        'timeField': 'starttime', 'cellField': 'nrcell', 'cityField': 'city',
        'columns': _build_columns_param(kpi_fields),
        'result': {'result': [
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '数据时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'NCGI', 'feild': 'ncgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名称', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '人力区县分公司', 'feild': 'branch', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '设备厂家', 'feild': 'vendor', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '覆盖类型', 'feild': 'cover_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'RRC连接平均数', 'feild': 'rrc_connmean', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'RRC连接最大数', 'feild': 'rrc_connmax', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'PDCP层上行业务字节数', 'feild': 'pdcp_up_tput_bytes', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'PDCP层下行业务字节数', 'feild': 'pdcp_down_tput_bytes', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': '小区PDCP层吞吐量-上行(Mbps)', 'feild': 'pdcp_up_tput_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': '小区PDCP层吞吐量-下行(Mbps)', 'feild': 'pdcp_down_tput_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': '小区PRB利用率-上行(%)', 'feild': 'prb_ul_util_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': '小区PRB利用率-下行(%)', 'feild': 'prb_dl_util_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'CQI=10占比(%)', 'feild': 'cqi10_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'PDSCHbler(%)', 'feild': 'pdsch_bler', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'order': [{'column': 0, 'dir': 'desc'}],
        'search': {'value': '', 'regex': False},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def get_4g_kpi_payload():
    """获取4G小区性能KPI报表payload"""
    print("[DEBUG-PAYLOAD] 生成 4G小区性能KPI报表 payload")
    
    # 4G小区KPI字段列表（与result中的字段一致）
    kpi_fields = [
        'starttime', 'endtime', 'cgi', 'cell_name', 'city', 'area', 'grid',
        'marketduty', 'marketgrid', 'network_type', 'vendor', 'cover_type',
        'frequency_band', 'freq_name', 'earfcn', 'pci', 'tac', 'state', 'enodeb_name'
    ]
    
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区，网格，地市，分公司', 'timedimension': '小时,天,周.月,忙时,15分钟',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'columns': _build_columns_param(kpi_fields),
        'result': {'result': [
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '开始时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '结束时间', 'feild': 'endtime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'CGI', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名称', 'feild': 'cell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任田', 'feild': 'marketduty', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '市场网格', 'feild': 'marketgrid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网络制式', 'feild': 'network_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '设备厂家', 'feild': 'vendor', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '覆盖类型', 'feild': 'cover_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '使用频段', 'feild': 'frequency_band', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '详细频段', 'feild': 'freq_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '频点', 'feild': 'earfcn', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'PCI', 'feild': 'pci', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'TAC', 'feild': 'tac', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网元状态', 'feild': 'state', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '基站名称', 'feild': 'enodeb_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'order': [{'column': 0, 'dir': 'desc'}],
        'search': {'value': '', 'regex': False},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def set_payload_time(payload, start_time, end_time):
    """设置payload的查询时间"""
    print(f"[DEBUG-PAYLOAD] 设置时间范围: {start_time} 至 {end_time}")

    # 获取 timeField 判断时间字段类型
    time_field = payload.get('timeField', 'day_id')
    print(f"[DEBUG-PAYLOAD] timeField: {time_field}")

    # 如果是 day_id（日期类型），只取日期部分
    # 如果是 starttime（timestamp类型），需要完整的时间格式
    if time_field == 'day_id':
        start_date = start_time.split(' ')[0]  # 只取日期部分
        end_date = end_time.split(' ')[0]      # 只取日期部分
        print(f"[DEBUG-PAYLOAD] day_id 类型，只取日期: {start_date} 至 {end_date}")
    elif time_field == 'starttime':
        # starttime 是 timestamp 类型，格式是 YYYY-MM-DD HH:MM:SS
        # 起始时间用 00:00:00，结束时间用 23:59:59
        start_date = start_time  # 已经是完整格式
        end_date = end_time      # 已经是完整格式
        print(f"[DEBUG-PAYLOAD] starttime 类型，使用完整时间: {start_date} 至 {end_date}")
    else:
        start_date = start_time
        end_date = end_time

    for condition in payload['where']:
        if condition['feild'] in ['day_id', 'starttime']:
            if condition['symbol'] in ['>=', '>']:
                condition['val'] = start_date
                print(f"[DEBUG-PAYLOAD] 设置 {condition['feild']} >= {condition['val']}")
            elif condition['symbol'] in ['<', '<=']:
                condition['val'] = end_date
                print(f"[DEBUG-PAYLOAD] 设置 {condition['feild']} < {condition['val']}")
    return payload


def set_payload_city(payload, city):
    """设置payload的查询城市，支持多地市（逗号分隔）"""
    print(f"[DEBUG-PAYLOAD] 设置查询城市: {city}")
    # 处理多地市情况，如 "广州,深圳,东莞" -> "广州,深圳,东莞"
    # 如果只有一个地市，也转换为列表处理
    city_list = [c.strip() for c in city.split(',') if c.strip()]
    city_value = ','.join(city_list)
    
    for condition in payload['where']:
        if condition['feild'] == 'city':
            condition['val'] = city_value
            print(f"[DEBUG-PAYLOAD] 设置 city = {city_value}")
    return payload


# ==================== 数据提取器 ====================
class CustomDataExtractor:
    """自定义数据提取器"""

    def __init__(self, username=None, password=None, parent=None):
        self.username = username or DEFAULT_USERNAME
        self.password = password or DEFAULT_PASSWORD
        self.parent = parent  # GUI 父窗口
        self.login_mgr = None
        self.jxcx = None

    def login(self):
        """执行登录"""
        self.login_mgr = LoginManager(self.username, self.password, self.parent)
        return self.login_mgr.login()
    
    def init_jxcx(self):
        """初始化即席查询"""
        if not self.login_mgr:
            print("✗ 请先执行登录")
            return False
        
        self.jxcx = JXCXQuery(self.login_mgr.sess)
        return self.jxcx.enter_jxcx(retry_times=3, timeout=60)
    
    def extract_data(self, payload, start_date, end_date, city):
        """提取数据"""
        if not self.jxcx:
            return pd.DataFrame()
        
        payload = set_payload_time(payload, start_date + ' 00:00:00', end_date + ' 23:59:59')
        payload = set_payload_city(payload, city)
        
        return self.jxcx.get_table(payload, to_df=True)
    
    def get_payload_with_dynamic_fields(self, table_config, start_date, end_date, city):
        """获取payload，自动处理动态字段配置"""
        table_name = table_config.get('description', '')
        
        # 需要动态获取字段的报表类型
        dynamic_tables = [
            'VoLTE小区监控预警', 'EPSFB小区监控预警', 'VONR小区监控预警',
            '5G小区性能KPI报表', '4G小区性能KPI报表'
        ]
        
        if table_name in dynamic_tables:
            # 映射表名到API key、fieldtype和API类型
            # api_type: 'search' 使用adhocquery/search接口，'table' 使用adhocquery/getSelectTable接口
            # 注意：API key与HAR文件中的实际请求参数一致
            table_key_map = {
                'VoLTE小区监控预警': ('volte小区监控预警', 'VoLTE小区监控预警数据表-天', 'search'),
                'EPSFB小区监控预警': ('EPSFB', 'EPSFB小区监控预警数据表-天', 'search'),
                'VONR小区监控预警': ('vonr', 'VONR小区监控预警数据表-天', 'search'),
                '5G小区性能KPI报表': ('5G小区性能KPI报表', 'SA_CU性能', 'table'),
                '4G小区性能KPI报表': ('4G小区性能KPI报表', '公共信息（小区级粒度）', 'table'),
            }
            
            table_key, fieldtype, api_type = table_key_map.get(table_name, (None, None, None))
            
            if table_key and fieldtype:
                # 构建where条件
                start_time = start_date + ' 00:00:00'
                end_time = end_date + ' 23:59:59'
                where_conditions = [
                    {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': start_time, 'whereCon': 'and', 'query': True},
                    {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': end_time, 'whereCon': 'and', 'query': True},
                    {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': city, 'whereCon': 'and', 'query': True}
                ]
                
                # 动态构建payload
                payload = self.jxcx.build_payload_from_config(table_key, fieldtype, where_conditions, api_type)
                if payload:
                    return payload
        
        # 对于其他表，使用静态payload函数
        payload_func = table_config.get('payload_func')
        if payload_func:
            payload = payload_func()
            payload = set_payload_time(payload, start_date + ' 00:00:00', end_date + ' 23:59:59')
            payload = set_payload_city(payload, city)
            return payload
        
        return None
    
    def save_to_excel(self, df, filename):
        """保存到Excel，自动分Sheet（每50万行一个Sheet）"""
        if df.empty:
            return None
        
        ensure_dirs()
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        MAX_ROWS_PER_SHEET = 500000  # 每个Sheet最大行数
        
        try:
            total_rows = len(df)
            
            if total_rows <= MAX_ROWS_PER_SHEET:
                # 数据量小，直接保存
                df.to_excel(filepath, index=False, engine='openpyxl')
            else:
                # 数据量大，分多个Sheet保存
                sheet_num = (total_rows + MAX_ROWS_PER_SHEET - 1) // MAX_ROWS_PER_SHEET
                base_name = os.path.splitext(filename)[0]
                filepath = os.path.join(OUTPUT_DIR, f'{base_name}.xlsx')
                
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    for i in range(sheet_num):
                        start_idx = i * MAX_ROWS_PER_SHEET
                        end_idx = min((i + 1) * MAX_ROWS_PER_SHEET, total_rows)
                        sheet_name = f'数据{i + 1}'
                        df.iloc[start_idx:end_idx].to_excel(writer, sheet_name=sheet_name, index=False)
                
                print(f"数据共 {total_rows} 行，已拆分为 {sheet_num} 个Sheet保存")
            
            return filepath
        except Exception as e:
            print(f"保存文件失败: {e}")
            return None


# ==================== 数据表配置 ====================
class TableConfig:
    """数据表配置类"""

    TABLES = {
        '5G干扰小区': {
            'payload_func': get_5g_interference_payload,
            'use_interference_filter': True,
            'description': '5G干扰小区数据提取'
        },
        '4G干扰小区': {
            'payload_func': get_4g_interference_payload,
            'use_interference_filter': True,
            'description': '4G干扰小区数据提取'
        },
        '5G小区容量报表': {
            'payload_func': get_5g_capacity_payload,
            'use_interference_filter': False,
            'description': '5G小区容量报表 - 天粒度'
        },
        '重要场景-天': {
            'payload_func': get_important_scene_payload,
            'use_interference_filter': False,
            'description': '重要场景-小区天粒度'
        },
        '5G小区工参报表': {
            'payload_func': get_5g_cfg_payload,
            'use_interference_filter': False,
            'description': '5G小区工参报表'
        },
        '4G小区工参报表': {
            'payload_func': get_4g_cfg_payload,
            'use_interference_filter': False,
            'description': '4G小区工参报表'
        },
        'VoLTE小区监控预警': {
            'payload_func': get_volte_warning_payload,
            'use_interference_filter': False,
            'description': 'VoLTE小区监控预警数据'
        },
        'EPSFB小区监控预警': {
            'payload_func': get_epsfb_warning_payload,
            'use_interference_filter': False,
            'description': 'EPSFB小区监控预警数据'
        },
        'VONR小区监控预警': {
            'payload_func': get_vonr_warning_payload,
            'use_interference_filter': False,
            'description': 'VONR小区监控预警数据'
        },
        '5G小区性能KPI报表': {
            'payload_func': get_5g_kpi_payload,
            'use_interference_filter': False,
            'description': '5G小区性能KPI报表'
        },
        '4G小区性能KPI报表': {
            'payload_func': get_4g_kpi_payload,
            'use_interference_filter': False,
            'description': '4G小区性能KPI报表'
        },
    }

    @classmethod
    def get_table_names(cls):
        return list(cls.TABLES.keys())

    @classmethod
    def get_table_config(cls, table_name):
        return cls.TABLES.get(table_name)


# ==================== 多选下拉组件 ====================
class MultiSelectDropdown(ttk.Frame):
    """带复选框的下拉选择组件"""
    
    GD_CITIES = ['广州', '深圳', '东莞', '佛山', '中山', '珠海', '江门', '肇庆',
                 '惠州', '汕头', '潮州', '揭阳', '汕尾', '湛江', '茂名', '阳江',
                 '云浮', '韶关', '梅州', '河源', '清远']

    def __init__(self, parent, values, width=18, select_all=False):
        super().__init__(parent)
        self.values = values
        self.var_dict = {}
        
        # 下拉框变量
        self.var = tk.StringVar(value="")
        
        # 创建 Entry
        self.entry = ttk.Entry(self, textvariable=self.var, width=width, state='readonly')
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建下拉按钮
        self.btn = ttk.Button(self, text="▼", width=3, command=self._toggle_dropdown)
        self.btn.pack(side=tk.LEFT)
        
        # 创建下拉窗口
        self.dropdown = tk.Toplevel(self)
        self.dropdown.withdraw()
        self.dropdown.overrideredirect(True)
        self.dropdown.attributes('-topmost', True)
        
        # 复选框容器
        self.check_frame = ttk.Frame(self.dropdown)
        self.check_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.check_vars = {}
        for val in values:
            var = tk.BooleanVar(value=False)
            self.check_vars[val] = var
            cb = ttk.Checkbutton(
                self.check_frame, text=val, variable=var,
                command=lambda v=val: self._on_check_change()
            )
            cb.pack(anchor=tk.W, padx=5, pady=1)
        
        # 全选按钮
        btn_frame = ttk.Frame(self.dropdown)
        btn_frame.pack(fill=tk.X, padx=2, pady=2)
        ttk.Button(btn_frame, text="全选", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="取消", command=self._deselect_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="确定", command=self._confirm).pack(side=tk.RIGHT, padx=2)
        
        # 初始全选
        if select_all:
            self._select_all()
    
    def _toggle_dropdown(self):
        """切换下拉框显示"""
        if self.dropdown.winfo_viewable():
            self.dropdown.withdraw()
        else:
            self._show_dropdown()
    
    def _show_dropdown(self):
        """显示下拉框"""
        self.dropdown.deiconify()
        # 定位到 Entry 下方
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        self.dropdown.geometry(f"+{x}+{y}")
        self.dropdown.lift()
    
    def _on_check_change(self):
        """复选框状态变化"""
        pass
    
    def _select_all(self):
        """全选"""
        for var in self.check_vars.values():
            var.set(True)
    
    def _deselect_all(self):
        """取消全选"""
        for var in self.check_vars.values():
            var.set(False)
    
    def _confirm(self):
        """确认选择"""
        selected = self.get_selected()
        if selected:
            self.var.set(','.join(selected))
        else:
            self.var.set("")
        self.dropdown.withdraw()
    
    def get_selected(self):
        """获取选中的值列表"""
        return [val for val, var in self.check_vars.items() if var.get()]
    
    def set_selected(self, values):
        """设置选中的值"""
        for val, var in self.check_vars.items():
            var.set(val in values)
        if values:
            self.var.set(','.join(values))
        else:
            self.var.set("")
    
    def get_value(self):
        """获取选中值（逗号分隔字符串）"""
        return self.var.get()
    
    def set_value(self, value):
        """设置选中值（逗号分隔字符串）"""
        if value:
            values = [v.strip() for v in value.split(',')]
            self.set_selected(values)


# ==================== GUI应用 ====================
class UniversalExtractorGUI:
    """通用数据提取工具GUI"""

    def __init__(self, root, expiry_time=None):
        self.root = root
        self.root.title("通用数据提取工具")
        self.root.geometry("1100x800")
        self.root.minsize(950, 700)
        self.root.resizable(True, True)
        
        # 授权过期时间
        self.expiry_time = expiry_time

        self.log_queue = queue.Queue()
        self.extractor = None
        self.is_logged_in = False

        self.create_widgets()
        self.root.update_idletasks()
        self._center_window()

        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass

        self.setup_logging()
        self.update_log()
        self.load_config()
        self._update_license_display()

    def _update_license_display(self):
        """更新授权时间显示"""
        if self.expiry_time:
            try:
                # 解析过期时间，只显示日期部分
                expiry_dt = datetime.strptime(self.expiry_time, "%Y-%m-%d %H:%M:%S")
                display_time = expiry_dt.strftime("%Y-%m-%d")
                
                # 计算剩余天数
                current_dt = datetime.now()
                days_left = (expiry_dt - current_dt).days
                
                if days_left < 0:
                    self.license_label.config(text="授权已过期", fg='#fce8e6')
                elif days_left <= 7:
                    self.license_label.config(text=f"授权到期: {display_time} (剩{days_left}天)", fg='#fce8e6')
                elif days_left <= 30:
                    self.license_label.config(text=f"授权到期: {display_time} (剩{days_left}天)", fg='#fff3e0')
                else:
                    self.license_label.config(text=f"授权到期: {display_time}", fg='#e8f5e9')
            except:
                self.license_label.config(text="", fg='#e8f5e9')

    def _center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width < 100:
            width = 1100
            height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_logging(self):
        """初始化日志系统"""
        ensure_dirs()
        log_filename = datetime.now().strftime("universal_gui_log_%Y%m%d_%H%M%S.log")
        self.log_file_path = os.path.join(LOG_DIR, log_filename)

        set_log_file(self.log_file_path)

        self.logger = logging.getLogger('UniversalExtractorGUI')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.logger.info("=" * 50)
        self.logger.info("通用数据提取工具 GUI 启动")
        self.logger.info(f"日志文件: {self.log_file_path}")
        self.logger.info("=" * 50)

    def create_widgets(self):
        """创建界面组件 - 使用现代化设计"""
        # 顶部蓝色标题栏
        self.header = tk.Frame(self.root, bg='#1a73e8', height=60)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)

        # 标题栏左侧 - Logo和标题
        left_frame = tk.Frame(self.header, bg='#1a73e8')
        left_frame.pack(side=tk.LEFT, padx=25, pady=15)

        icon_label = tk.Label(left_frame, text="📊", font=('Segoe UI Emoji', 24),
                             bg='#1a73e8', fg='white')
        icon_label.pack(side=tk.LEFT, padx=(0, 12))

        title = tk.Label(left_frame, text="通用数据提取工具",
                        font=('Microsoft YaHei UI', 18, 'bold'),
                        bg='#1a73e8', fg='white')
        title.pack(side=tk.LEFT)

        version = tk.Label(left_frame, text="v2.0",
                          font=('Microsoft YaHei UI', 9),
                          bg='#1557b0', fg='white',
                          padx=8, pady=2)
        version.pack(side=tk.LEFT, padx=(12, 0))

        # 标题栏右侧 - 状态和授权时间
        self.right_frame = tk.Frame(self.header, bg='#1a73e8')
        self.right_frame.pack(side=tk.RIGHT, padx=25, pady=15)

        # 授权过期时间标签
        self.license_label = tk.Label(self.right_frame, text="",
                              font=('Microsoft YaHei UI', 9),
                              bg='#1a73e8', fg='#e8f5e9')
        self.license_label.pack(side=tk.LEFT, padx=(0, 15))

        self.status_dot = tk.Label(self.right_frame, text="●", font=('Arial', 14),
                            bg='#1a73e8', fg='#80868b')
        self.status_dot.pack(side=tk.LEFT)
        self.status_text = tk.Label(self.right_frame, text="系统就绪",
                              font=('Microsoft YaHei UI', 10),
                              bg='#1a73e8', fg='white')
        self.status_text.pack(side=tk.LEFT, padx=(6, 0))

        # 主内容区域
        self.main_container = tk.Frame(self.root, bg='#f5f7fa')
        self.main_container.pack(fill=tk.BOTH, expand=True)

        content = tk.Frame(self.main_container, bg='#f5f7fa')
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # 第一行：查询参数卡片
        self._build_query_card(content)

        # 第二行：登录配置 + 地市日期选项
        second_row = tk.Frame(content, bg='#f5f7fa')
        second_row.pack(fill=tk.X, pady=(10, 10))

        self._build_login_card(second_row)
        self._build_params_card(second_row)

        # 底部：进度和日志
        self._build_bottom_section(content)

    def _build_card(self, parent, title, **kwargs):
        """创建卡片容器"""
        card = tk.Frame(parent, bg='white', highlightbackground='#e8eaed',
                        highlightthickness=1, **kwargs)

        if title:
            header = tk.Frame(card, bg='white', height=40)
            header.pack(fill=tk.X, padx=16, pady=(12, 0))
            header.pack_propagate(False)

            label = tk.Label(header, text=title,
                            font=('Microsoft YaHei UI', 11, 'bold'),
                            bg='white', fg='#202124', anchor='w')
            label.pack(fill=tk.X)

            separator = tk.Frame(card, bg='#e8eaed', height=1)
            separator.pack(fill=tk.X, padx=16, pady=(8, 0))

        return card

    def _build_query_card(self, parent):
        """构建查询参数卡片"""
        card = self._build_card(parent, "🔍 查询参数")
        card.pack(fill=tk.X, pady=(0, 10))

        body = tk.Frame(card, bg='white')
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        top_row = tk.Frame(body, bg='white')
        top_row.pack(fill=tk.X, pady=(0, 12))

        # 左侧：数据分类
        cat_frame = tk.Frame(top_row, bg='white', width=200)
        cat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_frame.pack_propagate(False)

        tk.Label(cat_frame, text="数据分类", font=('Microsoft YaHei UI', 10, 'bold'),
                bg='white', fg='#202124').pack(anchor='w', pady=(0, 8))

        self.category_vars = {}
        categories = [
            ("干扰", False),
            ("容量", False),
            ("工参", False),
            ("语音报表", False),
            ("小区性能", False)
        ]

        for name, checked in categories:
            var = tk.IntVar(value=int(checked))
            self.category_vars[name] = var
            cb = tk.Checkbutton(cat_frame, text=name, variable=var,
                               font=('Microsoft YaHei UI', 10, 'bold'),
                               bg='white', fg='#202124',
                               selectcolor='#e8f0fe',
                               activebackground='white',
                               activeforeground='#1a73e8',
                               cursor='hand2',
                               command=lambda c=name: self._on_category_changed(c))
            cb.pack(anchor='w', pady=2)

        # 右侧：数据表选择
        table_frame = tk.Frame(top_row, bg='white')
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0))

        tk.Label(table_frame, text="选择数据表", font=('Microsoft YaHei UI', 10, 'bold'),
                bg='white', fg='#202124').pack(anchor='w', pady=(0, 8))

        tables_grid = tk.Frame(table_frame, bg='white')
        tables_grid.pack(fill=tk.X)

        self.table_vars = {}
        TABLE_CATEGORIES = {
            '干扰': ['5G干扰小区', '4G干扰小区'],
            '容量': ['5G小区容量报表', '重要场景-天'],
            '工参': ['5G小区工参报表', '4G小区工参报表'],
            '语音报表': ['VoLTE小区监控预警', 'VONR小区监控预警', 'EPSFB小区监控预警'],
            '小区性能': ['5G小区性能KPI报表', '4G小区性能KPI报表'],
        }

        all_tables = []
        for tables in TABLE_CATEGORIES.values():
            all_tables.extend(tables)

        for i, name in enumerate(all_tables):
            var = tk.IntVar(value=1 if i < 2 else 0)
            self.table_vars[name] = var
            cb = tk.Checkbutton(tables_grid, text=name, variable=var,
                               font=('Microsoft YaHei UI', 10, 'bold'),
                               bg='white', fg='#202124',
                               selectcolor='#e8f0fe',
                               activebackground='white',
                               activeforeground='#1a73e8',
                               cursor='hand2')
            row, col = i // 3, i % 3
            cb.grid(row=row, column=col, sticky='w', padx=(0, 25), pady=2)

        # 全选按钮
        btn_frame = tk.Frame(table_frame, bg='white')
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_frame, text="全选", font=('Microsoft YaHei UI', 9, 'bold'),
                 bg='#e8eaed', fg='#202124', bd=0, padx=14, pady=4,
                 cursor='hand2', command=self._select_all_tables).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="取消", font=('Microsoft YaHei UI', 9, 'bold'),
                 bg='#e8eaed', fg='#202124', bd=0, padx=14, pady=4,
                 cursor='hand2', command=self._deselect_all_tables).pack(side=tk.LEFT)

    def _build_login_card(self, parent):
        """构建登录配置卡片"""
        card = self._build_card(parent, "🔐 登录配置", width=380)
        card.pack(side=tk.LEFT, padx=(0, 10))

        body = tk.Frame(card, bg='white')
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        row1 = tk.Frame(body, bg='white')
        row1.pack(fill=tk.X, pady=(0, 10))

        user_frame = tk.Frame(row1, bg='white')
        user_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(user_frame, text="用户名", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(anchor='w')
        self.username_entry = tk.Entry(user_frame, font=('Microsoft YaHei UI', 10),
                             relief='solid', bd=1, width=18)
        self.username_entry.insert(0, DEFAULT_USERNAME)
        self.username_entry.pack(fill=tk.X, pady=(4, 0))

        pass_frame = tk.Frame(row1, bg='white')
        pass_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        tk.Label(pass_frame, text="密码", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(anchor='w')
        self.password_entry = tk.Entry(pass_frame, font=('Microsoft YaHei UI', 10),
                             show="●", relief='solid', bd=1, width=18)
        self.password_entry.insert(0, DEFAULT_PASSWORD)
        self.password_entry.pack(fill=tk.X, pady=(4, 0))

        # 状态栏
        self.status_bar = tk.Frame(body, bg='#e8eaed', relief='flat')
        self.status_bar.pack(fill=tk.X, pady=(8, 0))

        self.login_status_icon = tk.Label(self.status_bar, text="○", font=('Arial', 12, 'bold'),
                              bg='#e8eaed', fg='#80868b')
        self.login_status_icon.pack(side=tk.LEFT, padx=(10, 6), pady=6)

        self.login_status_lbl = tk.Label(self.status_bar, text="未登录",
                             font=('Microsoft YaHei UI', 10, 'bold'),
                             bg='#e8eaed', fg='#80868b')
        self.login_status_lbl.pack(side=tk.LEFT, pady=6, padx=(0, 10))

        self.login_btn = tk.Button(self.status_bar, text="登录",
                             font=('Microsoft YaHei UI', 10, 'bold'),
                             bg='#1a73e8', fg='white', bd=0,
                             cursor='hand2', padx=20, pady=4,
                             command=self.login)
        self.login_btn.pack(side=tk.RIGHT, padx=(10, 0), pady=6)

    def _build_params_card(self, parent):
        """构建提取参数卡片"""
        card = self._build_card(parent, "⚙ 提取参数")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = tk.Frame(card, bg='white')
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        params_grid = tk.Frame(body, bg='white')
        params_grid.pack(fill=tk.X, pady=(0, 12))

        # 第一行：地市选择 + 快捷日期
        row1 = tk.Frame(params_grid, bg='white')
        row1.pack(fill=tk.X, pady=(0, 10))

        city_frame = tk.Frame(row1, bg='white')
        city_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(city_frame, text="地市选择", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(anchor='w')

        self.city_dropdown = MultiSelectDropdown(
            city_frame,
            MultiSelectDropdown.GD_CITIES,
            width=14,
            select_all=False
        )
        self.city_dropdown.pack(pady=(4, 0))
        self.city_dropdown.set_selected(['阳江'])

        quick_frame = tk.Frame(row1, bg='white')
        quick_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(quick_frame, text="快捷日期", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(anchor='w')

        quick_inner = tk.Frame(quick_frame, bg='white')
        quick_inner.pack(pady=(4, 0))

        for text, days in [("昨天", 1), ("近7天", 7), ("近30天", 30)]:
            btn = tk.Button(quick_inner, text=text, font=('Microsoft YaHei UI', 9, 'bold'),
                           bg='#e8eaed', fg='#202124', bd=0, padx=12, pady=4,
                           cursor='hand2', relief='flat',
                           command=lambda d=days: self.set_quick_date(d))
            btn.pack(side=tk.LEFT, padx=(0, 5))

        # 第二行：日期范围
        row2 = tk.Frame(params_grid, bg='white')
        row2.pack(fill=tk.X)

        date_frame = tk.Frame(row2, bg='white')
        date_frame.pack(side=tk.LEFT)
        tk.Label(date_frame, text="日期范围", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(anchor='w')

        date_inner = tk.Frame(date_frame, bg='white')
        date_inner.pack(pady=(4, 0))

        self.start_year_var = tk.IntVar(value=datetime.now().year)
        self.start_month_var = tk.IntVar(value=datetime.now().month)
        self.start_day_var = tk.IntVar(value=1)

        yesterday = datetime.now() - timedelta(days=1)
        self.end_year_var = tk.IntVar(value=yesterday.year)
        self.end_month_var = tk.IntVar(value=yesterday.month)
        self.end_day_var = tk.IntVar(value=yesterday.day)

        start_frame = tk.Frame(date_inner, bg='white')
        start_frame.pack(side=tk.LEFT)

        current_year = datetime.now().year
        ttk.Combobox(start_frame, textvariable=self.start_year_var,
                   values=list(range(2020, current_year + 1)),
                   width=5, state="readonly").pack(side=tk.LEFT)
        tk.Label(start_frame, text="-", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(side=tk.LEFT)
        ttk.Combobox(start_frame, textvariable=self.start_month_var,
                   values=list(range(1, 13)),
                   width=3, state="readonly").pack(side=tk.LEFT)
        tk.Label(start_frame, text="-", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(side=tk.LEFT)
        ttk.Combobox(start_frame, textvariable=self.start_day_var,
                   values=list(range(1, 32)),
                   width=3, state="readonly").pack(side=tk.LEFT)

        tk.Label(date_inner, text=" 至 ", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=4)

        end_frame = tk.Frame(date_inner, bg='white')
        end_frame.pack(side=tk.LEFT)

        ttk.Combobox(end_frame, textvariable=self.end_year_var,
                   values=list(range(2020, current_year + 1)),
                   width=5, state="readonly").pack(side=tk.LEFT)
        tk.Label(end_frame, text="-", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(side=tk.LEFT)
        ttk.Combobox(end_frame, textvariable=self.end_month_var,
                   values=list(range(1, 13)),
                   width=3, state="readonly").pack(side=tk.LEFT)
        tk.Label(end_frame, text="-", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(side=tk.LEFT)
        ttk.Combobox(end_frame, textvariable=self.end_day_var,
                   values=list(range(1, 32)),
                   width=3, state="readonly").pack(side=tk.LEFT)

        # 多日提取模式选项
        mode_frame = tk.Frame(row2, bg='white')
        mode_frame.pack(side=tk.RIGHT, padx=(20, 0))

        self.multi_day_var = tk.BooleanVar(value=False)
        multi_day_cb = tk.Checkbutton(mode_frame, text="多日模式（单日循环提取）",
                                      variable=self.multi_day_var,
                                      font=('Microsoft YaHei UI', 9),
                                      bg='white', fg='#202124',
                                      selectcolor='#e8f0fe',
                                      activebackground='white',
                                      command=self._on_multi_day_toggle)
        multi_day_cb.pack(side=tk.LEFT)

        tk.Label(mode_frame, text="提示: 多日模式按单日逐个提取后合并",
                font=('Microsoft YaHei UI', 8), bg='white', fg='#80868b').pack(side=tk.LEFT, padx=(8, 0))

        # 操作按钮
        btn_row = tk.Frame(body, bg='white')
        btn_row.pack(fill=tk.X, pady=(8, 0))

        self.extract_btn = tk.Button(btn_row, text="▶ 开始提取",
                               font=('Microsoft YaHei UI', 11, 'bold'),
                               bg='#1a73e8', fg='white', bd=0,
                               cursor='hand2', padx=28, pady=8,
                               state=tk.DISABLED, command=self.start_extract)
        self.extract_btn.pack(side=tk.LEFT)

        self.stop_btn = tk.Button(btn_row, text="⏹ 停止",
                            font=('Microsoft YaHei UI', 10),
                            bg='#ea4335', fg='white', bd=0,
                            cursor='hand2', padx=18, pady=6,
                            state=tk.DISABLED, command=self.stop_extract)
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))

        tk.Button(btn_row, text="📁 打开目录",
                 font=('Microsoft YaHei UI', 10, 'bold'),
                 bg='#e8eaed', fg='#202124', bd=1,
                 cursor='hand2', padx=16, pady=6,
                 command=self.open_output_dir).pack(side=tk.RIGHT)

    def _build_bottom_section(self, parent):
        """构建底部日志区域"""
        bottom = tk.Frame(parent, bg='white', highlightbackground='#e8eaed',
                         highlightthickness=1)
        bottom.pack(fill=tk.BOTH, expand=True)

        progress_area = tk.Frame(bottom, bg='white')
        progress_area.pack(fill=tk.X, padx=16, pady=(12, 8))

        progress_info = tk.Frame(progress_area, bg='white')
        progress_info.pack(fill=tk.X)

        self.progress_lbl_pct = tk.Label(progress_info, text="进度: 0%",
                          font=('Microsoft YaHei UI', 10, 'bold'),
                          bg='white', fg='#1a73e8')
        self.progress_lbl_pct.pack(side=tk.LEFT)

        self.progress_lbl_detail = tk.Label(progress_info, text="就绪",
                             font=('Microsoft YaHei UI', 9),
                             bg='white', fg='#5f6368')
        self.progress_lbl_detail.pack(side=tk.RIGHT)

        progress_outer = tk.Frame(progress_area, bg='#e8eaed', height=8)
        progress_outer.pack(fill=tk.X, pady=(8, 0))
        progress_outer.pack_propagate(False)

        self.progress_fill = tk.Frame(progress_outer, bg='#1a73e8', height=8)
        self.progress_fill.place(relx=0, rely=0, relwidth=0)

        log_header = tk.Frame(bottom, bg='white')
        log_header.pack(fill=tk.X, padx=16)

        tk.Label(log_header, text="📋 运行日志",
                font=('Microsoft YaHei UI', 10, 'bold'),
                bg='white', fg='#202124').pack(side=tk.LEFT)

        tk.Button(log_header, text="清空", font=('Microsoft YaHei UI', 9, 'bold'),
                 bg='#e8eaed', fg='#202124', bd=0,
                 cursor='hand2', padx=10, pady=3,
                 command=self.clear_log).pack(side=tk.RIGHT)

        log_frame = tk.Frame(bottom, bg='white')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 12))

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, font=('Consolas', 10),
                          bg='#f8f9fa', fg='#202124', bd=0,
                          padx=10, pady=8, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("#3c4043", foreground="#3c4043")
        self.log_text.tag_config("#34a853", foreground="#34a853")
        self.log_text.tag_config("#80868b", foreground="#80868b")
        self.log_text.tag_config("#1a73e8", foreground="#1a73e8")
        self.log_text.tag_config("#ea4335", foreground="#ea4335")

        status_bar = tk.Frame(bottom, bg='#f8f9fa', height=32)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)

        self.status_var = tk.StringVar(value=f"✓ 数据输出目录: {os.path.abspath(OUTPUT_DIR)}/")
        tk.Label(status_bar, textvariable=self.status_var,
                font=('Microsoft YaHei UI', 9, 'bold'),
                bg='#f8f9fa', fg='#202124').pack(side=tk.LEFT, padx=16, pady=8)

        tk.Label(status_bar, text="v2.0.1 | © 2026",
                font=('Microsoft YaHei UI', 8),
                bg='#f8f9fa', fg='#bdc1c6').pack(side=tk.RIGHT, padx=16, pady=8)

    def update_progress_bar(self, value, label=""):
        """更新进度条"""
        self.progress_lbl_pct.config(text=f"进度: {int(value)}%")
        self.progress_fill.place_configure(relwidth=value / 100)
        if label:
            self.progress_lbl_detail.config(text=label)

    def _on_category_changed(self, category_name):
        """分类复选框改变时的回调"""
        TABLE_CATEGORIES = {
            '干扰': ['5G干扰小区', '4G干扰小区'],
            '容量': ['5G小区容量报表', '重要场景-天'],
            '工参': ['5G小区工参报表', '4G小区工参报表'],
            '语音报表': ['VoLTE小区监控预警', 'VONR小区监控预警', 'EPSFB小区监控预警'],
            '小区性能': ['5G小区性能KPI报表', '4G小区性能KPI报表'],
        }

        is_checked = self.category_vars[category_name].get()
        tables = TABLE_CATEGORIES.get(category_name, [])

        for table_name in tables:
            if table_name in self.table_vars:
                self.table_vars[table_name].set(is_checked)

    def _select_all_tables(self):
        """全选所有数据表"""
        for var in self.table_vars.values():
            var.set(True)

    def _deselect_all_tables(self):
        """取消全选"""
        for var in self.table_vars.values():
            var.set(False)

    def _on_multi_day_toggle(self):
        """多日模式切换处理"""
        if self.multi_day_var.get():
            self.log("已启用多日模式，将按日期逐天提取数据", "INFO")
        else:
            self.log("已关闭多日模式", "INFO")

    def get_selected_tables(self):
        """获取选中的数据表列表"""
        return [name for name, var in self.table_vars.items() if var.get()]

    def validate_inputs(self):
        """验证输入"""
        selected_tables = self.get_selected_tables()
        if not selected_tables:
            messagebox.showwarning("警告", "请至少选择一个数据表")
            return False

        city = self.city_dropdown.get_value()
        if not city:
            messagebox.showwarning("警告", "请选择至少一个地市")
            return False

        start_date = self.get_date_string(self.start_year_var, self.start_month_var, self.start_day_var)
        end_date = self.get_date_string(self.end_year_var, self.end_month_var, self.end_day_var)

        if not start_date or not end_date:
            messagebox.showwarning("警告", "请输入有效的日期")
            return False

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                messagebox.showwarning("警告", "开始日期不能晚于结束日期")
                return False
        except ValueError:
            messagebox.showwarning("警告", "日期格式错误")
            return False

        return True

    def login(self):
        """执行登录"""
        if self.is_logged_in:
            messagebox.showinfo("提示", "已经登录，无需重复登录")
            return

        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("警告", "请输入用户名和密码")
            return

        self.login_btn.config(state=tk.DISABLED, text="登录中...")
        self.update_login_status("登录中...", "pending")

        thread = threading.Thread(target=self._login_thread, args=(username, password))
        thread.daemon = True
        thread.start()

    def _login_thread(self, username, password):
        """登录线程"""
        try:
            self.extractor = CustomDataExtractor(username, password, self.root)

            import builtins
            original_print = print

            def custom_print(*args, **kwargs):
                message = ' '.join(map(str, args))
                if '[DEBUG' in message:
                    self.log(message, "DEBUG")
                elif '✓' in message or '成功' in message:
                    self.log(message, "SUCCESS")
                elif '✗' in message or '失败' in message or '错误' in message:
                    self.log(message, "ERROR")
                elif '⚠' in message or '警告' in message or 'WARNING' in message:
                    self.log(message, "WARNING")
                else:
                    self.log(message, "INFO")

            builtins.print = custom_print

            self.update_progress_bar(30, "正在连接服务器...")
            success = self.extractor.login()

            builtins.print = original_print

            if success:
                self.update_progress_bar(60, "登录成功，初始化即席查询...")

                builtins.print = custom_print
                jxcx_success = self.extractor.init_jxcx()
                builtins.print = original_print

                if jxcx_success:
                    self.is_logged_in = True
                    self.update_progress_bar(100, "登录完成")
                    self.log("登录成功！", "SUCCESS")
                    self.root.after(0, self._login_success_ui)
                else:
                    self.log("初始化即席查询失败", "ERROR")
                    self.root.after(0, self._login_failed_ui)
            else:
                self.log("登录失败", "ERROR")
                self.root.after(0, self._login_failed_ui)

        except Exception as e:
            self.log(f"登录异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            self.root.after(0, self._login_failed_ui)

    def _login_success_ui(self):
        """登录成功UI"""
        self.login_btn.config(state=tk.DISABLED, text="已登录")
        self.extract_btn.config(state=tk.NORMAL)
        self.update_login_status("已登录 ✓", "success")
        self.status_text.config(text="登录成功")
        messagebox.showinfo("成功", "登录成功！")

    def _login_failed_ui(self):
        """登录失败UI"""
        self.login_btn.config(state=tk.NORMAL, text="登录")
        self.update_login_status("登录失败", "error")
        self.update_progress_bar(0, "登录失败")
        self.status_text.config(text="登录失败")
        messagebox.showerror("失败", "登录失败，请检查账号密码或网络连接")

    def update_login_status(self, text, status="normal"):
        """更新登录状态显示"""
        colors = {
            "success": ("✓", "#e8f5e9", "#34a853"),
            "error": ("✗", "#fce8e6", "#ea4335"),
            "pending": ("...", "#fff3e0", "#f57c00"),
            "normal": ("○", "#e8eaed", "#80868b")
        }
        icon, bg, fg = colors.get(status, colors["normal"])
        self.login_status_icon.config(text=icon, bg=bg, fg=fg)
        self.login_status_lbl.config(text=text, bg=bg, fg=fg)
        self.status_bar.config(bg=bg)
        self.login_status_icon.config(bg=bg)
        self.login_status_lbl.config(bg=bg)

    def start_extract(self):
        """开始提取"""
        if not self.is_logged_in:
            messagebox.showwarning("警告", "请先登录")
            return

        if not self.validate_inputs():
            return

        self.extract_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_text.config(text="正在提取数据...")

        thread = threading.Thread(target=self._extract_thread)
        thread.daemon = True
        thread.start()

    def _extract_thread(self):
        """提取数据线程 - 支持多表批量提取和多日模式"""
        import copy
        try:
            selected_tables = self.get_selected_tables()
            city = self.city_dropdown.get_value()
            start_date = self.get_date_string(self.start_year_var, self.start_month_var, self.start_day_var)
            end_date = self.get_date_string(self.end_year_var, self.end_month_var, self.end_day_var)
            
            # 检查是否启用多日模式
            is_multi_day = self.multi_day_var.get()

            total_tables = len(selected_tables)
            self.log("=" * 50, "INFO")
            self.log(f"开始批量提取数据，共 {total_tables} 个数据表", "INFO")
            self.log(f"地市: {city}", "INFO")
            self.log(f"日期范围: {start_date} 至 {end_date}", "INFO")
            if is_multi_day:
                self.log(f"模式: 多日模式（按日期逐天提取，合并为一个文件）", "INFO")
            self.log("=" * 50, "INFO")

            success_count = 0
            failed_count = 0

            for idx, table_name in enumerate(selected_tables):
                self.log("", "INFO")
                self.log(f"--- [{idx + 1}/{total_tables}] 正在处理: {table_name} ---", "INFO")

                table_config = TableConfig.get_table_config(table_name)
                if not table_config:
                    self.log(f"✗ 未找到数据表配置: {table_name}", "ERROR")
                    failed_count += 1
                    continue

                if is_multi_day:
                    # 多日模式：按日期逐天提取，最后合并成一个文件
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        current_dt = start_dt
                        
                        day_count = (end_dt - start_dt).days + 1
                        day_num = 0
                        
                        # 用于收集所有日期的数据
                        all_dfs = []
                        total_rows = 0
                        
                        while current_dt <= end_dt:
                            day_num += 1
                            current_date_str = current_dt.strftime("%Y-%m-%d")
                            self.log(f"  >>> 正在提取日期: {current_date_str} ({day_num}/{day_count})", "INFO")
                            
                            self.update_progress_bar(
                                int((idx / total_tables) * 100), 
                                f"正在提取 {table_name} {current_date_str}..."
                            )
                            
                            try:
                                payload = self.extractor.get_payload_with_dynamic_fields(
                                    table_config, current_date_str, current_date_str, city
                                )
                                
                                if not payload:
                                    self.log(f"  ✗ 生成payload失败: {current_date_str}", "ERROR")
                                    current_dt += timedelta(days=1)
                                    continue
                                
                                self.update_progress_bar(
                                    int((idx / total_tables) * 100) + 5, 
                                    f"正在查询 {current_date_str}..."
                                )
                                
                                df = self.extractor.jxcx.get_table(payload, to_df=True)
                                
                                if df.empty:
                                    self.log(f"  ⚠ {current_date_str}: 未查询到数据", "WARNING")
                                else:
                                    all_dfs.append(df)
                                    total_rows += len(df)
                                    self.log(f"  ✓ [{current_date_str}] 提取成功，共 {len(df)} 条记录", "SUCCESS")
                                    
                            except Exception as e:
                                self.log(f"  ✗ [{current_date_str}] 提取异常: {e}", "ERROR")
                            
                            current_dt += timedelta(days=1)
                        
                        # 所有日期提取完成后，合并并保存
                        if all_dfs:
                            self.update_progress_bar(
                                int(((idx + 0.8) / total_tables) * 100), 
                                "正在合并并保存数据..."
                            )
                            
                            combined_df = pd.concat(all_dfs, ignore_index=True)
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            filename = f'{table_name}_{city}_{start_date}_{end_date}_{timestamp}.xlsx'
                            filepath = self.extractor.save_to_excel(combined_df, filename)
                            
                            if filepath:
                                self.log(f"  ✓ 多日数据合并成功！共 {total_rows} 条记录", "SUCCESS")
                                self.log(f"    文件已保存: {filepath}", "SUCCESS")
                                success_count += 1
                            else:
                                self.log(f"  ✗ 保存文件失败", "ERROR")
                                failed_count += 1
                        else:
                            self.log(f"  ⚠ 所有日期均未查询到数据", "WARNING")
                            
                    except Exception as e:
                        self.log(f"✗ [{table_name}] 多日模式处理异常: {e}", "ERROR")
                        failed_count += 1
                else:
                    # 普通模式：直接提取整个日期范围
                    self.update_progress_bar(int((idx / total_tables) * 100), f"正在提取 {table_name}...")

                    try:
                        payload = self.extractor.get_payload_with_dynamic_fields(
                            table_config, start_date, end_date, city
                        )

                        if not payload:
                            self.log(f"✗ 生成payload失败: {table_name}", "ERROR")
                            failed_count += 1
                            continue

                        self.update_progress_bar(int((idx / total_tables) * 100) + 10, "正在查询数据...")

                        df = self.extractor.jxcx.get_table(payload, to_df=True)

                        if df.empty:
                            self.log(f"⚠ 未查询到数据: {table_name}", "WARNING")
                            continue

                        self.update_progress_bar(int(((idx + 0.8) / total_tables) * 100), "正在保存数据...")

                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f'{table_name}_{city}_{timestamp}.xlsx'
                        filepath = self.extractor.save_to_excel(df, filename)

                        if filepath:
                            self.log(f"✓ [{table_name}] 提取成功！共 {len(df)} 条记录", "SUCCESS")
                            self.log(f"  文件已保存: {filepath}", "SUCCESS")
                            success_count += 1
                        else:
                            self.log(f"✗ [{table_name}] 保存文件失败", "ERROR")
                            failed_count += 1

                    except Exception as e:
                        self.log(f"✗ [{table_name}] 提取异常: {e}", "ERROR")
                        failed_count += 1
                        continue

            self.log("", "INFO")
            self.log("=" * 50, "INFO")
            self.log(f"批量提取完成！成功: {success_count}/{total_tables}", "SUCCESS" if success_count == total_tables else "INFO")
            if failed_count > 0:
                self.log(f"失败: {failed_count}/{total_tables}", "WARNING")
            self.log("=" * 50, "INFO")

            self.root.after(0, self._extract_success_ui)

        except Exception as e:
            self.log(f"提取数据异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            self.root.after(0, self._extract_failed_ui)

    def _extract_success_ui(self):
        """提取成功UI"""
        self.extract_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_progress_bar(100, "提取完成")
        self.status_text.config(text="提取完成")

    def _extract_failed_ui(self):
        """提取失败UI"""
        self.extract_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_progress_bar(0, "提取失败")
        self.status_text.config(text="提取失败")

    def stop_extract(self):
        """停止提取"""
        messagebox.showinfo("提示", "停止功能开发中...")
        self.stop_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.NORMAL)

    def clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log("界面日志已清空", "INFO")

    def log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((timestamp, message, level))

        color_map = {
            "INFO": "#3c4043",
            "DEBUG": "#80868b",
            "SUCCESS": "#34a853",
            "WARNING": "#f57c00",
            "ERROR": "#ea4335"
        }
        color = color_map.get(level, "#3c4043")

        self.log_text.config(state='normal')
        log_line = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_line, color)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

        self.logger.log(logging.INFO, message)

    def update_log(self):
        """更新日志显示（保持向后兼容）"""
        self.root.after(100, self.update_log)

    def open_output_dir(self):
        """打开输出目录"""
        output_dir = os.path.abspath(OUTPUT_DIR)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        import platform
        system = platform.system()

        try:
            if system == "Windows":
                os.startfile(output_dir)
            elif system == "Darwin":
                os.system(f'open "{output_dir}"')
            else:
                os.system(f'xdg-open "{output_dir}"')
            self.log(f"已打开输出目录: {output_dir}", "SUCCESS")
        except Exception as e:
            self.log(f"打开目录失败: {e}", "ERROR")

    def get_date_string(self, year_var, month_var, day_var):
        """获取日期字符串"""
        year = year_var.get()
        month = month_var.get()
        day = day_var.get()

        try:
            last_day = calendar.monthrange(year, month)[1]
            day = min(day, last_day)
            return f"{year}-{month:02d}-{day:02d}"
        except ValueError:
            return None

    def load_config(self):
        """加载配置"""
        self.log("通用数据提取工具已就绪", "INFO")
        self.log(f"支持的数据表: {', '.join(TableConfig.get_table_names())}", "INFO")

    def on_closing(self):
        """窗口关闭"""
        self.logger.info("=" * 50)
        self.logger.info("通用数据提取工具 GUI 关闭")
        self.logger.info("=" * 50)
        self.root.destroy()


# ==================== 授权验证模块 ====================
import hashlib
import platform
import subprocess

def get_macos_hw_info():
    """获取macOS硬件信息"""
    hw_info = {"cpu_id": "", "board_sn": "", "disk_sn": "", "mac": ""}
    try:
        cmd = ["ioreg", "-l", "-w0", "-r", "-c", "IOPlatformExpertDevice", "-d", "2"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        hw_info["board_sn"] = output.split('"IOPlatformSerialNumber" = ')[1].split('"')[1].strip()
    except:
        hw_info["board_sn"] = "unknown_board"
    try:
        cmd = ["sysctl", "-n", "machdep.cpu.brand_string"]
        hw_info["cpu_id"] = subprocess.check_output(cmd).decode("utf-8").strip()
    except:
        hw_info["cpu_id"] = "unknown_cpu"
    try:
        cmd = ["diskutil", "info", "/"]
        output = subprocess.check_output(cmd).decode("utf-8")
        hw_info["disk_sn"] = output.split("Volume UUID:")[1].split("\n")[0].strip()
    except:
        hw_info["disk_sn"] = "unknown_disk"
    try:
        cmd = ["ifconfig", "en0"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        hw_info["mac"] = output.split("ether")[1].split(" ")[1].strip().replace(":", "")
    except:
        hw_info["mac"] = "unknown_mac"
    return hw_info


def get_windows_hw_info():
    """获取Windows硬件信息"""
    try:
        import wmi
        c = wmi.WMI()
        hw_info = {"cpu_id": "", "board_sn": "", "disk_sn": "", "mac": ""}
        cpu_list = c.Win32_Processor()
        hw_info["cpu_id"] = cpu_list[0].ProcessorId.strip() if (cpu_list and cpu_list[0].ProcessorId) else "unknown_cpu"
        board_list = c.Win32_BaseBoard()
        hw_info["board_sn"] = board_list[0].SerialNumber.strip() if (board_list and board_list[0].SerialNumber) else "unknown_board"
        disk_list = c.Win32_DiskDrive()
        hw_info["disk_sn"] = disk_list[0].SerialNumber.strip() if (disk_list and disk_list[0].SerialNumber) else "unknown_disk"
        nic_list = c.Win32_NetworkAdapterConfiguration(IPEnabled=True)
        hw_info["mac"] = nic_list[0].MACAddress.strip().replace(":", "") if (nic_list and nic_list[0].MACAddress) else "unknown_mac"
        return hw_info
    except:
        return {"cpu_id": "unknown", "board_sn": "unknown", "disk_sn": "unknown", "mac": "unknown"}


def get_linux_hw_info():
    """获取Linux硬件信息"""
    hw_info = {"cpu_id": "", "board_sn": "", "disk_sn": "", "mac": ""}
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f.readlines():
                if "serial" in line.lower():
                    hw_info["cpu_id"] = line.split(":")[1].strip()
                    break
        hw_info["cpu_id"] = hw_info["cpu_id"] if hw_info["cpu_id"] else "unknown_cpu"
    except:
        hw_info["cpu_id"] = "unknown_cpu"
    try:
        with open("/sys/devices/virtual/dmi/id/board_serial", "r") as f:
            hw_info["board_sn"] = f.read().strip()
    except:
        hw_info["board_sn"] = "unknown_board"
    try:
        cmd = ["lsblk", "-o", "SERIAL", "-n", "/dev/sda"]
        hw_info["disk_sn"] = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
    except:
        hw_info["disk_sn"] = "unknown_disk"
    try:
        for path in ["/sys/class/net/eth0/address", "/sys/class/net/ens33/address"]:
            if os.path.exists(path):
                with open(path, "r") as f:
                    hw_info["mac"] = f.read().strip().replace(":", "")
                break
        hw_info["mac"] = hw_info.get("mac", "unknown_mac")
    except:
        hw_info["mac"] = "unknown_mac"
    return hw_info


def get_hw_info():
    """跨平台获取硬件信息"""
    system = platform.system()
    if system == "Windows":
        return get_windows_hw_info()
    elif system == "Darwin":
        return get_macos_hw_info()
    elif system == "Linux":
        return get_linux_hw_info()
    else:
        return {"cpu_id": "unknown", "board_sn": "unknown", "disk_sn": "unknown", "mac": "unknown"}


def generate_machine_fingerprint(hw_info):
    """生成机器指纹"""
    raw_str = f"{hw_info['cpu_id']}-{hw_info['board_sn']}-{hw_info['disk_sn']}-{hw_info['mac']}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


# ==================== 授权验证系统 ====================

def aes_encrypt(plain_text, key):
    """AES加密"""
    import os
    iv = os.urandom(16)
    cipher = AES_Cipher.new(key, AES_Cipher.MODE_CBC, iv)
    padded_data = pad(plain_text.encode("utf-8"), 16)
    encrypted_data = cipher.encrypt(padded_data)
    return iv + encrypted_data


def aes_decrypt(encrypted_data, key):
    """AES解密"""
    iv = encrypted_data[:16]
    cipher = AES_Cipher.new(key, AES_Cipher.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_data[16:]), 16)
    return decrypted_data.decode("utf-8")


def rsa_verify(data, signature, public_key_pem):
    """RSA签名验证"""
    try:
        from Crypto.Hash import SHA256
        from Crypto.Signature import pkcs1_15

        key = RSA.import_key(public_key_pem)
        h = SHA256.new(data.encode("utf-8"))
        verifier = pkcs1_15.new(key)
        verifier.verify(h, base64.b64decode(signature))
        return True
    except Exception as e:
        print(f"[ERROR] RSA验签失败: {e}")
        return False


def rsa_sign(data, private_key):
    """RSA签名（服务端使用）"""
    from Crypto.Hash import SHA256
    from Crypto.Signature import pkcs1_15
    h = SHA256.new(data.encode("utf-8"))
    signature = pkcs1_15.new(private_key).sign(h)
    return base64.b64encode(signature).decode("utf-8")


def load_license_time():
    """加载上次验证时间"""
    if os.path.exists(LICENSE_TIME_FILE):
        try:
            with open(LICENSE_TIME_FILE, "rb") as f:
                encrypted_time = f.read()
            return aes_decrypt(encrypted_time, LICENSE_AES_KEY)
        except:
            pass
    return None


def save_license_time(verify_time):
    """保存验证时间（使用AES加密）"""
    encrypted_time = aes_encrypt(verify_time, LICENSE_AES_KEY)
    with open(LICENSE_TIME_FILE, "wb") as f:
        f.write(encrypted_time)


def verify_license():
    """验证授权，返回 (是否通过, 机器码, 错误信息, 过期时间)"""
    print("[DEBUG] 开始授权验证...")

    placeholder_key = "-----BEGIN PUBLIC KEY-----\n请在这里粘贴你的RSA公钥内容\n-----END PUBLIC KEY-----"
    if RSA_PUBLIC_KEY.strip() == placeholder_key.strip():
        print("[ERROR] 请先配置RSA公钥！")
        return False, None, "未配置RSA公钥，请联系开发者", None

    current_fp = generate_machine_fingerprint(get_hw_info())
    print(f"[DEBUG] 当前机器码: {current_fp}")

    if not os.path.exists(LICENSE_FILE):
        print("[DEBUG] 未找到 license.dat 文件")
        return False, current_fp, "未检测到授权文件（license.dat）", None

    try:
        with open(LICENSE_FILE, "rb") as f:
            license_data = f.read()

        # 解析license格式：SN | RSA签名 | AES加密的过期时间
        # 格式：SN长度(4字节) + SN + Base64签名 + 过期时间密文
        import struct
        sn_len = struct.unpack(">I", license_data[:4])[0]
        sn = license_data[4:4+sn_len].decode("utf-8")
        remaining = license_data[4+sn_len:]

        # 分割签名和加密时间（中间用 | 分隔）
        parts = remaining.split(b"|")
        if len(parts) != 2:
            print("[ERROR] 授权文件格式错误")
            return False, current_fp, "授权文件格式错误", None

        signature = parts[0].decode("utf-8")
        encrypted_expiry = parts[1]

        # 1. RSA验签：验证SN是否被篡改
        print("[DEBUG] 正在进行RSA签名验证...")
        if not rsa_verify(sn, signature, RSA_PUBLIC_KEY):
            print("[ERROR] RSA签名验证失败")
            return False, current_fp, "授权签名验证失败，授权文件可能被篡改", None

        # 2. 验证机器码是否匹配
        if sn != current_fp:
            print("[ERROR] 机器码不匹配")
            return False, current_fp, "授权验证失败，当前设备与授权文件不匹配", None

        # 3. AES解密获取过期时间
        print("[DEBUG] 正在解密授权时间...")
        expiry_time_str = aes_decrypt(encrypted_expiry, LICENSE_AES_KEY)
        expiry_time = datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S")
        print(f"[DEBUG] 授权过期时间: {expiry_time_str}")

        # 4. 检查是否过期
        current_time = datetime.now()
        if current_time > expiry_time:
            print("[ERROR] 授权已过期")
            return False, current_fp, f"授权已过期（{expiry_time_str}）", expiry_time_str

        # 5. 时间单调性校验：确保时间只能递增
        last_verify_time = load_license_time()
        if last_verify_time:
            last_time = datetime.strptime(last_verify_time, "%Y-%m-%d %H:%M:%S")
            if current_time < last_time:
                print("[ERROR] 系统时间被回改，拒绝验证")
                return False, current_fp, "检测到系统时间被回改，请恢复正确时间", None

        # 6. 更新验证时间（单向递增）
        print("[DEBUG] 更新验证时间...")
        save_license_time(current_time.strftime("%Y-%m-%d %H:%M:%S"))

        print("[SUCCESS] 授权验证通过")
        return True, None, None, expiry_time_str

    except Exception as e:
        print(f"[ERROR] 授权验证失败: {e}")
        return False, current_fp, f"授权验证失败：{e}", None


def show_machine_code_dialog(parent, machine_code, error_title="授权验证失败"):
    """显示机器码弹窗，供用户复制发给作者"""
    import tkinter as tk
    from tkinter import ttk
    
    exit_flag = [False]
    
    # 创建根窗口
    root = tk.Tk()
    root.title(error_title)
    root.geometry("550x320")
    root.resizable(False, False)
    
    # 居中显示
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 550) // 2
    y = (screen_height - 320) // 2
    root.geometry(f"550x320+{x}+{y}")
    
    # 设置为始终在最前
    root.attributes('-topmost', True)
    
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 标题
    ttk.Label(main_frame, text="授权验证失败，请联系作者",
              font=("Arial", 14, "bold"), foreground="#D32F2F").pack(pady=(0, 10))
    
    # 提示信息
    ttk.Label(main_frame, text="您的机器码如下，请复制后发给作者进行验证：",
              font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
    
    # 机器码文本框（可复制）
    text_frame = ttk.Frame(main_frame)
    text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
    machine_text = tk.Text(text_frame, height=4, font=("Courier New", 11), wrap=tk.WORD,
                           bg="#F5F5F5", fg="#333333")
    machine_text.insert("1.0", machine_code)
    machine_text.config(state=tk.DISABLED)  # 只读但可复制
    machine_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=machine_text.yview)
    machine_text.config(yscrollcommand=machine_scroll.set)
    machine_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    machine_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 复制按钮
    def copy_to_clipboard():
        root.clipboard_clear()
        root.clipboard_append(machine_code)
        copy_btn.config(text="已复制!", state=tk.DISABLED)
        root.after(2000, lambda: copy_btn.config(text="复制机器码", state=tk.NORMAL))
    
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(15, 0))
    
    copy_btn = ttk.Button(button_frame, text="复制机器码", command=copy_to_clipboard)
    copy_btn.pack(side=tk.LEFT, padx=5)
    
    def do_exit():
        exit_flag[0] = True
        root.destroy()
    
    exit_btn = ttk.Button(button_frame, text="退出程序", command=do_exit)
    exit_btn.pack(side=tk.LEFT, padx=5)
    
    root.mainloop()
    
    if exit_flag[0]:
        sys.exit(1)


def main():
    """主函数"""
    import tkinter as tk
    print("[MAIN] 程序启动")
    ensure_dirs()
    
    # 授权验证
    is_valid, machine_code, error_msg, expiry_time = verify_license()
    print(f"[MAIN] 验证完成: is_valid={is_valid}")
    
    if not is_valid:
        print("[MAIN] 授权验证失败，准备显示机器码弹窗...")
        show_machine_code_dialog(None, machine_code, f"授权验证失败 - {error_msg}")
        print("[MAIN] 弹窗已关闭，退出程序")
        sys.exit(1)
    
    # 授权通过，打开软件
    root = tk.Tk()
    app = UniversalExtractorGUI(root, expiry_time=expiry_time)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
