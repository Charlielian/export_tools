# -*- coding: utf-8 -*-
"""
主窗口模块
提供应用程序的主界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import logging
import os
from datetime import datetime

from gui.widgets import LogTextHandler, TableConfig
from core.auth import LoginManager
from core.query import JXCXQuery
from core.export import export_with_format
from utils.logger import set_log_file, ensure_dirs
from utils.config import LOG_DIR, EXPIRY_DATE


class NqiToolGUI:
    """NQI工具主窗口"""

    def __init__(self, root, expiry_time=None):
        self.root = root
        self.root.title("NQI工具")
        self.root.geometry("950x650")
        self.root.minsize(800, 600)

        self.expiry_time = datetime.strptime(EXPIRY_DATE, "%Y-%m-%d") if not expiry_time else expiry_time
        self.session = None
        self.jxcx = None
        self.query_thread = None
        self.is_querying = False

        self._setup_logging()
        self._create_widgets()
        self._bind_events()

        self.logger.info("=" * 50)
        self.logger.info("NQI工具 GUI 启动")
        self.logger.info(f"日志文件: {self.log_file_path}")
        self.logger.info("=" * 50)

        self.load_config()

    def _setup_logging(self):
        """设置日志系统"""
        ensure_dirs()
        log_filename = f"NqiTool_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.log_file_path = os.path.join(LOG_DIR, log_filename)
        set_log_file(self.log_file_path)

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                    datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def _create_widgets(self):
        """创建界面组件"""
        title_frame = tk.Frame(self.root, bg='#165DFF', height=50)
        title_frame.pack(side=tk.TOP, fill=tk.X)

        title = tk.Label(title_frame, text="NQI工具",
                         font=('Microsoft YaHei UI', 18, 'bold'),
                         bg='#165DFF', fg='white')
        title.pack(side=tk.LEFT, padx=20, pady=10)

        version_label = tk.Label(title_frame, text="NqiTool v1.0",
                                font=('Arial', 10),
                                bg='#165DFF', fg='white')
        version_label.pack(side=tk.RIGHT, padx=20, pady=10)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.LabelFrame(main_frame, text="操作面板", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        self._create_operation_panel(left_frame)

        right_frame = ttk.LabelFrame(main_frame, text="日志输出", padding=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(right_frame, height=30,
                                                   font=('Consolas', 9),
                                                   state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        handler = LogTextHandler(self.log_text)
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)

        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(bottom_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)

        expiry_label = ttk.Label(bottom_frame,
                                text=f"授权到期: {self.expiry_time.strftime('%Y-%m-%d')}")
        expiry_label.pack(side=tk.RIGHT)

    def _create_operation_panel(self, parent):
        """创建操作面板"""
        ttk.Label(parent, text="数据表:").pack(anchor=tk.W, pady=(0, 5))

        self.table_var = tk.StringVar()
        table_names = TableConfig.get_table_names()
        self.table_combo = ttk.Combobox(parent, textvariable=self.table_var,
                                        values=table_names, state='readonly', width=20)
        self.table_combo.pack(fill=tk.X, pady=(0, 10))
        if table_names:
            self.table_combo.current(0)

        ttk.Label(parent, text="起始日期:").pack(anchor=tk.W, pady=(0, 5))
        self.start_date_entry = ttk.Entry(parent, width=22)
        self.start_date_entry.pack(fill=tk.X, pady=(0, 10))
        self.start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        ttk.Label(parent, text="结束日期:").pack(anchor=tk.W, pady=(0, 5))
        self.end_date_entry = ttk.Entry(parent, width=22)
        self.end_date_entry.pack(fill=tk.X, pady=(0, 10))
        self.end_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        ttk.Label(parent, text="地市（可选）:").pack(anchor=tk.W, pady=(0, 5))
        self.city_entry = ttk.Entry(parent, width=22)
        self.city_entry.pack(fill=tk.X, pady=(0, 10))

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)

        self.login_btn = ttk.Button(btn_frame, text="登录", command=self._on_login)
        self.login_btn.pack(fill=tk.X, pady=(0, 5))

        self.query_btn = ttk.Button(btn_frame, text="开始查询", command=self._on_query,
                                    state=tk.DISABLED)
        self.query_btn.pack(fill=tk.X, pady=(0, 5))

        self.export_btn = ttk.Button(btn_frame, text="导出Excel", command=self._on_export,
                                     state=tk.DISABLED)
        self.export_btn.pack(fill=tk.X)

        self.clear_btn = ttk.Button(parent, text="清空日志", command=self._clear_log)
        self.clear_btn.pack(fill=tk.X, pady=(10, 0))

    def _bind_events(self):
        """绑定事件"""
        self.table_combo.bind('<<ComboboxSelected>>', lambda e: self._on_table_selected())

    def _on_table_selected(self):
        """数据表选择事件"""
        table_name = self.table_var.get()
        self.log(f"选择了数据表: {table_name}", "INFO")

    def _on_login(self):
        """登录按钮点击事件"""
        self.log("开始登录...", "INFO")
        thread = threading.Thread(target=self._login_worker)
        thread.daemon = True
        thread.start()

    def _login_worker(self):
        """登录工作线程"""
        try:
            login_mgr = LoginManager(parent=self.root)
            if login_mgr.login():
                self.session = login_mgr.sess
                self.jxcx = JXCXQuery(self.session)
                self.root.after(0, self._on_login_success)
            else:
                self.root.after(0, lambda: self.log("登录失败", "ERROR"))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"登录异常: {e}", "ERROR"))

    def _on_login_success(self):
        """登录成功回调"""
        self.log("登录成功！", "SUCCESS")
        self.query_btn.config(state=tk.NORMAL)
        self.login_btn.config(state=tk.DISABLED, text="已登录")

    def _on_query(self):
        """查询按钮点击事件"""
        if self.is_querying:
            self.log("正在查询中，请稍候...", "WARNING")
            return

        table_name = self.table_var.get()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()
        city = self.city_entry.get().strip()

        if not start_date or not end_date:
            messagebox.showwarning("警告", "请输入日期范围")
            return

        self.is_querying = True
        self.query_btn.config(state=tk.DISABLED, text="查询中...")
        self.export_btn.config(state=tk.DISABLED)

        self.log(f"开始查询: {table_name}", "INFO")
        self.log(f"日期范围: {start_date} 至 {end_date}", "INFO")
        if city:
            self.log(f"地市: {city}", "INFO")

        self.query_thread = threading.Thread(target=self._query_worker,
                                            args=(table_name, start_date, end_date, city))
        self.query_thread.daemon = True
        self.query_thread.start()

    def _query_worker(self, table_name, start_date, end_date, city):
        """查询工作线程"""
        try:
            result = self._execute_query(table_name, start_date, end_date, city)
            self.root.after(0, self._on_query_complete, result)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"查询异常: {e}", "ERROR"))
            self.root.after(0, self._on_query_failed)

    def _execute_query(self, table_name, start_date, end_date, city):
        """执行查询"""
        table_config = TableConfig.get_table_config(table_name)
        if not table_config:
            return None

        self.jxcx.enter_jxcx()

        conditions = table_config.get('default_conditions', []).copy()
        conditions.append({'field': 'starttime', 'operator': '>=', 'value': start_date})
        conditions.append({'field': 'starttime', 'operator': '<=', 'value': end_date})
        if city:
            conditions.append({'field': 'city', 'operator': '=', 'value': city})

        payload = self.jxcx.build_payload_from_config(
            table_config['table_key'],
            table_config['fieldtype'],
            conditions,
            table_config['api_type']
        )

        if payload:
            self.jxcx.get_table(payload)
            return {'success': True}

        return None

    def _on_query_complete(self, result):
        """查询完成回调"""
        self.is_querying = False
        self.query_btn.config(state=tk.NORMAL, text="开始查询")
        self.export_btn.config(state=tk.NORMAL)
        if result and result.get('success'):
            self.log("查询完成！", "SUCCESS")

    def _on_query_failed(self):
        """查询失败回调"""
        self.is_querying = False
        self.query_btn.config(state=tk.NORMAL, text="开始查询")

    def _on_export(self):
        """导出按钮点击事件"""
        self.log("导出功能开发中...", "INFO")

    def _clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')

    def log(self, message, level="INFO"):
        """输出日志"""
        self.log_text.config(state='normal')

        tag_map = {
            'INFO': 'INFO',
            'ERROR': 'ERROR',
            'WARNING': 'WARNING',
            'SUCCESS': 'SUCCESS'
        }

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}\n"

        self.log_text.insert(tk.END, log_line, (tag_map.get(level, 'INFO'),))
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def load_config(self):
        """加载配置"""
        self.log("NQI工具已就绪", "INFO")
        self.log(f"支持的数据表: {', '.join(TableConfig.get_table_names())}", "INFO")

    def run(self):
        """运行应用"""
        self.root.mainloop()
