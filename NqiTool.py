# -*- coding: utf-8 -*-
"""
NQI工具 - 主入口
NQI平台数据提取工具

使用方法：
    python NqiTool.py
"""

import sys
import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from core.license import get_hw_info, generate_machine_code, verify_license
from gui.main_window import NqiToolGUI


def check_license():
    """检查授权"""
    print("正在检查授权...")

    hw_info = get_hw_info()
    machine_code = generate_machine_code(hw_info)

    print(f"机器码: {machine_code}")
    print(f"请将机器码发送给管理员获取授权")

    return True, None, machine_code

    valid, error = verify_license(machine_code)

    if not valid:
        print(f"授权验证失败: {error}")
        return False, error, machine_code

    print("授权验证通过！")
    return True, None, machine_code


def show_error_dialog_with_gui(title, message, machine_code):
    """显示带机器码的错误对话框"""
    root = tk.Tk()
    root.title(title)
    root.geometry("500x350")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    style = ttk.Style()
    style.configure("Error.TLabel", foreground="red", font=("Arial", 11))

    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main_frame, text="授权验证失败",
             font=("Arial", 14, "bold")).pack(pady=(0, 10))

    ttk.Label(main_frame, text="错误信息：",
             font=("Arial", 10, "bold")).pack(anchor=tk.W)
    ttk.Label(main_frame, text=message,
             style="Error.TLabel", wraplength=450).pack(fill=tk.X, pady=(0, 15))

    ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)

    ttk.Label(main_frame, text="您的机器码：",
             font=("Arial", 10, "bold")).pack(anchor=tk.W)
    code_frame = ttk.Frame(main_frame)
    code_frame.pack(fill=tk.X, pady=5)

    code_var = tk.StringVar(value=machine_code)
    code_entry = ttk.Entry(code_frame, textvariable=code_var, font=("Courier", 9))
    code_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    code_entry.configure(state='readonly')

    def copy_code():
        root.clipboard_clear()
        root.clipboard_append(machine_code)
        copy_btn.config(text="已复制!")

    copy_btn = ttk.Button(code_frame, text="复制", command=copy_code)
    copy_btn.pack(side=tk.LEFT, padx=(5, 0))

    ttk.Label(main_frame, text="请将机器码发送给管理员获取授权",
             foreground="gray").pack(pady=(10, 0))

    def on_close():
        root.destroy()
        sys.exit(1)

    ok_btn = ttk.Button(main_frame, text="确定", command=on_close)
    ok_btn.pack(pady=(20, 0))

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def main():
    """主函数"""
    print("=" * 60)
    print("   NQI工具 v1.0")
    print("   NQI平台数据提取工具")
    print("=" * 60)

    valid, error, machine_code = check_license()
    if not valid:
        show_error_dialog_with_gui("授权验证失败", error, machine_code)
        sys.exit(1)

    expiry_time = datetime.strptime("2026-06-30", "%Y-%m-%d")

    root = tk.Tk()
    app = NqiToolGUI(root, expiry_time)
    app.run()


if __name__ == '__main__':
    main()