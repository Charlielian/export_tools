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
from datetime import datetime, timedelta
import queue

from gui.widgets import LogTextHandler, TableConfig, MultiSelectDropdown
from core.auth import LoginManager
from core.query import JXCXQuery
from core.export import export_with_format
from utils.logger import set_log_file, ensure_dirs
from utils.config import LOG_DIR, EXPIRY_DATE, DEFAULT_USERNAME, DEFAULT_PASSWORD


class NqiToolGUI:
    """NQI工具主窗口"""

    def __init__(self, root, expiry_time=None):
        self.root = root
        self.root.title("NQI工具")
        self.root.geometry("1100x800")
        self.root.minsize(800, 600)

        self.expiry_time = datetime.strptime(EXPIRY_DATE, "%Y-%m-%d") if not expiry_time else expiry_time
        self.session = None
        self.jxcx = None
        self.query_thread = None
        self.is_querying = False
        self.log_queue = queue.Queue()

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
        try:
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
        except Exception as e:
            print(f"[WARNING] 初始化日志系统失败: {e}")
            self.logger = logging.getLogger()
            self.logger.setLevel(logging.DEBUG)

    def _create_widgets(self):
        """创建界面组件 - 使用现代化设计"""
        # 顶部蓝色标题栏
        self.header = tk.Frame(self.root, bg='#165DFF', height=60)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)

        # 标题栏左侧 - Logo和标题
        left_frame = tk.Frame(self.header, bg='#165DFF')
        left_frame.pack(side=tk.LEFT, padx=25, pady=12)

        icon_frame = tk.Frame(left_frame, bg='#1a6ce8', width=36, height=36)
        icon_frame.pack(side=tk.LEFT, padx=(0, 12))
        icon_frame.pack_propagate(False)
        icon_label = tk.Label(icon_frame, text="📊", font=('Segoe UI Emoji', 18),
                             bg='#1a6ce8', fg='white')
        icon_label.place(relx=0.5, rely=0.5, anchor='center')

        title_frame = tk.Frame(left_frame, bg='#165DFF')
        title_frame.pack(side=tk.LEFT)

        title = tk.Label(title_frame, text="NQI工具",
                        font=('Microsoft YaHei UI', 18, 'bold'),
                        bg='#165DFF', fg='white')
        title.pack(anchor='w')

        version = tk.Label(title_frame, text="NqiTool v1.0",
                          font=('Microsoft YaHei UI', 9),
                          bg='#1a6ce8', fg='white',
                          padx=8, pady=2)
        version.pack(anchor='w', pady=(2, 0))

        # 标题栏右侧 - 状态和授权时间
        self.right_frame = tk.Frame(self.header, bg='#165DFF')
        self.right_frame.pack(side=tk.RIGHT, padx=25, pady=12)

        # 授权过期时间标签
        self.license_label = tk.Label(self.right_frame, text="",
                              font=('Microsoft YaHei UI', 9),
                              bg='#165DFF', fg='#e0e7ff')
        self.license_label.pack(side=tk.LEFT, padx=(0, 15))

        # 状态指示器
        self.status_dot = tk.Label(self.right_frame, text="●", font=('Arial', 14),
                            bg='#165DFF', fg='#a5b4fc')
        self.status_dot.pack(side=tk.LEFT)
        self.status_text = tk.Label(self.right_frame, text="系统就绪",
                              font=('Microsoft YaHei UI', 10),
                              bg='#165DFF', fg='white')
        self.status_text.pack(side=tk.LEFT, padx=(6, 0))

        # 主内容区域
        self.main_container = tk.Frame(self.root, bg='#f9fafb')
        self.main_container.pack(fill=tk.BOTH, expand=True)

        content = tk.Frame(self.main_container, bg='#f9fafb')
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # 第一行：登录配置卡片（单行紧凑）
        self._build_login_card(content)

        # 第二行：查询参数 + 提取参数（左右分布）
        params_row = tk.Frame(content, bg='#f9fafb')
        params_row.pack(fill=tk.X, pady=(0, 10))

        # 左侧：查询参数卡片
        self._build_query_card(params_row)

        # 右侧：提取参数卡片
        self._build_params_card(params_row)

        # 底部：进度和日志
        self._build_bottom_section(content)

        # 更新授权显示
        self._update_license_display()

    def _build_card(self, parent, title=None, **kwargs):
        """创建卡片容器
        Args:
            parent: 父容器
            title: 卡片标题（可选）
            compact: 是否紧凑模式（无标题边框）
        """
        card = tk.Frame(parent, bg='white', bd=0, relief='flat')

        if title:
            header = tk.Frame(card, bg='white')
            header.pack(fill=tk.X, padx=20, pady=(16, 0))

            label = tk.Label(header, text=title,
                            font=('Microsoft YaHei UI', 13, 'bold'),
                            bg='white', fg='#374151', anchor='w')
            label.pack(fill='x')

            separator = tk.Frame(card, bg='#f3f4f6', height=1)
            separator.pack(fill=tk.X, padx=20, pady=(12, 0))

        return card

    def _build_login_card(self, parent):
        """构建登录配置卡片（一行紧凑布局）"""
        card = self._build_card(parent, "🔐 登录配置")
        card.pack(fill=tk.X, pady=(0, 10))

        body = tk.Frame(card, bg='white')
        body.pack(fill=tk.X, padx=16, pady=10)

        # 单行布局：用户名 | 密码 | 登录状态 | 按钮
        row = tk.Frame(body, bg='white')
        row.pack(fill=tk.X)

        # 用户名
        user_frame = tk.Frame(row, bg='white')
        user_frame.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(user_frame, text="用户名", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(anchor='w')
        self.username_entry = tk.Entry(user_frame, font=('Microsoft YaHei UI', 10),
                             relief='flat', bg='#f8f9fa', bd=0, width=15)
        self.username_entry.insert(0, DEFAULT_USERNAME)
        self.username_entry.pack(fill=tk.X, pady=(2, 0), ipady=4)

        # 密码
        pass_frame = tk.Frame(row, bg='white')
        pass_frame.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(pass_frame, text="密码", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(anchor='w')
        self.password_entry = tk.Entry(pass_frame, font=('Microsoft YaHei UI', 10),
                             show="●", relief='flat', bg='#f8f9fa', bd=0, width=15)
        self.password_entry.insert(0, DEFAULT_PASSWORD)
        self.password_entry.pack(fill=tk.X, pady=(2, 0), ipady=4)

        # 登录状态图标和标签
        self.login_status_icon = tk.Label(row, text="○", font=('Arial', 12, 'bold'),
                              bg='white', fg='#80868b')
        self.login_status_icon.pack(side=tk.LEFT, padx=(10, 4), pady=0)

        self.login_status_lbl = tk.Label(row, text="未登录",
                             font=('Microsoft YaHei UI', 10, 'bold'),
                             bg='white', fg='#80868b')
        self.login_status_lbl.pack(side=tk.LEFT, padx=(0, 10), pady=0)

        # 登录按钮
        self.login_btn = tk.Button(row, text="登录",
                             font=('Microsoft YaHei UI', 10, 'bold'),
                             bg='#165DFF', fg='white', bd=1,
                             relief='raised',
                             cursor='arrow', padx=20, pady=6,
                             command=self._on_login)
        self.login_btn.pack(side=tk.LEFT)

    def _build_query_card(self, parent):
        """构建查询参数卡片（紧凑布局）"""
        card = self._build_card(parent, "🔍 查询参数")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        body = tk.Frame(card, bg='white')
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # ========== 数据分类（横向排列）==========
        cat_frame = tk.Frame(body, bg='white')
        cat_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(cat_frame, text="数据分类：", font=('Microsoft YaHei UI', 9, 'bold'),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=(0, 6))

        self.category_vars = {}
        categories = ["干扰", "容量", "工参", "MR覆盖", "语音报表", "小区性能", "全程完好率", "语音小区"]

        for name in categories:
            var = tk.IntVar(value=0)
            self.category_vars[name] = var
            cb = tk.Checkbutton(cat_frame, text=name, variable=var,
                              font=('Microsoft YaHei UI', 9, 'bold'),
                              bg='white', fg='#202124',
                              selectcolor='#165DFF',
                              activebackground='white',
                              activeforeground='#165DFF',
                              cursor='hand2',
                              command=lambda c=name: self._on_category_changed(c))
            cb.pack(side=tk.LEFT, padx=(0, 8))

        # ========== 数据表选择（下拉框）==========
        table_frame = tk.Frame(body, bg='white')
        table_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(table_frame, text="选择数据表：", font=('Microsoft YaHei UI', 9, 'bold'),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=(0, 6))

        self.table_vars = {}
        TABLE_CATEGORIES = {
            '干扰': ['5G干扰小区', '4G干扰小区'],
            '容量': ['5G小区容量报表', '重要场景-天'],
            '工参': ['5G小区工参报表', '4G小区工参报表'],
            'MR覆盖': ['5GMR覆盖-小区天', '4GMR覆盖-小区天'],
            '语音报表': ['VoLTE小区监控预警', 'VONR小区监控预警', 'EPSFB小区监控预警'],
            '小区性能': ['5G小区性能KPI报表', '4G小区性能KPI报表'],
            '全程完好率': ['4G全程完好率报表', '5G全程完好率报表'],
            '语音小区': ['4G语音小区', '5G语音小区'],
        }

        all_tables = []
        for tables in TABLE_CATEGORIES.values():
            all_tables.extend(tables)

        for name in all_tables:
            self.table_vars[name] = tk.IntVar(value=0)

        # 使用下拉框选择数据表
        self.table_dropdown = MultiSelectDropdown(
            table_frame,
            all_tables,
            width=22,
            select_all=False
        )
        self.table_dropdown.pack(pady=(2, 0))

        # 自定义字段选择
        custom_field_frame = tk.Frame(body, bg='white')
        custom_field_frame.pack(fill=tk.X, pady=(0, 8))

        self.custom_fields_var = tk.BooleanVar(value=False)
        custom_field_cb = tk.Checkbutton(custom_field_frame, text="自定义字段",
                                        variable=self.custom_fields_var,
                                        font=('Microsoft YaHei UI', 9, 'bold'),
                                        bg='white', fg='#202124',
                                        selectcolor='#165DFF',
                                        activebackground='white',
                                        activeforeground='#165DFF',
                                        cursor='arrow',
                                        command=self._on_custom_fields_toggle)
        custom_field_cb.pack(side=tk.LEFT, padx=(0, 6))

        self.select_fields_btn = tk.Button(custom_field_frame, text="选择字段",
                                         font=('Microsoft YaHei UI', 8, 'bold'),
                                         bg='#e8eaed', fg='#202124', bd=1,
                                         cursor='arrow', relief='raised',
                                         padx=10, pady=2,
                                         state=tk.DISABLED,
                                         command=self._show_field_selector)
        self.select_fields_btn.pack(side=tk.LEFT)

        # 存储选中的字段
        self.selected_fields = {}
        self.field_configs = {}

    def _build_params_card(self, parent):
        """构建提取参数卡片（紧凑布局，右侧显示）"""
        card = self._build_card(parent, "⚙ 提取参数")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        body = tk.Frame(card, bg='white')
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # 第一行：地市选择 + 快捷日期（水平排列）
        top_row = tk.Frame(body, bg='white')
        top_row.pack(fill=tk.X, pady=(0, 6))

        # 地市选择
        city_frame = tk.Frame(top_row, bg='white')
        city_frame.pack(side=tk.LEFT, padx=(0, 15))
        tk.Label(city_frame, text="地市选择", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(anchor='w')

        self.city_dropdown = MultiSelectDropdown(
            city_frame,
            MultiSelectDropdown.GD_CITIES,
            width=12,
            select_all=False
        )
        self.city_dropdown.pack(pady=(2, 0))
        self.city_dropdown.set_selected(['阳江'])

        # 快捷日期
        quick_frame = tk.Frame(top_row, bg='white')
        quick_frame.pack(side=tk.LEFT, padx=(0, 15))
        tk.Label(quick_frame, text="快捷日期", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(anchor='w')

        quick_inner = tk.Frame(quick_frame, bg='white')
        quick_inner.pack(pady=(2, 0))

        self.quick_date_btns = {}
        for text, days in [("昨天", 1), ("近7天", 7), ("近30天", 30)]:
            btn = tk.Button(quick_inner, text=text, font=('Microsoft YaHei UI', 8, 'bold'),
                           bg='#e8eaed', fg='#202124', bd=1, padx=10, pady=2,
                           cursor='arrow', relief='raised',
                           command=lambda d=days: self.set_quick_date(d))
            btn.pack(side=tk.LEFT, padx=(0, 3))
            self.quick_date_btns[days] = btn

        # 第二行：日期范围（单独一行）
        date_row = tk.Frame(body, bg='white')
        date_row.pack(fill=tk.X, pady=(0, 6))

        # 日期范围
        date_frame = tk.Frame(date_row, bg='white')
        date_frame.pack(side=tk.LEFT, padx=(0, 15))
        tk.Label(date_frame, text="日期范围", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(anchor='w')

        date_inner = tk.Frame(date_frame, bg='white')
        date_inner.pack(pady=(2, 0))

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
                   width=4, state="readonly").pack(side=tk.LEFT)
        tk.Label(start_frame, text="-", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=1)
        ttk.Combobox(start_frame, textvariable=self.start_month_var,
                   values=list(range(1, 13)),
                   width=2, state="readonly").pack(side=tk.LEFT)
        tk.Label(start_frame, text="-", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=1)
        ttk.Combobox(start_frame, textvariable=self.start_day_var,
                   values=list(range(1, 32)),
                   width=2, state="readonly").pack(side=tk.LEFT)

        tk.Label(date_inner, text=" 至 ", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=3)

        end_frame = tk.Frame(date_inner, bg='white')
        end_frame.pack(side=tk.LEFT)

        ttk.Combobox(end_frame, textvariable=self.end_year_var,
                   values=list(range(2020, current_year + 1)),
                   width=4, state="readonly").pack(side=tk.LEFT)
        tk.Label(end_frame, text="-", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=1)
        ttk.Combobox(end_frame, textvariable=self.end_month_var,
                   values=list(range(1, 13)),
                   width=2, state="readonly").pack(side=tk.LEFT)
        tk.Label(end_frame, text="-", font=('Microsoft YaHei UI', 8),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=1)
        ttk.Combobox(end_frame, textvariable=self.end_day_var,
                   values=list(range(1, 32)),
                   width=2, state="readonly").pack(side=tk.LEFT)

        # 第三行：多日模式选项（在日期范围下方，按钮上方）
        mode_row = tk.Frame(body, bg='white')
        mode_row.pack(fill=tk.X, pady=(0, 6))

        mode_frame = tk.Frame(mode_row, bg='white')
        mode_frame.pack(side=tk.LEFT, padx=(0, 0))

        self.multi_day_var = tk.BooleanVar(value=False)
        multi_day_cb = tk.Checkbutton(mode_frame, text="多日模式",
                                      variable=self.multi_day_var,
                                      font=('Microsoft YaHei UI', 8),
                                      bg='white', fg='#202124',
                                      selectcolor='#e8f0fe',
                                      activebackground='white',
                                      command=self._on_multi_day_toggle)
        multi_day_cb.pack(side=tk.LEFT)

        self.multi_day_per_sheet_var = tk.BooleanVar(value=False)
        multi_day_per_sheet_cb = tk.Checkbutton(mode_frame, text="按日分Sheet",
                                               variable=self.multi_day_per_sheet_var,
                                               font=('Microsoft YaHei UI', 8),
                                               bg='white', fg='#202124',
                                               selectcolor='#e8f0fe',
                                               activebackground='white',
                                               state=tk.DISABLED,
                                               command=self._on_multi_day_per_sheet_toggle)
        self.multi_day_per_sheet_cb = multi_day_per_sheet_cb
        multi_day_per_sheet_cb.pack(side=tk.LEFT, padx=(6, 0))

        # 第四行：操作按钮
        btn_row = tk.Frame(body, bg='white')
        btn_row.pack(fill=tk.X, pady=(4, 0))

        self.extract_btn = tk.Button(btn_row, text="▶ 开始提取",
                               font=('Microsoft YaHei UI', 10, 'bold'),
                               bg='#165DFF', fg='white', bd=1,
                               cursor='arrow', relief='raised', padx=22, pady=5,
                               state=tk.DISABLED, command=self._on_query)
        self.extract_btn.pack(side=tk.LEFT)

        self.stop_btn = tk.Button(btn_row, text="⏹ 停止",
                            font=('Microsoft YaHei UI', 9),
                            bg='#dc3545', fg='white', bd=1,
                            cursor='arrow', relief='raised', padx=14, pady=5,
                            state=tk.DISABLED, command=self._on_stop)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(btn_row, text="📁 打开目录",
                 font=('Microsoft YaHei UI', 9),
                 bg='#f0f2f5', fg='#202124', bd=1,
                 cursor='arrow', relief='raised', padx=12, pady=5,
                 command=self.open_output_dir).pack(side=tk.RIGHT)

    def _build_bottom_section(self, parent):
        """构建底部日志区域"""
        # 直接使用 Frame 作为容器，填满所有剩余空间
        bottom = tk.Frame(parent, bg='white')
        bottom.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        progress_area = tk.Frame(bottom, bg='white')
        progress_area.pack(fill=tk.X, padx=16, pady=(10, 6))

        progress_info = tk.Frame(progress_area, bg='white')
        progress_info.pack(fill=tk.X)

        self.progress_lbl_pct = tk.Label(progress_info, text="进度: 0%",
                          font=('Microsoft YaHei UI', 10, 'bold'),
                          bg='white', fg='#165DFF')
        self.progress_lbl_pct.pack(side=tk.LEFT)

        self.progress_lbl_detail = tk.Label(progress_info, text="就绪",
                             font=('Microsoft YaHei UI', 9),
                             bg='white', fg='#5f6368')
        self.progress_lbl_detail.pack(side=tk.RIGHT)

        # 圆角进度条
        self.progress_canvas = tk.Canvas(progress_area, height=8, bg='white', highlightthickness=0)
        self.progress_canvas.pack(fill=tk.X, pady=(6, 0))
        self.progress_bar = self.progress_canvas.create_rectangle(0, 0, 0, 8, fill='#165DFF', outline='')
        self.progress_bg = self.progress_canvas.create_rectangle(0, 0, 1000, 8, fill='#f0f2f5', outline='')

        # 日志输出
        log_area = tk.Frame(bottom, bg='white')
        log_area.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        self.log_text = scrolledtext.ScrolledText(log_area, height=15,
                                                   font=('Consolas', 9),
                                                   state='disabled',
                                                   bg='#f8f9fa',
                                                   relief='flat',
                                                   bd=1)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 添加日志处理器
        handler = LogTextHandler(self.log_text)
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)

    def _update_license_display(self):
        """更新授权时间显示"""
        if self.expiry_time:
            try:
                # 解析过期时间
                display_time = self.expiry_time.strftime("%Y-%m-%d")
                
                # 计算剩余天数
                current_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                days_left = (self.expiry_time - current_dt).days
                
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

    def _bind_events(self):
        """绑定事件"""
        pass

    def _on_category_changed(self, category):
        """数据分类选择事件"""
        self.log(f"选择了数据分类: {category}", "INFO")

    def _on_multi_day_toggle(self):
        """多日模式切换事件"""
        if self.multi_day_var.get():
            self.multi_day_per_sheet_cb.config(state=tk.NORMAL)
        else:
            self.multi_day_per_sheet_var.set(False)
            self.multi_day_per_sheet_cb.config(state=tk.DISABLED)

    def _on_multi_day_per_sheet_toggle(self):
        """按日分Sheet切换事件"""
        pass

    def _on_custom_fields_toggle(self):
        """自定义字段切换事件"""
        if self.custom_fields_var.get():
            self.select_fields_btn.config(state=tk.NORMAL)
        else:
            self.select_fields_btn.config(state=tk.DISABLED)

    def _show_field_selector(self):
        """显示字段选择窗口"""
        selected_tables = self.table_dropdown.get_selected()
        if not selected_tables:
            messagebox.showwarning("警告", "请先选择数据表")
            return

        # 创建字段选择窗口
        field_window = tk.Toplevel(self.root)
        field_window.title("选择导出字段")
        field_window.geometry("600x400")
        field_window.resizable(True, True)

        # 设置窗口在主窗口中间
        self.root.update_idletasks()
        x = (self.root.winfo_width() - 600) // 2 + self.root.winfo_x()
        y = (self.root.winfo_height() - 400) // 2 + self.root.winfo_y()
        field_window.geometry(f"600x400+{x}+{y}")

        # 创建滚动区域
        canvas = tk.Canvas(field_window)
        scrollbar = ttk.Scrollbar(field_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 布局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 字段选择区域
        field_vars = {}
        for table_name in selected_tables:
            # 动态获取字段配置
            if table_name not in self.field_configs and self.jxcx:
                table_config = TableConfig.get_table_config(table_name)
                if table_config:
                    try:
                        self.log(f"正在获取 {table_name} 的字段配置...", "INFO")
                        configs = self.jxcx.get_field_config(
                            table_config['table_key'],
                            table_config['fieldtype'],
                            table_config['api_type']
                        )
                        if configs:
                            self.field_configs[table_name] = configs
                            self.log(f"获取到 {table_name} 的 {len(configs)} 个字段", "SUCCESS")
                        else:
                            self.log(f"获取 {table_name} 的字段配置失败", "ERROR")
                    except Exception as e:
                        self.log(f"获取字段配置异常: {e}", "ERROR")

            # 显示字段选择
            if table_name in self.field_configs:
                configs = self.field_configs[table_name]
                
                # 表格标题
                table_frame = tk.Frame(scrollable_frame, bg='white', bd=1, relief='solid')
                table_frame.pack(fill=tk.X, pady=5, padx=10)
                
                table_title = tk.Label(table_frame, text=table_name, 
                                     font=('Microsoft YaHei UI', 10, 'bold'),
                                     bg='white', fg='#165DFF')
                table_title.pack(anchor='w', padx=5, pady=3)

                # 字段选择
                fields_frame = tk.Frame(scrollable_frame, bg='white')
                fields_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

                # 按行排列，每行4个复选框
                row_frame = None
                for i, config in enumerate(configs):
                    if i % 4 == 0:
                        row_frame = tk.Frame(fields_frame, bg='white')
                        row_frame.pack(fill=tk.X, pady=2)

                    field_name = config.get('columnname_cn', config.get('columnname', ''))
                    field_key = config.get('columnname', '')
                    
                    var = tk.BooleanVar(value=True)  # 默认全选
                    field_vars[(table_name, field_key)] = var

                    cb = tk.Checkbutton(row_frame, text=field_name,
                                       variable=var,
                                       font=('Microsoft YaHei UI', 9),
                                       bg='white', fg='#202124',
                                       selectcolor='#165DFF',
                                       activebackground='white',
                                       activeforeground='#165DFF',
                                       cursor='arrow')
                    cb.pack(side=tk.LEFT, padx=10, pady=1, fill=tk.X, expand=True)

        # 按钮区域
        btn_frame = tk.Frame(field_window, bg='white')
        btn_frame.pack(fill=tk.X, pady=10, padx=10)

        def on_ok():
            # 保存选中的字段
            self.selected_fields = {}
            for (table_name, field_key), var in field_vars.items():
                if var.get():
                    if table_name not in self.selected_fields:
                        self.selected_fields[table_name] = []
                    self.selected_fields[table_name].append(field_key)
            
            # 显示选中的字段数量
            total_fields = sum(len(fields) for fields in self.selected_fields.values())
            self.log(f"已选择 {total_fields} 个字段", "INFO")
            field_window.destroy()

        def on_cancel():
            field_window.destroy()

        ttk.Button(btn_frame, text="确定", command=on_ok, width=10).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel, width=10).pack(side=tk.RIGHT, padx=5)

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

        self.log(f"设置快捷日期: 近{days}天", "INFO")

    def open_output_dir(self):
        """打开输出目录"""
        import webbrowser
        output_dir = os.path.join(os.getcwd(), 'data_output')
        os.makedirs(output_dir, exist_ok=True)
        webbrowser.open(output_dir)

    def _on_login(self):
        """登录按钮点击事件"""
        self.log("开始登录...", "INFO")
        self.status_text.config(text="登录中...")
        self.status_dot.config(fg='#fbbf24')  # 黄色
        thread = threading.Thread(target=self._login_worker)
        thread.daemon = True
        thread.start()

    def _login_worker(self):
        """登录工作线程"""
        try:
            username = self.username_entry.get().strip()
            password = self.password_entry.get().strip()
            login_mgr = LoginManager(username=username, password=password, parent=self.root)
            if login_mgr.login():
                self.session = login_mgr.sess
                self.jxcx = JXCXQuery(self.session)
                self.root.after(0, self._on_login_success)
            else:
                self.root.after(0, lambda: self.log("登录失败", "ERROR"))
                self.root.after(0, lambda: self.status_text.config(text="登录失败"))
                self.root.after(0, lambda: self.status_dot.config(fg='#ef4444'))  # 红色
                self.root.after(0, lambda: self.login_status_icon.config(text="○", fg='#ef4444'))
                self.root.after(0, lambda: self.login_status_lbl.config(text="登录失败", fg='#ef4444'))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"登录异常: {e}", "ERROR"))
            self.root.after(0, lambda: self.status_text.config(text="登录异常"))
            self.root.after(0, lambda: self.status_dot.config(fg='#ef4444'))  # 红色
            self.root.after(0, lambda: self.login_status_icon.config(text="○", fg='#ef4444'))
            self.root.after(0, lambda: self.login_status_lbl.config(text="登录异常", fg='#ef4444'))

    def _on_login_success(self):
        """登录成功回调"""
        self.log("登录成功！", "SUCCESS")
        self.extract_btn.config(state=tk.NORMAL)
        self.login_btn.config(state=tk.DISABLED, text="已登录")
        self.status_text.config(text="已登录")
        self.status_dot.config(fg='#22c55e')  # 绿色
        self.login_status_icon.config(text="●", fg='#22c55e')
        self.login_status_lbl.config(text="已登录", fg='#22c55e')

    def _on_query(self):
        """查询按钮点击事件"""
        if self.is_querying:
            self.log("正在查询中，请稍候...", "WARNING")
            return

        selected_tables = self.table_dropdown.get_selected()
        if not selected_tables:
            messagebox.showwarning("警告", "请选择要查询的数据表")
            return

        # 获取日期范围
        start_date = f"{self.start_year_var.get()}-{self.start_month_var.get():02d}-{self.start_day_var.get():02d}"
        end_date = f"{self.end_year_var.get()}-{self.end_month_var.get():02d}-{self.end_day_var.get():02d}"
        
        # 获取选中的地市
        selected_cities = self.city_dropdown.get_selected()
        city = ",".join(selected_cities) if selected_cities else ""

        self.is_querying = True
        self.extract_btn.config(state=tk.DISABLED, text="查询中...")
        self.stop_btn.config(state=tk.NORMAL)
        self.status_text.config(text="查询中...")
        self.status_dot.config(fg='#fbbf24')  # 黄色

        self.log(f"开始查询: {', '.join(selected_tables)}", "INFO")
        self.log(f"日期范围: {start_date} 至 {end_date}", "INFO")
        if city:
            self.log(f"地市: {city}", "INFO")

        self.query_thread = threading.Thread(target=self._query_worker,
                                            args=(selected_tables, start_date, end_date, city))
        self.query_thread.daemon = True
        self.query_thread.start()

    def _on_stop(self):
        """停止查询"""
        self.log("正在停止查询...", "INFO")
        # 这里可以添加停止逻辑

    def _query_worker(self, table_names, start_date, end_date, city):
        """查询工作线程"""
        try:
            for table_name in table_names:
                self.log(f"正在查询: {table_name}", "INFO")
                table_config = TableConfig.get_table_config(table_name)
                if table_config:
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
                        df = self.jxcx.get_table(payload)
                        if not df.empty:
                            # 应用自定义字段选择
                            if self.custom_fields_var.get() and table_name in self.selected_fields:
                                selected_field_keys = self.selected_fields[table_name]
                                # 过滤出选中的字段
                                available_fields = [col for col in df.columns if col in selected_field_keys]
                                if available_fields:
                                    df = df[available_fields]
                                    self.log(f"应用自定义字段: {len(available_fields)} 个字段", "INFO")
                                else:
                                    self.log(f"没有选中的字段可用", "WARNING")
                                    continue

                            # 导出数据到Excel
                            import os
                            from datetime import datetime
                            from core.export import export_with_format
                            
                            filename = f"{table_name}_{start_date}_{end_date}.xlsx"
                            filepath = export_with_format(df, filename, table_name)
                            if filepath:
                                self.log(f"数据已导出到: {os.path.basename(filepath)}", "SUCCESS")
                            else:
                                self.log(f"导出失败: {table_name}", "ERROR")
                        else:
                            self.log(f"查询结果为空: {table_name}", "WARNING")
                        self.log(f"查询完成: {table_name}", "SUCCESS")

            self.root.after(0, self._on_query_complete)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"查询异常: {e}", "ERROR"))
            self.root.after(0, self._on_query_failed)

    def _on_query_complete(self):
        """查询完成回调"""
        self.is_querying = False
        self.extract_btn.config(state=tk.NORMAL, text="▶ 开始提取")
        self.stop_btn.config(state=tk.DISABLED)
        self.status_text.config(text="查询完成")
        self.status_dot.config(fg='#22c55e')  # 绿色
        self.log("所有查询完成！", "SUCCESS")

    def _on_query_failed(self):
        """查询失败回调"""
        self.is_querying = False
        self.extract_btn.config(state=tk.NORMAL, text="▶ 开始提取")
        self.stop_btn.config(state=tk.DISABLED)
        self.status_text.config(text="查询失败")
        self.status_dot.config(fg='#ef4444')  # 红色

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
