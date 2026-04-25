# -*- coding: utf-8 -*-
"""
GUI组件模块
提供自定义的GUI组件和辅助类
"""

import tkinter as tk
from tkinter import ttk
import logging


class LogTextHandler(logging.Handler):
    """日志处理器 - 将日志输出到Text组件"""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                           datefmt='%Y-%m-%d %H:%M:%S')

    def emit(self, record):
        msg = self.formatter.format(record) + '\n'

        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg)

            color_map = {
                'DEBUG': '#888888',
                'INFO': '#000000',
                'WARNING': '#FFA500',
                'ERROR': '#FF0000',
                'CRITICAL': '#FF0000'
            }

            tag_name = f'tag_{record.levelname}'
            self.text_widget.tag_config(tag_name, foreground=color_map.get(record.levelname, '#000000'))

            last_line_num = self.text_widget.index(tk.END).split('.')[0]
            start_idx = f'{int(last_line_num)-1}.0'
            end_idx = f'{last_line_num}.end'
            self.text_widget.tag_add(tag_name, start_idx, end_idx)

            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')

        try:
            self.text_widget.after(0, append)
        except Exception:
            pass


class ScrolledTextFrame(ttk.Frame):
    """带滚动条的文本框组件"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent)

        self.text_widget = tk.Text(self, **kwargs)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self, command=self.text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.config(yscrollcommand=scrollbar.set)

        self._setup_tags()

    def _setup_tags(self):
        """设置文本标签样式"""
        self.text_widget.tag_configure('INFO', foreground='#000000')
        self.text_widget.tag_configure('WARNING', foreground='#FFA500')
        self.text_widget.tag_configure('ERROR', foreground='#FF0000')
        self.text_widget.tag_configure('SUCCESS', foreground='#00AA00')

    def append(self, message, tag=None):
        """添加文本"""
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, message + '\n', tag)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

    def clear(self):
        """清空文本"""
        self.text_widget.configure(state='normal')
        self.text_widget.delete('1.0', tk.END)
        self.text_widget.configure(state='disabled')


class DateEntry(ttk.Entry):
    """日期输入组件"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.bind('<FocusIn>', self._on_focus_in)
        self.bind('<KeyRelease>', self._on_key_release)

        self._placeholder = 'YYYY-MM-DD'
        self._show_placeholder()

    def _show_placeholder(self):
        """显示占位符"""
        self.delete('0', tk.END)
        self.insert('0', self._placeholder)
        self.config(foreground='gray')

    def _hide_placeholder(self):
        """隐藏占位符"""
        if self.get() == self._placeholder:
            self.delete('0', tk.END)
            self.config(foreground='black')

    def _on_focus_in(self, event):
        """获取焦点时清除占位符"""
        self._hide_placeholder()

    def _on_key_release(self, event):
        """按键释放时检查是否为空"""
        if not self.get():
            self._show_placeholder()

    def get_date(self):
        """获取日期字符串"""
        value = self.get()
        if value == self._placeholder:
            return None
        return value


class TableConfig:
    """数据表配置类"""

    TABLE_CONFIGS = {
        '4G干扰小区': {
            'name': '4G干扰小区',
            'table_key': '4G干扰小区',
            'fieldtype': 'grid',
            'api_type': 'search',
            'default_conditions': [
                {'field': 'city', 'operator': 'like', 'value': '%%'},
            ]
        },
        '5G干扰小区': {
            'name': '5G干扰小区',
            'table_key': '5G干扰小区',
            'fieldtype': 'grid',
            'api_type': 'search',
            'default_conditions': [
                {'field': 'city', 'operator': 'like', 'value': '%%'},
            ]
        },
        '5G小区容量报表': {
            'name': '5G小区容量报表',
            'table_key': '5G小区容量报表',
            'fieldtype': 'grid',
            'api_type': 'table',
            'default_conditions': []
        },
    }

    @classmethod
    def get_table_names(cls):
        """获取所有数据表名称"""
        return list(cls.TABLE_CONFIGS.keys())

    @classmethod
    def get_table_config(cls, table_name):
        """获取指定数据表的配置"""
        return cls.TABLE_CONFIGS.get(table_name)

    @classmethod
    def get_all_configs(cls):
        """获取所有数据表配置"""
        return cls.TABLE_CONFIGS
