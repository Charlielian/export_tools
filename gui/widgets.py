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
        
        # 记录选择顺序（解决显示顺序问题）
        self._selected_order = []
        
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
                command=lambda v=val: self._on_check_change(v)
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
        """显示下拉框（自适应屏幕空间）"""
        self.dropdown.update_idletasks()

        # 获取 Entry 的位置和尺寸
        entry_x = self.entry.winfo_rootx()
        entry_y = self.entry.winfo_rooty()
        entry_h = self.entry.winfo_height()

        # 获取下拉框的所需尺寸
        dropdown_w = self.dropdown.winfo_reqwidth()
        dropdown_h = self.dropdown.winfo_reqheight()

        # 获取屏幕工作区域尺寸（排除任务栏等）
        screen_w = self.dropdown.winfo_screenwidth()
        screen_h = self.dropdown.winfo_screenheight()

        # 计算下方和上方可用的空间
        space_below = screen_h - (entry_y + entry_h)
        space_above = entry_y

        # 判断应该显示在上方还是下方
        # 优先显示在下方，如果下方空间不够但上方够用，则显示在上方
        if space_below >= dropdown_h or space_below >= space_above:
            # 显示在下方
            y = entry_y + entry_h
        else:
            # 显示在上方
            y = entry_y - dropdown_h

        # 确保不会超出屏幕左右边界
        if entry_x + dropdown_w > screen_w:
            x = screen_w - dropdown_w
        else:
            x = entry_x

        # 确保不会超出屏幕上边界
        if y < 0:
            y = 0

        self.dropdown.geometry(f"{dropdown_w}x{dropdown_h}+{x}+{y}")
        self.dropdown.deiconify()
        self.dropdown.lift()
    
    def _on_check_change(self, val=None):
        """复选框状态变化 - 记录选择顺序"""
        if val is not None:
            var = self.check_vars.get(val)
            if var:
                if var.get():
                    # 选中：添加到顺序列表（避免重复）
                    if val not in self._selected_order:
                        self._selected_order.append(val)
                else:
                    # 取消选中：从顺序列表移除
                    if val in self._selected_order:
                        self._selected_order.remove(val)
    
    def _select_all(self):
        """全选"""
        self._selected_order = list(self.values)  # 按values顺序记录
        for var in self.check_vars.values():
            var.set(True)
    
    def _deselect_all(self):
        """取消全选"""
        self._selected_order = []
        for var in self.check_vars.values():
            var.set(False)
    
    def _confirm(self):
        """确认选择"""
        # 使用记录的选择顺序返回，而不是字典遍历顺序
        selected = [val for val in self._selected_order if val in self.check_vars and self.check_vars[val].get()]
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
        # 先清空选择顺序
        self._selected_order = []
        for val, var in self.check_vars.items():
            var.set(val in values)
            if val in values:
                self._selected_order.append(val)
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


class TableConfig:
    """数据表配置类"""

    # 5G干扰小区字段配置
    INTERFERENCE_5G_FIELDS = [
        {'feild': 'starttime', 'feildName': '数据时间', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'endtime', 'feildName': '结束时间', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'cgi', 'feildName': 'CGI', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'cell_name', 'feildName': '小区名', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'freq', 'feildName': '频段', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'micro_grid', 'feildName': '微网格标识', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'averagevalue', 'feildName': '全频段均值', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'averagevalued1', 'feildName': 'D1均值', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'averagevalued2', 'feildName': 'D2均值', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'is_interfere_5g', 'feildName': '是否干扰小区', 'datatype': 'character varying', 'columntype': '1'},
    ]

    # 4G干扰小区字段配置
    INTERFERENCE_4G_FIELDS = [
        {'feild': 'starttime', 'feildName': '数据时间', 'datatype': '1', 'columntype': '1'},
        {'feild': 'endtime', 'feildName': '结束时间', 'datatype': '1', 'columntype': '1'},
        {'feild': 'cgi', 'feildName': 'CGI', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'cell_name', 'feildName': '小区名', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'freq', 'feildName': '频段', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'micro_grid', 'feildName': '微网格标识', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'bandwidth', 'feildName': '系统带宽', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'averagevalue', 'feildName': '平均干扰电平', 'datatype': 'character varying', 'columntype': '1'},
        {'feild': 'is_interfere', 'feildName': '是否干扰小区', 'datatype': 'character varying', 'columntype': '1'},
    ]

    TABLE_CONFIGS = {
        # ========== 干扰类 ==========
        '5G干扰小区': {
            'name': '5G干扰小区',
            'table_key': '5G干扰报表（忙时）',
            'table_name': 'appdbv3.a_interfere_nr_cell_zb2_d',
            'fieldtype': '5G干扰报表（忙时）',
            'api_type': 'search',
            'default_conditions': [
                {'field': 'city', 'operator': 'like', 'value': '%%'},
            ],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'gnodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            },
            'fields': INTERFERENCE_5G_FIELDS,
        },
        '4G干扰小区': {
            'name': '4G干扰小区',
            'table_key': '4G干扰报表（忙时）',
            'table_name': 'appdbv3.a_interfere_lte_cell_zb2_d',
            'fieldtype': '4G干扰报表（忙时）',
            'api_type': 'search',
            'default_conditions': [
                {'field': 'city', 'operator': 'like', 'value': '%%'},
            ],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            },
            'fields': INTERFERENCE_4G_FIELDS,
        },

        # ========== 容量类 ==========
        '5G小区容量报表': {
            'name': '5G小区容量报表',
            'table_key': '5G小区容量报表 - 天粒度',
            'table_name': 'appdbv3.a_adhoc_capacity_nr_nrcell_d',
            'fieldtype': '5G小区容量报表 - 天粒度',
            'api_type': 'table',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'ncgi',
                'timeField': 'starttime',
                'cellField': 'nrcell',
                'cityField': 'city',
            }
        },
        '重要场景-天': {
            'name': '重要场景-天',
            'table_key': '重要场景-小区天',
            'table_name': 'appdbv3.a_overview_ispm_lte_cell_d',
            'fieldtype': '重要场景-小区天',
            'api_type': 'table',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },

        # ========== 工参类 ==========
        '5G小区工参报表': {
            'name': '5G小区工参报表',
            'table_key': 'appdbv3.a_common_cfg_nr_cellant_d',
            'table_name': 'appdbv3.a_common_cfg_nr_cellant_d',
            'fieldtype': '5G小区工参',
            'api_type': 'table',
            'is_gongcan': True,
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区，网格，地市，分公司',
                'timedimension': '天粒度',
                'enodebField': 'gnodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },
        '4G小区工参报表': {
            'name': '4G小区工参报表',
            'table_key': 'appdbv3.v_a_common_cfg_lte_cellant_d',
            'table_name': 'appdbv3.v_a_common_cfg_lte_cellant_d',
            'fieldtype': '4G小区工参',
            'api_type': 'table',
            'is_gongcan': True,
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区，网格，地市，分公司',
                'timedimension': '天粒度',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },

        # ========== MR覆盖类 ==========
        '5GMR覆盖-小区天': {
            'name': '5GMR覆盖-小区天',
            'table_key': 'appdbv3.a_common_mro_scssrsrp_nr_nrcell',
            'table_name': 'appdbv3.a_common_mro_scssrsrp_nr_nrcell',
            'fieldtype': '应用_5GMRO_RSRP基础性能_小区',
            'api_type': 'table',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'gnodeb_id',
                'cgiField': 'ncgi',
                'timeField': 'starttime',
                'cellField': 'nrcell',
                'cityField': 'city',
            }
        },
        '4GMR覆盖-小区天': {
            'name': '4GMR覆盖-小区天',
            'table_key': 'appdbv3.a_common_mro_rsrp_lte_cell',
            'table_name': 'appdbv3.a_common_mro_rsrp_lte_cell',
            'fieldtype': '应用_4GMRO_RSRP基础性能_小区',
            'api_type': 'table',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },

        # ========== 语音报表类 ==========
        'VoLTE小区监控预警': {
            'name': 'VoLTE小区监控预警',
            'table_key': 'volte小区监控预警',
            'table_name': '',
            'fieldtype': 'VoLTE小区监控预警数据表-天',
            'api_type': 'search',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },
        'VONR小区监控预警': {
            'name': 'VONR小区监控预警',
            'table_key': 'vonr',
            'table_name': '',
            'fieldtype': 'VONR小区监控预警数据表-天',
            'api_type': 'search',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'gnodeb_id',
                'cgiField': 'ncgi',
                'timeField': 'starttime',
                'cellField': 'nrcell',
                'cityField': 'city',
            }
        },
        'EPSFB小区监控预警': {
            'name': 'EPSFB小区监控预警',
            'table_key': 'EPSFB',
            'table_name': '',
            'fieldtype': 'EPSFB小区监控预警数据表-天',
            'api_type': 'search',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },

        # ========== 小区性能类 ==========
        '5G小区性能KPI报表': {
            'name': '5G小区性能KPI报表',
            'table_key': 'appdbv3.a_common_pm_sacu',
            'table_name': 'appdbv3.a_common_pm_sacu',
            'fieldtype': 'SA_CU性能',
            'api_type': 'table',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'gnodeb_id',
                'cgiField': 'ncgi',
                'timeField': 'starttime',
                'cellField': 'nrcell',
                'cityField': 'city',
            }
        },
        '4G小区性能KPI报表': {
            'name': '4G小区性能KPI报表',
            'table_key': 'appdbv3.a_common_pm_lte',
            'table_name': 'appdbv3.a_common_pm_lte',
            'fieldtype': '公共信息（小区级粒度）',
            'api_type': 'table',
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },

        # ========== 全程完好率类 ==========
        '4G全程完好率报表': {
            'name': '4G全程完好率报表',
            'table_key': 'appdbv3.a_common_pm_lte',
            'table_name': 'appdbv3.a_common_pm_lte',
            'fieldtype': '公共信息（小区级粒度）',
            'api_type': 'table',
            'calc_columns': ['4G全程完好率', '4G是否差小区'],
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },
        '5G全程完好率报表': {
            'name': '5G全程完好率报表',
            'table_key': 'appdbv3.a_common_pm_sacu',
            'table_name': 'appdbv3.a_common_pm_sacu',
            'fieldtype': 'SA_CU性能',
            'api_type': 'table',
            'calc_columns': ['5G全程完好率', '5G是否差小区'],
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'gnodeb_id',
                'cgiField': 'ncgi',
                'timeField': 'starttime',
                'cellField': 'nrcell',
                'cityField': 'city',
            }
        },

        # ========== 语音小区类 ==========
        '4G语音小区': {
            'name': '4G语音小区',
            'table_key': 'volte小区监控预警',  # 实际会分别查询VoLTE和EPSFB
            'fieldtype': 'VoLTE小区监控预警数据表-天',
            'api_type': 'search',
            'is_4g_voice': True,  # 标记为4G语音小区，需要VoLTE+EPSFB合并
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'enodeb_id',
                'cgiField': 'cgi',
                'timeField': 'starttime',
                'cellField': 'cell',
                'cityField': 'city',
            }
        },
        '5G语音小区': {
            'name': '5G语音小区',
            'table_key': 'vonr',
            'table_name': '',
            'fieldtype': 'VONR小区监控预警数据表-天',
            'api_type': 'search',
            'calc_columns': ['5G语音小区'],
            'default_conditions': [],
            'dimension': {
                'geographicdimension': '小区',
                'timedimension': '天',
                'enodebField': 'gnodeb_id',
                'cgiField': 'ncgi',
                'timeField': 'starttime',
                'cellField': 'nrcell',
                'cityField': 'city',
            }
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
