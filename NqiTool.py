# -*- coding: utf-8 -*-
"""
NQI工具 - 主入口
NQI平台数据提取工具

使用方法：
    python NqiTool.py
"""

import sys
import tkinter as tk
from tkinter import messagebox
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

    valid, error = verify_license(machine_code)

    if not valid:
        print(f"授权验证失败: {error}")
        return False, error

    print("授权验证通过！")
    return True, None


def main():
    """主函数"""
    print("=" * 60)
    print("   NQI工具 v1.0")
    print("   NQI平台数据提取工具")
    print("=" * 60)

    valid, error = check_license()
    if not valid:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("授权验证失败", f"软件授权验证失败:\n{error}\n\n请联系管理员获取授权。")
        root.destroy()
        sys.exit(1)

    expiry_time = datetime.strptime("2026-06-30", "%Y-%m-%d")

    root = tk.Tk()
    app = NqiToolGUI(root, expiry_time)
    app.run()


if __name__ == '__main__':
    main()
