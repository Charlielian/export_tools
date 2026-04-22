# -*- coding: utf-8 -*-
"""单独测试授权弹窗"""
import tkinter as tk
from tkinter import messagebox
import sys

def show_machine_code_dialog(parent, machine_code, error_title="授权验证失败"):
    """显示机器码弹窗"""
    messagebox.showerror(
        error_title,
        f"授权验证未通过，请联系作者获取授权。\n\n"
        f"您的机器码：\n{machine_code}\n\n"
        f"请复制机器码发给作者以获取授权文件。"
    )
    if messagebox.askyesno("退出程序", "是否退出程序？"):
        sys.exit(1)

# 测试机器码
test_code = "5ea6281d3f278d03c8902355c0bab4ffbee5faf540edb70c83dfd995e3e5a7de"

root = tk.Tk()
root.withdraw()
print("准备显示弹窗...")
show_machine_code_dialog(root, test_code, "授权验证失败 - 测试")
root.destroy()
print("弹窗已关闭")
