# -*- coding: utf-8 -*-
"""
通用数据提取工具 - 优化版Demo
现代化UI设计展示
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

class ModernExtractorGUIDemo:
    """优化版GUI Demo"""

    def __init__(self, root):
        self.root = root
        self.root.title("数据提取工具 Pro")
        self.root.geometry("1100x800")
        self.root.minsize(950, 700)
        
        self.setup_styles()
        self.create_ui()
        self.center_window()
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('.', font=('Microsoft YaHei UI', 10))
        style.configure('TFrame', background='#f5f7fa')
        style.configure('Card.TFrame', background='white')
        style.configure('Title.TLabel', 
                       font=('Microsoft YaHei UI', 18, 'bold'),
                       background='#1a73e8',
                       foreground='white')
        style.configure('Subtitle.TLabel',
                       font=('Microsoft YaHei UI', 11),
                       background='#f5f7fa',
                       foreground='#5f6368')
        style.configure('Section.TLabelframe',
                       background='white',
                       borderwidth=0,
                       relief='flat')
        style.configure('Section.TLabelframe.Label',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       foreground='#1a73e8',
                       background='white')
        style.configure('Status.TLabel',
                       font=('Microsoft YaHei UI', 9),
                       background='white')
        style.configure('Accent.TButton',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=(20, 8),
                       background='#1a73e8',
                       foreground='white',
                       borderwidth=0)
        style.map('Accent.TButton',
                 background=[('active', '#1557b0'), ('pressed', '#104ba0')])
        style.configure('Secondary.TButton',
                       font=('Microsoft YaHei UI', 9),
                       padding=(12, 6),
                       background='white',
                       foreground='#5f6368',
                       borderwidth=1,
                       relief='solid')
        style.map('Secondary.TButton',
                 background=[('active', '#f0f4f8')])
        style.configure('Danger.TButton',
                       font=('Microsoft YaHei UI', 9, 'bold'),
                       padding=(12, 6),
                       background='#ea4335',
                       foreground='white',
                       borderwidth=0)
        style.configure('Success.TButton',
                       font=('Microsoft YaHei UI', 9, 'bold'),
                       padding=(12, 6),
                       background='#34a853',
                       foreground='white',
                       borderwidth=0)
        style.configure('TCheckbutton',
                       font=('Microsoft YaHei UI', 9),
                       background='white')
        style.configure('TEntry',
                       font=('Microsoft YaHei UI', 10),
                       fieldbackground='white',
                       padding=5)
        style.configure('Horizontal.TProgressbar',
                       troughcolor='#e8eaed',
                       background='#1a73e8',
                       thickness=8)
        style.configure('TLabelframe',
                       background='white')
        style.configure('TLabelframe.Label',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       foreground='#202124',
                       background='white')

    def create_ui(self):
        main_container = ttk.Frame(self.root, style='TFrame')
        main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_header(main_container)
        
        content = ttk.Frame(main_container, style='TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # 第一位置：查询参数
        self.create_query_card(content)
        
        # 第二行：登录配置 + 地市日期选项
        second_row = ttk.Frame(content, style='TFrame')
        second_row.pack(fill=tk.X, pady=(10, 10))
        
        # 第二左下方：登录配置
        self.create_login_card(second_row)
        
        # 第二右边：地市、日期等选项
        self.create_params_card(second_row)
        
        # 底部：进度和日志
        self.create_bottom_section(content)

    def create_header(self, parent):
        header = tk.Frame(parent, bg='#1a73e8', height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        left_frame = tk.Frame(header, bg='#1a73e8')
        left_frame.pack(side=tk.LEFT, padx=25, pady=15)
        
        icon_label = tk.Label(left_frame, text="📊", font=('Segoe UI Emoji', 24), 
                             bg='#1a73e8', fg='white')
        icon_label.pack(side=tk.LEFT, padx=(0, 12))
        
        title = tk.Label(left_frame, text="数据提取工具 Pro", 
                        font=('Microsoft YaHei UI', 18, 'bold'),
                        bg='#1a73e8', fg='white')
        title.pack(side=tk.LEFT)
        
        version = tk.Label(left_frame, text="v2.0", 
                          font=('Microsoft YaHei UI', 9),
                          bg='#1557b0', fg='white',
                          padx=8, pady=2)
        version.pack(side=tk.LEFT, padx=(12, 0))
        
        right_frame = tk.Frame(header, bg='#1a73e8')
        right_frame.pack(side=tk.RIGHT, padx=25, pady=15)
        
        status_dot = tk.Label(right_frame, text="●", font=('Arial', 14),
                            bg='#1a73e8', fg='#34a853')
        status_dot.pack(side=tk.LEFT)
        status_text = tk.Label(right_frame, text="系统就绪", 
                              font=('Microsoft YaHei UI', 10),
                              bg='#1a73e8', fg='white')
        status_text.pack(side=tk.LEFT, padx=(6, 0))

    def create_card(self, parent, title, **kwargs):
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

    def create_login_card(self, parent):
        card = self.create_card(parent, "🔐 登录配置", width=380)
        card.pack(side=tk.LEFT, padx=(0, 10))
        
        body = tk.Frame(card, bg='white')
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        
        row1 = tk.Frame(body, bg='white')
        row1.pack(fill=tk.X, pady=(0, 10))
        
        user_frame = tk.Frame(row1, bg='white')
        user_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(user_frame, text="用户名", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(anchor='w')
        entry_user = tk.Entry(user_frame, font=('Microsoft YaHei UI', 10),
                             relief='solid', bd=1, width=18)
        entry_user.insert(0, "admin")
        entry_user.pack(fill=tk.X, pady=(4, 0))
        
        pass_frame = tk.Frame(row1, bg='white')
        pass_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        tk.Label(pass_frame, text="密码", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(anchor='w')
        entry_pass = tk.Entry(pass_frame, font=('Microsoft YaHei UI', 10),
                             show="●", relief='solid', bd=1, width=18)
        entry_pass.insert(0, "********")
        entry_pass.pack(fill=tk.X, pady=(4, 0))
        
        status_bar = tk.Frame(body, bg='#e8f5e9', relief='flat')
        status_bar.pack(fill=tk.X, pady=(8, 0))
        
        status_icon = tk.Label(status_bar, text="✓", font=('Arial', 12, 'bold'),
                              bg='#e8f5e9', fg='#34a853')
        status_icon.pack(side=tk.LEFT, padx=(10, 6), pady=6)
        
        status_lbl = tk.Label(status_bar, text="已连接", 
                             font=('Microsoft YaHei UI', 10, 'bold'),
                             bg='#e8f5e9', fg='#34a853')
        status_lbl.pack(side=tk.LEFT, pady=6, padx=(0, 10))
        
        login_btn = tk.Button(status_bar, text="登录", 
                             font=('Microsoft YaHei UI', 10, 'bold'),
                             bg='#1a73e8', fg='white', bd=0,
                             cursor='hand2', padx=20, pady=4)
        login_btn.pack(side=tk.RIGHT, padx=(10, 0), pady=6)

    def create_params_card(self, parent):
        card = self.create_card(parent, "� 提取参数")
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
        city_combo = ttk.Combobox(city_frame, values=['阳江', '广州', '深圳', '佛山'],
                                 state='readonly', width=14)
        city_combo.set('阳江')
        city_combo.pack(pady=(4, 0))
        
        quick_frame = tk.Frame(row1, bg='white')
        quick_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(quick_frame, text="快捷日期", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(anchor='w')
        
        quick_inner = tk.Frame(quick_frame, bg='white')
        quick_inner.pack(pady=(4, 0))
        
        for text in ["昨天", "近7天", "近30天"]:
            btn = tk.Button(quick_inner, text=text, font=('Microsoft YaHei UI', 8),
                           bg='#f1f3f4', fg='#5f6368', bd=0, padx=10, pady=3,
                           cursor='hand2', relief='flat')
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
        
        start_entry = tk.Entry(date_inner, font=('Microsoft YaHei UI', 9),
                              width=12, relief='solid', bd=1)
        start_entry.insert(0, "2026-04-01")
        start_entry.pack(side=tk.LEFT)
        
        tk.Label(date_inner, text=" 至 ", font=('Microsoft YaHei UI', 9),
                bg='white', fg='#5f6368').pack(side=tk.LEFT, padx=4)
        
        end_entry = tk.Entry(date_inner, font=('Microsoft YaHei UI', 9),
                            width=12, relief='solid', bd=1)
        end_entry.insert(0, "2026-04-19")
        end_entry.pack(side=tk.LEFT)
        
        # 操作按钮
        btn_row = tk.Frame(body, bg='white')
        btn_row.pack(fill=tk.X, pady=(8, 0))
        
        extract_btn = tk.Button(btn_row, text="▶ 开始提取", 
                               font=('Microsoft YaHei UI', 11, 'bold'),
                               bg='#1a73e8', fg='white', bd=0,
                               cursor='hand2', padx=28, pady=8)
        extract_btn.pack(side=tk.LEFT)
        
        stop_btn = tk.Button(btn_row, text="⏹ 停止", 
                            font=('Microsoft YaHei UI', 10),
                            bg='#ea4335', fg='white', bd=0,
                            cursor='hand2', padx=18, pady=6)
        stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        open_btn = tk.Button(btn_row, text="📁 打开目录", 
                            font=('Microsoft YaHei UI', 9),
                            bg='white', fg='#5f6368', bd=1,
                            cursor='hand2', padx=14, pady=5)
        open_btn.pack(side=tk.RIGHT)

    def create_query_card(self, parent):
        card = self.create_card(parent, "🔍 查询参数")
        card.pack(fill=tk.X, pady=(0, 10))
        
        body = tk.Frame(card, bg='white')
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        
        # 数据分类和数据表选择
        top_row = tk.Frame(body, bg='white')
        top_row.pack(fill=tk.X, pady=(0, 12))
        
        cat_frame = tk.Frame(top_row, bg='white', width=200, height=150)
        cat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_frame.pack_propagate(False)
        
        tk.Label(cat_frame, text="数据分类", font=('Microsoft YaHei UI', 10, 'bold'),
                bg='white', fg='#202124').pack(anchor='w', pady=(0, 8))
        
        categories = [
            ("干扰", True),
            ("容量", False),
            ("工参", False),
            ("语音报表", False),
            ("小区性能", False)
        ]
        
        for name, checked in categories:
            var = tk.IntVar(value=int(checked))
            cb = tk.Checkbutton(cat_frame, text=name, variable=var,
                               font=('Microsoft YaHei UI', 9),
                               bg='white', fg='#3c4043',
                               selectcolor='#e8f0fe',
                               activebackground='white',
                               activeforeground='#1a73e8',
                               cursor='hand2')
            cb.pack(anchor='w', pady=2)
        
        table_frame = tk.Frame(top_row, bg='white')
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0))
        
        tk.Label(table_frame, text="选择数据表", font=('Microsoft YaHei UI', 10, 'bold'),
                bg='white', fg='#202124').pack(anchor='w', pady=(0, 8))
        
        tables_grid = tk.Frame(table_frame, bg='white')
        tables_grid.pack(fill=tk.X)
        
        tables = [
            "5G干扰小区", "4G干扰小区",
            "5G小区容量报表", "重要场景-天",
            "5G小区工参报表", "4G小区工参报表",
            "VoLTE小区监控预警", "VONR小区监控预警",
            "EPSFB小区监控预警", "5G小区性能KPI报表",
            "4G小区性能KPI报表"
        ]
        
        for i, name in enumerate(tables):
            var = tk.IntVar(value=1 if i < 2 else 0)
            cb = tk.Checkbutton(tables_grid, text=name, variable=var,
                               font=('Microsoft YaHei UI', 9),
                               bg='white', fg='#3c4043',
                               selectcolor='#e8f0fe',
                               activebackground='white',
                               activeforeground='#1a73e8',
                               cursor='hand2')
            row, col = i // 3, i % 3
            cb.grid(row=row, column=col, sticky='w', padx=(0, 25), pady=2)

    def create_bottom_section(self, parent):
        bottom = tk.Frame(parent, bg='white', highlightbackground='#e8eaed',
                         highlightthickness=1)
        bottom.pack(fill=tk.BOTH, expand=True)
        
        progress_area = tk.Frame(bottom, bg='white')
        progress_area.pack(fill=tk.X, padx=16, pady=(12, 8))
        
        progress_info = tk.Frame(progress_area, bg='white')
        progress_info.pack(fill=tk.X)
        
        lbl_pct = tk.Label(progress_info, text="进度: 65%", 
                          font=('Microsoft YaHei UI', 10, 'bold'),
                          bg='white', fg='#1a73e8')
        lbl_pct.pack(side=tk.LEFT)
        
        lbl_detail = tk.Label(progress_info, text="正在提取: 5G干扰小区 (12,450/19,200)",
                             font=('Microsoft YaHei UI', 9),
                             bg='white', fg='#5f6368')
        lbl_detail.pack(side=tk.RIGHT)
        
        progress_outer = tk.Frame(progress_area, bg='#e8eaed', height=8)
        progress_outer.pack(fill=tk.X, pady=(8, 0))
        progress_outer.pack_propagate(False)
        
        progress_fill = tk.Frame(progress_outer, bg='#1a73e8', height=8)
        progress_fill.place(relx=0, rely=0, relwidth=0.65)
        
        log_header = tk.Frame(bottom, bg='white')
        log_header.pack(fill=tk.X, padx=16)
        
        tk.Label(log_header, text="📋 运行日志", 
                font=('Microsoft YaHei UI', 10, 'bold'),
                bg='white', fg='#202124').pack(side=tk.LEFT)
        
        clear_btn = tk.Button(log_header, text="清空", font=('Microsoft YaHei UI', 8),
                             bg='white', fg='#5f6368', bd=0,
                             cursor='hand2')
        clear_btn.pack(side=tk.RIGHT)
        
        log_frame = tk.Frame(bottom, bg='white')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 12))
        
        log_text = tk.Text(log_frame, wrap=tk.WORD, font=('Consolas', 9),
                          bg='#f8f9fa', fg='#3c4043', bd=0,
                          padx=10, pady=8, state='disabled')
        log_text.pack(fill=tk.BOTH, expand=True)
        
        log_text.config(state='normal')
        logs = [
            ('[INFO]    2026-04-21 10:30:15  系统启动完成', '#3c4043'),
            ('[SUCCESS] 2026-04-21 10:30:16  登录验证成功 ✓', '#34a853'),
            ('[INFO]    2026-04-21 10:30:17  开始查询: 5G干扰小区', '#3c4043'),
            ('[DEBUG]   2026-04-21 10:30:18  查询参数: 地市=阳江, 日期=2026-04-01~2026-04-19', '#80868b'),
            ('[INFO]    2026-04-21 10:30:20  获取到 19200 条记录', '#3c4043'),
            ('[INFO]    2026-04-21 10:30:22  正在导出数据...', '#3c4043'),
            ('[SUCCESS] 2026-04-21 10:30:25  导出完成: 5G干扰小区_20260419.xlsx (2.3MB)', '#34a853'),
            ('[INFO]    2026-04-21 10:30:26  开始查询: 4G干扰小区', '#1a73e8'),
            ('[PROGRESS]2026-04-21 10:30:28  已处理 12,450 / 19,200 条 (65%)', '#1a73e8'),
        ]
        
        for text, color in logs:
            log_text.insert(tk.END, text + '\n')
            end_line = int(log_text.index('end-1c').split('.')[0])
            start = f'{end_line-1}.0'
            end = f'{end_line-1}.end'
            log_text.tag_add(color, start, end)
            log_text.tag_config(color, foreground=color)
        
        log_text.config(state='disabled')
        log_text.see(tk.END)
        
        status_bar = tk.Frame(bottom, bg='#f8f9fa', height=32)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)
        
        tk.Label(status_bar, text="✓ 数据输出目录: ./data_output/", 
                font=('Microsoft YaHei UI', 8),
                bg='#f8f9fa', fg='#5f6368').pack(side=tk.LEFT, padx=16, pady=8)
        
        tk.Label(status_bar, text="v2.0.1 | © 2026", 
                font=('Microsoft YaHei UI', 8),
                bg='#f8f9fa', fg='#bdc1c6').pack(side=tk.RIGHT, padx=16, pady=8)

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

if __name__ == '__main__':
    root = tk.Tk()
    app = ModernExtractorGUIDemo(root)
    root.mainloop()