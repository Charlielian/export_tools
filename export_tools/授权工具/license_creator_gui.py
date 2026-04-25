# -*- coding: utf-8 -*-
"""
免审批导出工具 - 授权文件生成器（GUI版本）
提供图形界面，方便生成授权文件
"""
import os
import sys
import json
import base64
import struct
import hashlib
from datetime import datetime

# 加密依赖
try:
    from Crypto.Cipher import AES as AES_Cipher
    from Crypto.Util.Padding import pad
    from Crypto.PublicKey import RSA
    from Crypto.Hash import SHA256
    from Crypto.Signature import pkcs1_15
except ModuleNotFoundError:
    from Cryptodome.Cipher import AES as AES_Cipher
    from Cryptodome.Util.Padding import pad
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Hash import SHA256
    from Cryptodome.Signature import pkcs1_15

# 配置
PRIVATE_KEY_FILE = "private_key.pem"
LICENSE_RECORD_FILE = "license_records.json"


def load_records():
    """加载授权记录"""
    if os.path.exists(LICENSE_RECORD_FILE):
        try:
            with open(LICENSE_RECORD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []


def save_records(records):
    """保存授权记录"""
    with open(LICENSE_RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def add_record(machine_code, note=""):
    """添加授权记录"""
    records = load_records()

    # 检查是否已存在
    for record in records:
        if record["machine_code"] == machine_code:
            record["count"] = record.get("count", 1) + 1
            record["last_generate_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if note:
                record["note"] = note
            save_records(records)
            return

    # 新增记录
    records.append({
        "machine_code": machine_code,
        "first_generate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_generate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": 1,
        "note": note
    })
    save_records(records)


def load_private_key():
    """加载RSA私钥"""
    if not os.path.exists(PRIVATE_KEY_FILE):
        return None
    with open(PRIVATE_KEY_FILE, "rb") as f:
        return RSA.import_key(f.read())


def rsa_sign(data, private_key):
    """RSA签名"""
    h = SHA256.new(data.encode("utf-8"))
    signature = pkcs1_15.new(private_key).sign(h)
    return base64.b64encode(signature).decode("utf-8")


def create_license(machine_code, note=""):
    """生成授权文件（仅存储机器码）

    新格式：仅包含机器码，无过期日期
    过期日期在主程序中配置
    """
    machine_code = machine_code.strip()

    # 验证机器码
    if len(machine_code) != 64:
        return False, f"机器码长度应为64位，当前为{len(machine_code)}位"
    try:
        int(machine_code, 16)
    except ValueError:
        return False, "机器码包含非法字符"

    # 加载私钥（用于签名验证，非必需）
    private_key = load_private_key()
    if private_key:
        # 如果有私钥，进行签名（可选，增强安全性）
        signature = rsa_sign(machine_code, private_key)
        # 格式：SN长度(4字节) + SN + "|" + Base64签名
        sn_bytes = machine_code.encode("utf-8")
        sn_len = len(sn_bytes)
        license_data = struct.pack(">I", sn_len) + sn_bytes + b"|" + signature.encode("utf-8")
    else:
        # 无私钥，仅存储机器码
        license_data = machine_code.encode("utf-8")

    with open("license.dat", "wb") as f:
        f.write(license_data)

    # 添加授权记录
    add_record(machine_code, note)

    msg = f"授权文件已生成：{os.path.abspath('license.dat')}\n机器码：{machine_code}"
    if private_key:
        msg += "\n（已签名）"
    return True, msg


def main():
    """GUI主函数"""
    import tkinter as tk
    from tkinter import ttk, messagebox

    root = tk.Tk()
    root.title("授权文件生成器")
    root.geometry("700x500")
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - 700) // 2
    y = (screen_h - 500) // 2
    root.geometry(f"700x500+{x}+{y}")

    # 创建Notebook（标签页）
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # ========== 标签页1：生成授权 ==========
    gen_frame = ttk.Frame(notebook, padding="15")
    notebook.add(gen_frame, text="  生成授权  ")

    ttk.Label(gen_frame, text="授权文件生成器", font=("Arial", 16, "bold")).pack(pady=(0, 15))

    # 机器码输入
    ttk.Label(gen_frame, text="机器码：").pack(anchor=tk.W)
    machine_entry = ttk.Entry(gen_frame, width=60, font=("Courier New", 10))
    machine_entry.pack(fill=tk.X, pady=(5, 10))
    ttk.Label(gen_frame, text="（64位十六进制机器码，从用户处获取）", foreground="gray").pack(anchor=tk.W)

    # 备注输入
    ttk.Label(gen_frame, text="备注（可选）：").pack(anchor=tk.W, pady=(10, 5))
    note_entry = ttk.Entry(gen_frame, width=60, font=("Microsoft YaHei UI", 10))
    note_entry.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(gen_frame, text="（用于标记这台机器的用途，如：张三的电脑）", foreground="gray").pack(anchor=tk.W)

    # 提示信息
    ttk.Label(gen_frame, text="注意：过期日期在主程序的 EXPIRY_DATE 配置项中设置",
              foreground="#666666", font=("Microsoft YaHei UI", 9)).pack(pady=(10, 0))

    # 生成按钮
    def on_generate():
        machine_code = machine_entry.get().strip()
        if not machine_code:
            messagebox.showwarning("警告", "请输入机器码")
            return

        note = note_entry.get().strip()
        success, msg = create_license(machine_code, note)
        if success:
            messagebox.showinfo("成功", msg)
            # 清空输入框
            machine_entry.delete(0, tk.END)
            note_entry.delete(0, tk.END)
            # 刷新记录列表
            refresh_records()
        else:
            messagebox.showerror("失败", msg)

    btn_frame = ttk.Frame(gen_frame)
    btn_frame.pack(fill=tk.X, pady=(20, 0))

    ttk.Button(btn_frame, text="生成授权文件", command=on_generate).pack(side=tk.LEFT, padx=5)

    # ========== 标签页2：授权记录 ==========
    records_frame = ttk.Frame(notebook, padding="15")
    notebook.add(records_frame, text="  授权记录  ")

    ttk.Label(records_frame, text="授权记录", font=("Arial", 14, "bold")).pack(pady=(0, 10))

    # 创建Treeview显示记录
    columns = ("machine_code", "note", "count", "last_time")
    tree = ttk.Treeview(records_frame, columns=columns, show="headings", height=15)

    tree.heading("machine_code", text="机器码")
    tree.heading("note", text="备注")
    tree.heading("count", text="生成次数")
    tree.heading("last_time", text="最后生成时间")

    tree.column("machine_code", width=220)
    tree.column("note", width=150)
    tree.column("count", width=80, anchor="center")
    tree.column("last_time", width=160, anchor="center")

    # 添加滚动条
    scrollbar = ttk.Scrollbar(records_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_records():
        """刷新授权记录列表"""
        # 清空现有内容
        for item in tree.get_children():
            tree.delete(item)

        records = load_records()
        for record in records:
            tree.insert("", tk.END, values=(
                record.get("machine_code", ""),
                record.get("note", ""),
                record.get("count", 1),
                record.get("last_generate_time", "")
            ))

    def on_copy_code():
        """复制选中的机器码"""
        selection = tree.selection()
        if selection:
            values = tree.item(selection[0])["values"]
            root.clipboard_clear()
            root.clipboard_append(values[0])
            messagebox.showinfo("成功", "机器码已复制到剪贴板")

    def on_delete_record():
        """删除选中的记录"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一条记录")
            return

        if messagebox.askyesno("确认", "确定要删除这条授权记录吗？"):
            values = tree.item(selection[0])["values"]
            machine_code = values[0]
            records = load_records()
            records = [r for r in records if r["machine_code"] != machine_code]
            save_records(records)
            refresh_records()
            messagebox.showinfo("成功", "记录已删除")

    # 记录操作按钮
    record_btn_frame = ttk.Frame(records_frame)
    record_btn_frame.pack(fill=tk.X, pady=(10, 0))

    ttk.Button(record_btn_frame, text="刷新", command=refresh_records).pack(side=tk.LEFT, padx=5)
    ttk.Button(record_btn_frame, text="复制机器码", command=on_copy_code).pack(side=tk.LEFT, padx=5)
    ttk.Button(record_btn_frame, text="删除记录", command=on_delete_record).pack(side=tk.LEFT, padx=5)

    # 底部按钮
    bottom_frame = ttk.Frame(root, padding="10")
    bottom_frame.pack(fill=tk.X)

    # 统计信息
    records = load_records()
    ttk.Label(bottom_frame, text=f"共 {len(records)} 条授权记录", foreground="#666666").pack(side=tk.LEFT)
    ttk.Button(bottom_frame, text="退出", command=root.destroy).pack(side=tk.RIGHT)

    # 初始加载记录
    refresh_records()

    root.mainloop()


if __name__ == '__main__':
    main()
