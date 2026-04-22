# -*- coding: utf-8 -*-
"""
通用数据提取工具 - PyQt6版本
按照网页demo风格设计现代化界面
"""
import sys
import os

# 检查 PyQt6
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QCheckBox, QLineEdit, QComboBox,
        QTextEdit, QProgressBar, QFrame, QGridLayout, QScrollArea,
        QSizePolicy
    )
    from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer
    from PyQt6.QtGui import QFont, QIcon, QPalette, QColor
    USE_PYQT6 = True
except ImportError as e:
    USE_PYQT6 = False
    print(f"PyQt6 导入失败: {e}")
    print("请运行: pip install PyQt6")

# ==================== 配置 ====================

def load_config():
    config = {
        'auth': {'username': 'XXXXX', 'password': 'XXXX'},
        'paths': {'output_dir': './data_output', 'cookie_dir': './cookies'},
        'server': {'base_url': 'https://nqi.gmcc.net:20443'}
    }
    config_file = 'config.yaml'
    if os.path.exists(config_file):
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config.update(yaml.safe_load(f) or {})
        except:
            pass
    return config

_config = load_config()
DEFAULT_USERNAME = _config['auth']['username']
DEFAULT_PASSWORD = _config['auth']['password']
OUTPUT_DIR = _config['paths']['output_dir']

# ==================== 样式 ====================

MAIN_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f9fafb;
    font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
}

#header {
    background-color: #165DFF;
    min-height: 60px;
}

.card {
    background-color: white;
    border-radius: 12px;
    border: 1px solid #f3f4f6;
}

.inner-frame {
    background-color: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
}

QLineEdit, QComboBox {
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #374151;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #165DFF;
    background-color: white;
}

QComboBox {
    padding-right: 30px;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #9ca3af;
    margin-right: 10px;
}

QCheckBox {
    spacing: 8px;
    font-size: 14px;
    color: #374151;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #d1d5db;
    background-color: white;
}

QCheckBox::indicator:checked {
    background-color: #165DFF;
    border-color: #165DFF;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiI+PHBhdGggZD0iTTEyLjIwNyA0Ljc5M2ExIDEgMCAwMTEtMS40MTQgMS40MTRsLTUgNWwtMi0yYTEgMSAwIDAxMS40MTQtMS40MTRMNi41IDEwLjkwODYgMTIuMjA3IDQuNzkzem0tNSA1Ljc1M2ExIDEgMCAwMS0xLjQxNCAxLjQxNEw2LjUgMTEuMjAMyA0LjU1IDkuMjYzbC0yLTJhMSAxIDAgMDEtMS40MTQgMS40MTRMNyA5LjQ1ODIgMTIuMjA3IDQuNzkzeiIvPjwvc3ZnPg==);
}

QCheckBox::indicator:hover {
    border-color: #165DFF;
}

.btn-primary {
    background-color: #165DFF;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 500;
}

.btn-primary:hover {
    background-color: #0d47e1;
}

.btn-primary:disabled {
    background-color: #93c5fd;
}

.btn-secondary {
    background-color: #f3f4f6;
    color: #374151;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}

.btn-secondary:hover {
    background-color: #e5e7eb;
}

.date-btn {
    background-color: #f3f4f6;
    color: #374151;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}

.date-btn:hover {
    background-color: #e5e7eb;
}

.date-btn:checked {
    background-color: #165DFF;
    color: white;
}

QProgressBar {
    background-color: #f3f4f6;
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #165DFF;
    border-radius: 6px;
}

#logText {
    background-color: #111827;
    color: #4ade80;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    border: none;
    border-radius: 8px;
    padding: 12px;
}

#footer {
    background-color: #f3f4f6;
}
"""


# ==================== 主窗口 ====================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("通用数据提取工具 v2.0")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self.is_logged_in = False
        self.create_widgets()
        
    def create_widgets(self):
        # 顶部导航栏
        self.header = QFrame()
        self.header.setObjectName("header")
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 12, 20, 12)
        
        # Logo 区域
        left_area = QWidget()
        left_layout = QHBoxLayout(left_area)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        self.icon_label = QLabel("📊")
        self.icon_label.setStyleSheet("""
            background-color: rgba(255,255,255,0.2);
            border-radius: 18px;
            min-width: 36px;
            max-width: 36px;
            min-height: 36px;
            max-height: 36px;
            font-size: 18px;
        """)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.icon_label)
        
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        
        self.title_label = QLabel("通用数据提取工具")
        self.title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        title_layout.addWidget(self.title_label)
        
        self.version_label = QLabel("v2.0")
        self.version_label.setStyleSheet("""
            background-color: rgba(255,255,255,0.2);
            color: white;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
        """)
        title_layout.addWidget(self.version_label)
        left_layout.addWidget(title_widget)
        header_layout.addWidget(left_area)
        
        header_layout.addStretch()
        
        # 右侧区域
        right_area = QWidget()
        right_layout = QHBoxLayout(right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        
        self.license_label = QLabel("🔑 授权到期: 2027-04-21")
        self.license_label.setStyleSheet("color: #c7d2fe; font-size: 12px; background: transparent;")
        right_layout.addWidget(self.license_label)
        
        self.unlock_btn = QPushButton("🔓 系统解锁")
        self.unlock_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.1);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.2);
            }
        """)
        right_layout.addWidget(self.unlock_btn)
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #a5b4fc; font-size: 14px; background: transparent;")
        right_layout.addWidget(self.status_indicator)
        
        self.status_text = QLabel("系统就绪")
        self.status_text.setStyleSheet("color: white; font-size: 13px; background: transparent;")
        right_layout.addWidget(self.status_text)
        
        header_layout.addWidget(right_area)
        
        # 主内容区域
        self.main_widget = QWidget()
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # 查询参数卡片
        self.query_card = self.create_card("🔍 查询参数")
        main_layout.addWidget(self.query_card)
        
        # 配置卡片
        config_widget = QWidget()
        config_layout = QHBoxLayout(config_widget)
        config_layout.setSpacing(16)
        
        self.login_card = self.create_card("🔐 登录配置")
        self.login_card.setFixedWidth(380)
        config_layout.addWidget(self.login_card)
        
        self.params_card = self.create_card("⚙ 提取参数")
        config_layout.addWidget(self.params_card)
        
        main_layout.addWidget(config_widget)
        
        # 进度卡片
        self.progress_card = self.create_card("")
        progress_layout = self.progress_card.layout()
        progress_layout.setContentsMargins(20, 12, 20, 12)
        
        progress_info = QHBoxLayout()
        self.progress_label = QLabel("进度: <span style='font-weight: bold;'>0%</span>")
        self.progress_label.setStyleSheet("color: #374151; font-size: 13px;")
        progress_info.addWidget(self.progress_label)
        
        self.progress_status = QLabel("就绪")
        self.progress_status.setStyleSheet("color: #6b7280; font-size: 12px;")
        progress_info.addWidget(self.progress_status, 1, Qt.AlignmentFlag.AlignRight)
        
        progress_layout.addLayout(progress_info)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(self.progress_card)
        
        # 日志卡片
        self.log_card = self.create_card("📋 运行日志")
        main_layout.addWidget(self.log_card)
        
        # 日志文本
        self.log_widget = QFrame()
        self.log_widget.setObjectName("logText")
        self.log_layout = QVBoxLayout(self.log_widget)
        self.log_layout.setContentsMargins(16, 12, 16, 12)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            background-color: transparent;
            color: #4ade80;
            border: none;
        """)
        self.log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(self.log_widget)
        
        # 底部
        self.footer = QFrame()
        self.footer.setObjectName("footer")
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(20, 8, 20, 8)
        
        self.footer_status = QLabel(f"📁 数据输出目录: {os.path.abspath(OUTPUT_DIR)}/")
        self.footer_status.setStyleSheet("color: #374151; font-size: 12px;")
        footer_layout.addWidget(self.footer_status)
        
        footer_right = QLabel("v2.0.1 | © 2026")
        footer_right.setStyleSheet("color: #9ca3af; font-size: 11px;")
        footer_layout.addWidget(footer_right, 1, Qt.AlignmentFlag.AlignRight)
        
        main_layout.addWidget(self.footer)
        
        # 填充卡片内容
        self.fill_query_card()
        self.fill_login_card()
        self.fill_params_card()
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidget(self.main_widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #f9fafb;")
        
        self.setCentralWidget(scroll)
        
    def create_card(self, title=""):
        card = QFrame()
        card.setObjectName("card")
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if title:
            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(20, 16, 20, 0)
            
            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            
            # 清除按钮（仅日志卡片）
            if "日志" in title:
                clear_btn = QPushButton("清空")
                clear_btn.setFixedWidth(50)
                clear_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f3f4f6;
                        color: #374151;
                        border: none;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #e5e7eb;
                    }
                """)
                clear_btn.clicked.connect(self.clear_log)
                header_layout.addWidget(clear_btn)
            
            layout.addWidget(header)
            
            separator = QFrame()
            separator.setStyleSheet("background-color: #f3f4f6; max-height: 1px; margin: 12px 20px;")
            separator.setFrameShape(QFrame.Shape.HLine)
            layout.addWidget(separator)
        
        return card
    
    def fill_query_card(self):
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(20, 0, 20, 16)
        content_layout.setSpacing(16)
        
        # 数据分类
        cat_frame = QFrame()
        cat_frame.setObjectName("inner-frame")
        cat_frame.setStyleSheet("""
            QFrame#inner-frame {
                background-color: #f9fafb;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
        """)
        cat_layout = QVBoxLayout(cat_frame)
        cat_layout.setContentsMargins(14, 10, 14, 10)
        
        cat_title = QLabel("数据分类")
        cat_title.setStyleSheet("font-size: 12px; font-weight: 500; color: #374151; background: transparent;")
        cat_layout.addWidget(cat_title)
        
        self.category_checks = {}
        for name in ["干扰", "容量", "工参", "语音报表", "小区性能"]:
            cb = QCheckBox(name)
            cb.setStyleSheet("""
                QCheckBox {
                    spacing: 8px;
                    font-size: 14px;
                    color: #374151;
                    background: transparent;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 2px solid #d1d5db;
                    background-color: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #165DFF;
                    border-color: #165DFF;
                }
            """)
            cat_layout.addWidget(cb)
            self.category_checks[name] = cb
        
        cat_layout.addStretch()
        content_layout.addWidget(cat_frame, 1)
        
        # 数据表选择
        table_frame = QFrame()
        table_frame.setObjectName("inner-frame")
        table_frame.setStyleSheet(cat_frame.styleSheet())
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(14, 10, 14, 10)
        
        table_title = QLabel("选择数据表")
        table_title.setStyleSheet("font-size: 12px; font-weight: 500; color: #374151; background: transparent;")
        table_layout.addWidget(table_title)
        
        self.table_checks = {}
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
        
        grid = QGridLayout()
        grid.setSpacing(8)
        
        for i, name in enumerate(all_tables):
            row, col = i // 3, i % 3
            cb = QCheckBox(name)
            cb.setStyleSheet("""
                QCheckBox {
                    spacing: 8px;
                    font-size: 14px;
                    color: #374151;
                    background: transparent;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 2px solid #d1d5db;
                    background-color: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #165DFF;
                    border-color: #165DFF;
                }
            """)
            if i < 2:
                cb.setChecked(True)
            grid.addWidget(cb, row, col)
            self.table_checks[name] = cb
        
        table_layout.addLayout(grid)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #d1d5db;
            }
        """)
        select_all_btn.clicked.connect(self.select_all_tables)
        btn_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("取消")
        clear_btn.setStyleSheet(select_all_btn.styleSheet())
        clear_btn.clicked.connect(self.clear_all_tables)
        btn_layout.addWidget(clear_btn)
        
        table_layout.addLayout(btn_layout)
        content_layout.addWidget(table_frame, 2)
        
        self.query_card.layout().addWidget(content)
    
    def fill_login_card(self):
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 0, 20, 16)
        content_layout.setSpacing(12)
        
        # 用户名/密码行
        user_layout = QHBoxLayout()
        user_layout.setSpacing(10)
        
        user_widget = QWidget()
        user_inner = QVBoxLayout(user_widget)
        user_inner.setContentsMargins(0, 0, 0, 0)
        user_inner.setSpacing(4)
        
        user_label = QLabel("用户名")
        user_label.setStyleSheet("font-size: 11px; font-weight: 500; color: #374151; background: transparent;")
        user_inner.addWidget(user_label)
        
        self.username_input = QLineEdit()
        self.username_input.setText(DEFAULT_USERNAME)
        user_inner.addWidget(self.username_input)
        user_layout.addWidget(user_widget)
        
        pass_widget = QWidget()
        pass_inner = QVBoxLayout(pass_widget)
        pass_inner.setContentsMargins(0, 0, 0, 0)
        pass_inner.setSpacing(4)
        
        pass_label = QLabel("密码")
        pass_label.setStyleSheet("font-size: 11px; font-weight: 500; color: #374151; background: transparent;")
        pass_inner.addWidget(pass_label)
        
        self.password_input = QLineEdit()
        self.password_input.setText(DEFAULT_PASSWORD)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        pass_inner.addWidget(self.password_input)
        user_layout.addWidget(pass_widget)
        
        content_layout.addLayout(user_layout)
        
        # 状态栏
        status_bar = QWidget()
        status_bar.setStyleSheet("""
            background-color: #f3f4f6;
            border-radius: 8px;
            padding: 8px 12px;
        """)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_indicator = QLabel("🔴")
        self.status_indicator.setStyleSheet("font-size: 10px;")
        status_layout.addWidget(self.status_indicator)
        
        self.login_status_label = QLabel("未登录")
        self.login_status_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        status_layout.addWidget(self.login_status_label)
        status_layout.addStretch()
        
        self.login_btn = QPushButton("登录")
        status_layout.addWidget(self.login_btn)
        
        content_layout.addWidget(status_bar)
        self.login_card.layout().addWidget(content)
    
    def fill_params_card(self):
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 0, 20, 16)
        content_layout.setSpacing(16)
        
        # 第一行
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        
        # 地市
        city_widget = QWidget()
        city_layout = QVBoxLayout(city_widget)
        city_layout.setContentsMargins(0, 0, 0, 0)
        city_layout.setSpacing(4)
        
        city_label = QLabel("地市选择")
        city_label.setStyleSheet("font-size: 11px; font-weight: 500; color: #6b7280;")
        city_layout.addWidget(city_label)
        
        self.city_combo = QComboBox()
        self.city_combo.addItems(["阳江", "广州", "深圳", "佛山", "东莞", "惠州", "中山", "珠海", "江门", "肇庆", "云浮", "韶关", "梅州", "河源", "清远"])
        city_layout.addWidget(self.city_combo)
        row1.addWidget(city_widget)
        
        # 快捷日期
        date_widget = QWidget()
        date_layout = QVBoxLayout(date_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(4)
        
        date_label = QLabel("快捷日期")
        date_label.setStyleSheet(city_label.styleSheet())
        date_layout.addWidget(date_label)
        
        date_btns = QHBoxLayout()
        date_btns.setSpacing(6)
        
        self.date_buttons = {}
        for text, days in [("昨天", 1), ("近7天", 7), ("近30天", 30)]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setChecked(days == 30)
            btn.clicked.connect(lambda checked, d=days: self.on_date_btn_clicked(d))
            date_btns.addWidget(btn)
            self.date_buttons[days] = btn
        
        date_layout.addLayout(date_btns)
        row1.addWidget(date_widget)
        row1.addStretch()
        content_layout.addLayout(row1)
        
        # 第二行
        row2 = QHBoxLayout()
        row2.setSpacing(20)
        
        # 日期范围
        range_widget = QWidget()
        range_layout = QVBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(4)
        
        range_label = QLabel("日期范围")
        range_label.setStyleSheet(city_label.styleSheet())
        range_layout.addWidget(range_label)
        
        range_btns = QHBoxLayout()
        range_btns.setSpacing(6)
        
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)
        
        self.start_year = QComboBox()
        self.start_year.addItems([str(y) for y in range(2020, 2030)])
        self.start_year.setCurrentText(str(yesterday.year))
        self.start_year.setFixedWidth(80)
        
        self.start_month = QComboBox()
        self.start_month.addItems([f"{m:02d}" for m in range(1, 13)])
        self.start_month.setCurrentText(f"{yesterday.month:02d}")
        self.start_month.setFixedWidth(60)
        
        self.start_day = QComboBox()
        self.start_day.addItems([f"{d:02d}" for d in range(1, 32)])
        self.start_day.setCurrentText(f"{yesterday.day:02d}")
        self.start_day.setFixedWidth(60)
        
        range_btns.addWidget(self.start_year)
        range_btns.addWidget(QLabel("-"))
        range_btns.addWidget(self.start_month)
        range_btns.addWidget(QLabel("-"))
        range_btns.addWidget(self.start_day)
        range_btns.addWidget(QLabel("  至  "))
        
        self.end_year = QComboBox()
        self.end_year.addItems([str(y) for y in range(2020, 2030)])
        self.end_year.setCurrentText(str(yesterday.year))
        self.end_year.setFixedWidth(80)
        
        self.end_month = QComboBox()
        self.end_month.addItems([f"{m:02d}" for m in range(1, 13)])
        self.end_month.setCurrentText(f"{yesterday.month:02d}")
        self.end_month.setFixedWidth(60)
        
        self.end_day = QComboBox()
        self.end_day.addItems([f"{d:02d}" for d in range(1, 32)])
        self.end_day.setCurrentText(f"{yesterday.day:02d}")
        self.end_day.setFixedWidth(60)
        
        range_btns.addWidget(self.end_year)
        range_btns.addWidget(QLabel("-"))
        range_btns.addWidget(self.end_month)
        range_btns.addWidget(QLabel("-"))
        range_btns.addWidget(self.end_day)
        
        range_layout.addLayout(range_btns)
        row2.addWidget(range_widget)
        
        # 多模式
        self.multi_mode_check = QCheckBox("多模式（单日循环提取）")
        self.multi_mode_check.setChecked(True)
        row2.addWidget(self.multi_mode_check)
        
        # 打开目录
        open_btn = QPushButton("📁 打开目录")
        row2.addWidget(open_btn)
        row2.addStretch()
        content_layout.addLayout(row2)
        
        # 第三行：按钮
        row3 = QHBoxLayout()
        row3.setSpacing(12)
        
        self.extract_btn = QPushButton("▶ 开始提取")
        self.extract_btn.setEnabled(False)
        row3.addWidget(self.extract_btn)
        
        self.stop_btn = QPushButton("⏹ 停止")
        row3.addWidget(self.stop_btn)
        row3.addStretch()
        content_layout.addLayout(row3)
        
        self.params_card.layout().addWidget(content)
    
    def on_date_btn_clicked(self, days):
        for d, btn in self.date_buttons.items():
            btn.setChecked(d == days)
        
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)
        start_date = yesterday - timedelta(days=days - 1)
        
        self.start_year.setCurrentText(str(start_date.year))
        self.start_month.setCurrentText(f"{start_date.month:02d}")
        self.start_day.setCurrentText(f"{start_date.day:02d}")
        
        self.end_year.setCurrentText(str(yesterday.year))
        self.end_month.setCurrentText(f"{yesterday.month:02d}")
        self.end_day.setCurrentText(f"{yesterday.day:02d}")
    
    def select_all_tables(self):
        for cb in self.table_checks.values():
            cb.setChecked(True)
    
    def clear_all_tables(self):
        for cb in self.table_checks.values():
            cb.setChecked(False)
    
    def clear_log(self):
        self.log_text.clear()
    
    def log(self, message):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"<span style='color: #9ca3af;'>[{timestamp}]</span> {message}")
    
    def update_progress(self, value, status=""):
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"进度: <span style='font-weight: bold;'>{value}%</span>")
        if status:
            self.progress_status.setText(status)
    
    def set_login_status(self, logged_in):
        self.is_logged_in = logged_in
        if logged_in:
            self.status_indicator.setText("🟢")
            self.login_status_label.setText("已登录")
            self.login_status_label.setStyleSheet("font-size: 12px; color: #16a34a;")
            self.extract_btn.setEnabled(True)
        else:
            self.status_indicator.setText("🔴")
            self.login_status_label.setText("未登录")
            self.login_status_label.setStyleSheet("font-size: 12px; color: #6b7280;")
            self.extract_btn.setEnabled(False)


# ==================== 主程序 ====================

def main():
    if not USE_PYQT6:
        print("需要安装 PyQt6 才能运行 GUI")
        print("请运行: pip install PyQt6")
        return
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    window.log("通用数据提取工具已就绪")
    window.log("支持的数据表: 5G干扰小区, 4G干扰小区, 5G小区容量报表, 重要场景-天, 5G小区工参报表, 4G小区工参报表, VoLTE小区监控预警, VONR小区监控预警, EPSFB小区监控预警, 5G小区性能KPI报表, 4G小区性能KPI报表")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
