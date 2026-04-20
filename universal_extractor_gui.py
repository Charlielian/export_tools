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

# ==================== 第三方依赖 ====================
import requests
import pandas as pd
from lxml import etree
try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
except ModuleNotFoundError:
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Cipher import PKCS1_v1_5
import base64
from urllib.parse import quote
import random
import pickle
import json
import yaml


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
                    'timeField', 'cellField', 'cityField', 'result', 'where', 'indexcount']
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
        """获取查询数据"""
        if not self.enabled:
            self.enter_jxcx()

        print(f"[DEBUG-TABLE] ========== 开始查询数据 ==========")
        print(f"[DEBUG-TABLE] 请求URL: {JXCX_URL}")

        # 打印表名
        if 'result' in payload and 'result' in payload['result']:
            table_names = [r.get('table', '') for r in payload['result']['result']]
            print(f"[DEBUG-TABLE] 查询表名: {set(table_names)}")

        # 打印 where 条件
        if 'where' in payload:
            print(f"[DEBUG-TABLE] 查询条件 (where): {json.dumps(payload['where'], ensure_ascii=False)}")

        # 先获取总数
        print(f"[DEBUG-TABLE] 调用 get_table_count 获取数据总数...")
        total_count = self.get_table_count(payload)
        print(f"[DEBUG-TABLE] 返回的总数: {total_count}")

        if total_count == 0:
            print(f"[WARNING-TABLE] 数据总数为0，尝试直接查询不限制条数...")

        if 'length' in payload:
            if total_count > 0:
                payload['length'] = total_count
                print(f"[DEBUG-TABLE] 设置 payload length: {total_count}")
            else:
                payload['length'] = 5000
                print(f"[DEBUG-TABLE] 总数为0，设置 length 为 5000 尝试查询")

        payload_encoded = self._encode_payload(payload)
        print(f"[DEBUG-TABLE] 编码后的参数 (前800字符): {payload_encoded[:800]}...")

        try:
            res = self.sess.post(JXCX_URL, data=payload_encoded, headers=HEADERS, timeout=120)
            print(f"[DEBUG-TABLE] 响应状态码: {res.status_code}")

            if res.status_code != 200:
                print(f"[ERROR-TABLE] 请求失败，状态码: {res.status_code}")
                print(f"[ERROR-TABLE] 响应内容: {res.text[:500]}")
                return pd.DataFrame() if to_df else {}
        except Exception as e:
            print(f"[ERROR-TABLE] 请求异常: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame() if to_df else {}

        try:
            result = json.loads(res.content)
            print(f"[DEBUG-TABLE] 响应JSON keys: {result.keys()}")

            # 打印可能的错误信息
            if 'msg' in result:
                print(f"[DEBUG-TABLE] 响应消息: {result['msg']}")
            if 'message' in result and result['message']:
                print(f"[DEBUG-TABLE] 响应消息: {result['message']}")

            # 检查是否有错误
            if 'message' in result and result['message']:
                if '不存在' in str(result['message']):
                    print(f"[WARNING-TABLE] 服务器返回: 数据不存在")
                    return pd.DataFrame() if to_df else {}

            data_list = result.get('data') or []
            print(f"[DEBUG-TABLE] 返回数据条数: {len(data_list)}")
            if data_list:
                print(f"[DEBUG-TABLE] 数据样例 (第一条): {data_list[0]}")

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
                return result
        except Exception as e:
            print(f"[ERROR-TABLE] 解析响应异常: {e}")
            print(f"[ERROR-TABLE] 响应内容 (前500字符): {res.text[:500]}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame() if to_df else {}
    
    def _encode_payload(self, payload):
        """编码payload为URL格式"""
        out_list = []
        for key in payload:
            if key not in ['result', 'where']:
                right = str(payload[key]) if type(payload[key]) is int else quote(str(payload[key]))
            else:
                right = quote(json.dumps(payload[key]))
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
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': 'RRC连接平均数--忙时', 'feild': 'bh_rrc_connmean', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '5G小区容量报表 - 天粒度', 'table': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
             'tableName': '5G小区容量报表 - 天粒度', 'datatype': 'decimal', 'columntype': '1',
             'feildName': 'RRC连接最大数--忙时', 'feild': 'bh_rrc_connmax', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
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
    print(f"[DEBUG-PAYLOAD] 5G小区容量报表 payload 生成完成，表名: appdbv3.a_adhoc_capacity_nr_nrcell_d")
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
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '详细使用频段', 'feild': 'frequency_band_detail', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属基站id', 'feild': 'enodeb_id', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属基站名称', 'feild': 'enodeb_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'PCI', 'feild': 'pci', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'TAC', 'feild': 'tac', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '方位角', 'feild': 'azimuth', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '电下倾角', 'feild': 'tilt', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '挂高', 'feild': 'height', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '设备维护单位', 'feild': 'maintain_department', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '入网时间', 'feild': 'setup_time', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '一级标签', 'feild': 'cover_scene1', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '二级标签', 'feild': 'cover_scene2', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '4G小区工参', 'table': 'appdbv3.v_a_common_cfg_lte_cellant_d', 'tableName': '4G小区工参', 'datatype': 'character varying', 'columntype': 1, 'feildName': '三级标签', 'feild': 'cover_scene3', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True},
        ],
        'indexcount': 0
    }
    return payload


def get_volte_warning_payload():
    """获取VoLTE小区监控预警payload"""
    print("[DEBUG-PAYLOAD] 生成 VoLTE小区监控预警 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名称', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '初始注册成功率（控制面）', 'feild': 'cs_reg1_suss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE注册成功率（控制面）', 'feild': 'cs_reg_suss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE用户面丢包率', 'feild': 'volte_user_pkt_loss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE用户面时延（秒）', 'feild': 'volte_user_delay', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE接通率', 'feild': 'volte_connect_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE掉话率', 'feild': 'volte_drop_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'ESRVCC切换成功率', 'feild': 'esrvcc_ho_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE语音话务量（Erl）', 'feild': 'volte_voice_traffic', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE视频话务量（Erl）', 'feild': 'volte_video_traffic', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE语音QCI=1承载成功率', 'feild': 'volte_voice_qci1_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE视频QCI=2承载成功率', 'feild': 'volte_video_qci2_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'ERAB建立成功率', 'feild': 'erab_setup_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'ERAB掉线率', 'feild': 'erab_drop_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'RRC连接建立成功率', 'feild': 'rrc_setup_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
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
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': '---', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPS+FB+始呼网络接通率(SA控制起始)', 'feild': 'sacs_start_moc_net_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPS+FB+终呼网络接通率(SA控制起始)', 'feild': 'sacs_start_mtc_net_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPS+FB+始呼网络接通率(CSCF控制起始)', 'feild': 'saccs_start_moc_net_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPS+FB+终呼网络接通率(CSCF控制起始)', 'feild': 'saccs_start_mtc_net_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPSFB语音话务量(Erl)', 'feild': 'epsfb_voice_traffic', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPSFB掉话率', 'feild': 'epsfb_drop_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE呼迁成功率', 'feild': 'volte_ho_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'ESRVCC切换成功率', 'feild': 'esrvcc_ho_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
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
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'gnodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '5G+SA+IMS+CSCF初始注册成功率（SA控制起始）', 'feild': 'sacs_start_reg_init_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '5G+SA+IMS+CSCF注册成功率[含重注册]（SA控制起始）', 'feild': 'sacs_start_reg_suss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '5G+SA+IMS+CSCF初始注册成功率（CSCF控制起始）', 'feild': 'saccs_start_reg_init_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '5G+SA+IMS+CSCF注册成功率[含重注册]（CSCF控制起始）', 'feild': 'saccs_start_reg_suss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoNR语音话务量(Erl)', 'feild': 'vonr_voice_traffic', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoNR掉话率', 'feild': 'vonr_drop_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoNR用户面丢包率', 'feild': 'vonr_user_pkt_loss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoNR接通率', 'feild': 'vonr_connect_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
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
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区，网格，地市，分公司', 'timedimension': '小时,天,周,月',
        'enodebField': 'gnodeb_id', 'cgiField': 'ncgi',
        'timeField': 'starttime', 'cellField': 'nrcell', 'cityField': 'city',
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
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区，网格，地市，分公司', 'timedimension': '小时,天,周.月,忙时,15分钟',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
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
    """设置payload的查询城市"""
    print(f"[DEBUG-PAYLOAD] 设置查询城市: {city}")
    for condition in payload['where']:
        if condition['feild'] == 'city':
            condition['val'] = city
            print(f"[DEBUG-PAYLOAD] 设置 city = {city}")
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


# ==================== GUI应用 ====================
class UniversalExtractorGUI:
    """通用数据提取工具GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("通用数据提取工具")
        self.root.geometry("700x650")
        self.root.resizable(True, True)

        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass

        self.log_queue = queue.Queue()
        self.extractor = None
        self.is_logged_in = False

        self.setup_logging()
        self.create_widgets()
        self.update_log()
        self.load_config()

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)

        title_label = ttk.Label(main_frame, text="通用数据提取工具",
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 15))

        self.create_login_section(main_frame)
        self.create_query_section(main_frame)
        self.create_button_section(main_frame)
        self.create_progress_section(main_frame)
        self.create_log_section(main_frame)
        self.create_status_bar(main_frame)

    def create_login_section(self, parent):
        """登录配置区域"""
        login_frame = ttk.LabelFrame(parent, text="登录配置", padding="10")
        login_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        login_frame.columnconfigure(1, weight=1)
        login_frame.columnconfigure(3, weight=1)

        ttk.Label(login_frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.username_var = tk.StringVar(value=DEFAULT_USERNAME)
        ttk.Entry(login_frame, textvariable=self.username_var, width=25).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(login_frame, text="密码:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.password_var = tk.StringVar(value=DEFAULT_PASSWORD)
        ttk.Entry(login_frame, textvariable=self.password_var, show="*", width=25).grid(
            row=0, column=3, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.login_status_var = tk.StringVar(value="未登录")
        status_label = ttk.Label(login_frame, textvariable=self.login_status_var,
                                foreground="red", font=("Arial", 10, "bold"))
        status_label.grid(row=0, column=4, padx=10)

    def create_query_section(self, parent):
        """查询参数区域"""
        query_frame = ttk.LabelFrame(parent, text="查询参数", padding="10")
        query_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        query_frame.columnconfigure(1, weight=1)
        query_frame.columnconfigure(3, weight=1)

        # 数据表分类定义
        TABLE_CATEGORIES = {
            '干扰': ['5G干扰小区', '4G干扰小区'],
            '容量': ['5G小区容量报表', '重要场景-天'],
            '工参': ['5G小区工参报表', '4G小区工参报表'],
            '语音报表': ['VoLTE小区监控预警', 'VONR小区监控预警', 'EPSFB小区监控预警'],
            '小区性能': ['5G小区性能KPI报表', '4G小区性能KPI报表'],
        }

        ttk.Label(query_frame, text="数据表:").grid(row=0, column=0, sticky=(tk.W, tk.N), padx=5, pady=(8, 0))
        
        # 上部：分类复选框行
        category_frame = ttk.LabelFrame(query_frame, text="分类", padding=5)
        category_frame.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=(5, 0))
        
        self.category_vars = {}
        for cat_name in TABLE_CATEGORIES.keys():
            var = tk.BooleanVar(value=False)
            self.category_vars[cat_name] = var
            cb = ttk.Checkbutton(category_frame, text=cat_name, variable=var,
                                command=lambda c=cat_name: self._on_category_changed(c))
            cb.pack(side=tk.LEFT, padx=10, pady=2)
        
        # 下部：数据表复选框（按分类分组）
        check_frame = ttk.LabelFrame(query_frame, text="报表列表", padding=5)
        check_frame.grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=(5, 5))
        
        # 复选框变量字典
        self.table_vars = {}
        table_names = TableConfig.get_table_names()
        
        # 按分类创建复选框，使用紧凑的网格布局
        cols = 2
        all_tables = []
        for cat_name, tables in TABLE_CATEGORIES.items():
            all_tables.extend(tables)
        
        for i, name in enumerate(all_tables):
            row = i // cols
            col = i % cols
            var = tk.BooleanVar(value=(i == 0))  # 默认选中第一项
            self.table_vars[name] = var
            cb = ttk.Checkbutton(check_frame, text=name, variable=var, 
                                command=self._on_table_checkbox_changed)
            cb.grid(row=row, column=col, sticky=tk.W, padx=8, pady=1)
        
        # 全选/取消全选按钮
        btn_frame = ttk.Frame(query_frame)
        btn_frame.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5, pady=(0, 5))
        ttk.Button(btn_frame, text="全选", width=8, 
                   command=self._select_all_tables).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="取消全选", width=8, 
                   command=self._deselect_all_tables).pack(side=tk.LEFT, padx=2)

        ttk.Label(query_frame, text="地市:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=8)
        self.city_var = tk.StringVar(value="阳江")
        ttk.Entry(query_frame, textvariable=self.city_var, width=25).grid(
            row=2, column=1, columnspan=3, sticky=tk.W, padx=5, pady=8)

        ttk.Label(query_frame, text="开始日期:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=8)
        self.start_date_var = tk.StringVar()
        start_frame = ttk.Frame(query_frame)
        start_frame.grid(row=3, column=1, columnspan=3, sticky=tk.W, padx=5, pady=8)

        ttk.Label(start_frame, text="年:").grid(row=0, column=0)
        current_year = datetime.now().year
        self.start_year_var = tk.IntVar(value=current_year)
        start_year_combo = ttk.Combobox(start_frame, textvariable=self.start_year_var,
                                       values=list(range(2020, current_year + 1)),
                                       width=6, state="readonly")
        start_year_combo.grid(row=0, column=1)

        ttk.Label(start_frame, text="月:").grid(row=0, column=2, padx=(10, 0))
        self.start_month_var = tk.IntVar(value=datetime.now().month)
        start_month_combo = ttk.Combobox(start_frame, textvariable=self.start_month_var,
                                       values=list(range(1, 13)),
                                       width=4, state="readonly")
        start_month_combo.grid(row=0, column=3)

        ttk.Label(start_frame, text="日:").grid(row=0, column=4, padx=(10, 0))
        self.start_day_var = tk.IntVar(value=1)
        start_day_combo = ttk.Combobox(start_frame, textvariable=self.start_day_var,
                                      values=list(range(1, 32)),
                                      width=4, state="readonly")
        start_day_combo.grid(row=0, column=5)

        ttk.Label(query_frame, text="结束日期:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=8)
        end_frame = ttk.Frame(query_frame)
        end_frame.grid(row=4, column=1, columnspan=3, sticky=tk.W, padx=5, pady=8)

        ttk.Label(end_frame, text="年:").grid(row=0, column=0)
        self.end_year_var = tk.IntVar(value=current_year)
        end_year_combo = ttk.Combobox(end_frame, textvariable=self.end_year_var,
                                     values=list(range(2020, current_year + 1)),
                                     width=6, state="readonly")
        end_year_combo.grid(row=0, column=1)

        ttk.Label(end_frame, text="月:").grid(row=0, column=2, padx=(10, 0))
        self.end_month_var = tk.IntVar(value=datetime.now().month)
        end_month_combo = ttk.Combobox(end_frame, textvariable=self.end_month_var,
                                     values=list(range(1, 13)),
                                     width=4, state="readonly")
        end_month_combo.grid(row=0, column=3)

        ttk.Label(end_frame, text="日:").grid(row=0, column=4, padx=(10, 0))
        self.end_day_var = tk.IntVar(value=datetime.now().day - 1 if datetime.now().day > 1 else 1)
        end_day_combo = ttk.Combobox(end_frame, textvariable=self.end_day_var,
                                    values=list(range(1, 32)),
                                    width=4, state="readonly")
        end_day_combo.grid(row=0, column=5)

        quick_frame = ttk.Frame(query_frame)
        quick_frame.grid(row=5, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(5, 0))

        ttk.Label(quick_frame, text="快捷选择:").grid(row=0, column=0, padx=(0, 5))

        ttk.Button(quick_frame, text="昨天", width=8,
                   command=lambda: self.set_quick_date(1)).grid(row=0, column=1, padx=2)
        ttk.Button(quick_frame, text="近7天", width=8,
                   command=lambda: self.set_quick_date(7)).grid(row=0, column=2, padx=2)
        ttk.Button(quick_frame, text="近30天", width=8,
                   command=lambda: self.set_quick_date(30)).grid(row=0, column=3, padx=2)

    def set_quick_date(self, days):
        """设置快捷日期"""
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days-1)

        self.start_year_var.set(start_date.year)
        self.start_month_var.set(start_date.month)
        self.start_day_var.set(start_date.day)

        self.end_year_var.set(end_date.year)
        self.end_month_var.set(end_date.month)
        self.end_day_var.set(end_date.day)

    def create_button_section(self, parent):
        """操作按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)

        self.login_btn = ttk.Button(button_frame, text="登录", command=self.login, width=12)
        self.login_btn.pack(side=tk.LEFT, padx=5)

        self.extract_btn = ttk.Button(button_frame, text="开始提取", command=self.start_extract,
                                     width=12, state=tk.DISABLED)
        self.extract_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_extract,
                                  width=12, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.open_dir_btn = ttk.Button(button_frame, text="打开输出目录",
                                      command=self.open_output_dir, width=12)
        self.open_dir_btn.pack(side=tk.LEFT, padx=5)

        self.clear_log_btn = ttk.Button(button_frame, text="清空日志",
                                       command=self.clear_log, width=12)
        self.clear_log_btn.pack(side=tk.LEFT, padx=5)

    def create_progress_section(self, parent):
        """进度条区域"""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                            maximum=100, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)

        self.progress_label_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.progress_label_var).grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=2)

    def create_log_section(self, parent):
        """日志显示区域"""
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding="5")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD,
                                                  height=12, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("DEBUG", foreground="#666666")
        self.log_text.tag_config("SUCCESS", foreground="green")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")

    def create_status_bar(self, parent):
        """状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=6, column=0, sticky=tk.W, pady=5)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def setup_logging(self):
        """初始化日志系统"""
        ensure_dirs()
        log_filename = datetime.now().strftime("universal_gui_log_%Y%m%d_%H%M%S.log")
        self.log_file_path = os.path.join(LOG_DIR, log_filename)

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

    def log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((timestamp, message, level))

        log_level_map = {
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "SUCCESS": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        self.logger.log(log_level_map.get(level, logging.INFO), message)

    def update_log(self):
        """更新日志显示"""
        try:
            while True:
                timestamp, message, level = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", level)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass

        self.root.after(100, self.update_log)

    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log("界面日志已清空", "INFO")

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

    def _on_table_checkbox_changed(self):
        """复选框状态改变时的回调（用于未来扩展）"""
        pass

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

    def get_selected_tables(self):
        """获取选中的数据表列表"""
        return [name for name, var in self.table_vars.items() if var.get()]

    def validate_inputs(self):
        """验证输入"""
        selected_tables = self.get_selected_tables()
        if not selected_tables:
            messagebox.showwarning("警告", "请至少选择一个数据表")
            return False

        city = self.city_var.get().strip()
        if not city:
            messagebox.showwarning("警告", "请输入地市名称")
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

        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showwarning("警告", "请输入用户名和密码")
            return

        self.login_btn.config(state=tk.DISABLED)
        self.update_status("正在登录...")
        self.log("开始登录...", "INFO")

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

            self.update_progress(30, "正在连接服务器...")
            success = self.extractor.login()

            builtins.print = original_print

            if success:
                self.update_progress(60, "登录成功，初始化即席查询...")

                builtins.print = custom_print
                jxcx_success = self.extractor.init_jxcx()
                builtins.print = original_print

                if jxcx_success:
                    self.is_logged_in = True
                    self.update_progress(100, "登录完成")
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
        self.login_status_var.set("已登录 ✓")
        self.login_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.NORMAL)
        self.update_status("登录成功，可以开始提取数据")
        messagebox.showinfo("成功", "登录成功！")

    def _login_failed_ui(self):
        """登录失败UI"""
        self.login_status_var.set("登录失败")
        self.login_btn.config(state=tk.NORMAL)
        self.update_status("登录失败")
        self.update_progress(0, "登录失败")
        messagebox.showerror("失败", "登录失败，请检查账号密码或网络连接")

    def start_extract(self):
        """开始提取"""
        if not self.is_logged_in:
            messagebox.showwarning("警告", "请先登录")
            return

        if not self.validate_inputs():
            return

        self.extract_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.update_status("正在提取数据...")

        thread = threading.Thread(target=self._extract_thread)
        thread.daemon = True
        thread.start()

    def _extract_thread(self):
        """提取数据线程 - 支持多表批量提取"""
        try:
            selected_tables = self.get_selected_tables()
            city = self.city_var.get().strip()
            start_date = self.get_date_string(self.start_year_var, self.start_month_var, self.start_day_var)
            end_date = self.get_date_string(self.end_year_var, self.end_month_var, self.end_day_var)

            total_tables = len(selected_tables)
            self.log(f"=" * 50, "INFO")
            self.log(f"开始批量提取数据，共 {total_tables} 个数据表", "INFO")
            self.log(f"地市: {city}", "INFO")
            self.log(f"日期范围: {start_date} 至 {end_date}", "INFO")
            self.log(f"=" * 50, "INFO")

            success_count = 0
            failed_count = 0

            for idx, table_name in enumerate(selected_tables):
                self.log(f"", "INFO")
                self.log(f"--- [{idx + 1}/{total_tables}] 正在处理: {table_name} ---", "INFO")

                table_config = TableConfig.get_table_config(table_name)
                if not table_config:
                    self.log(f"✗ 未找到数据表配置: {table_name}", "ERROR")
                    failed_count += 1
                    continue

                self.update_progress(int((idx / total_tables) * 100), f"正在提取 {table_name}...")

                try:
                    payload_func = table_config['payload_func']
                    payload = payload_func()

                    start_time = start_date + ' 00:00:00'
                    end_time = end_date + ' 23:59:59'
                    payload = set_payload_time(payload, start_time, end_time)
                    payload = set_payload_city(payload, city)

                    self.update_progress(int((idx / total_tables) * 100) + 10, "正在查询数据...")

                    df = self.extractor.extract_data(
                        payload=payload,
                        start_date=start_date,
                        end_date=end_date,
                        city=city
                    )

                    if df.empty:
                        self.log(f"⚠ 未查询到数据: {table_name}", "WARNING")
                        continue

                    self.update_progress(int(((idx + 0.8) / total_tables) * 100), "正在保存数据...")

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

            self.log(f"", "INFO")
            self.log(f"=" * 50, "INFO")
            self.log(f"批量提取完成！成功: {success_count}/{total_tables}", "SUCCESS" if success_count == total_tables else "INFO")
            if failed_count > 0:
                self.log(f"失败: {failed_count}/{total_tables}", "WARNING")
            self.log(f"=" * 50, "INFO")

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
        self.update_status("数据提取完成")
        self.update_progress(100, "提取完成")

    def _extract_failed_ui(self):
        """提取失败UI"""
        self.extract_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("数据提取失败")
        self.update_progress(0, "提取失败")

    def stop_extract(self):
        """停止提取"""
        messagebox.showinfo("提示", "停止功能开发中...")
        self.stop_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.NORMAL)

    def update_progress(self, value, label=""):
        """更新进度条"""
        self.root.after(0, lambda: self.progress_var.set(value))
        if label:
            self.root.after(0, lambda: self.progress_label_var.set(label))

    def update_status(self, message):
        """更新状态栏"""
        self.root.after(0, lambda: self.status_var.set(message))

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

# AES加密依赖
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad

LICENSE_FILE = "license.dat"
AES_KEY = b"GMCC_License_Key"  # 16字节


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


def aes_decrypt(encrypted_data):
    """AES解密"""
    iv = encrypted_data[:16]
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_data[16:]), 16)
    return decrypted_data.decode("utf-8")


def verify_license():
    """验证授权，返回True通过，False失败"""
    current_fp = generate_machine_fingerprint(get_hw_info())
    
    if not os.path.exists(LICENSE_FILE):
        print("=" * 60)
        print("  未检测到授权文件（license.dat），请联系管理员获取授权！")
        print(f"\n  您的机器码：\n  {current_fp}")
        print("  请将此机器码发给管理员以获取授权文件")
        print("=" * 60)
        return False
    try:
        with open(LICENSE_FILE, "rb") as f:
            encrypted_fp = f.read()
        stored_fp = aes_decrypt(encrypted_fp)
        if current_fp == stored_fp:
            print("授权验证通过")
            return True
        else:
            print("=" * 60)
            print("  授权验证失败！当前设备未授权，禁止使用！")
            print(f"\n  您的机器码：\n  {current_fp}")
            print("  请将此机器码发给管理员以获取授权文件")
            print("=" * 60)
            return False
    except Exception as e:
        print("=" * 60)
        print(f"  授权文件损坏或解密失败：{e}")
        print(f"\n  您的机器码：\n  {current_fp}")
        print("  请联系管理员重新获取授权文件")
        print("=" * 60)
        return False


def main():
    """主函数"""
    # 授权验证
    if not verify_license():
        input("\n按回车键退出...")
        sys.exit(1)
    
    ensure_dirs()
    root = tk.Tk()
    app = UniversalExtractorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
