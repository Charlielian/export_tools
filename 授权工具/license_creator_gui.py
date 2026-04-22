# -*- coding: utf-8 -*-
"""
免审批导出工具 - 授权文件生成器（GUI版本）
提供图形界面，方便选择授权日期
"""
import os
import sys
import base64
import struct
import hashlib
from datetime import datetime, timedelta

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
LICENSE_AES_KEY = b"GMCCLicenseV2Key"


def load_private_key():
    """加载RSA私钥"""
    if not os.path.exists(PRIVATE_KEY_FILE):
        return None
    with open(PRIVATE_KEY_FILE, "rb") as f:
        return RSA.import_key(f.read())


def aes_encrypt(plain_text, key):
    """AES加密"""
    import os
    iv = os.urandom(16)
    cipher = AES_Cipher.new(key, AES_Cipher.MODE_CBC, iv)
    padded_data = pad(plain_text.encode("utf-8"), 16)
    encrypted_data = cipher.encrypt(padded_data)
    return iv + encrypted_data


def rsa_sign(data, private_key):
    """RSA签名"""
    h = SHA256.new(data.encode("utf-8"))
    signature = pkcs1_15.new(private_key).sign(h)
    return base64.b64encode(signature).decode("utf-8")


def create_license(machine_code, expiry_date):
    """生成授权文件"""
    machine_code = machine_code.strip()

    # 验证机器码
    if len(machine_code) != 64:
        return False, f"机器码长度应为64位，当前为{len(machine_code)}位"
    try:
        int(machine_code, 16)
    except ValueError:
        return False, "机器码包含非法字符"

    # 加载私钥
    private_key = load_private_key()
    if not private_key:
        return False, f"未找到私钥文件 {PRIVATE_KEY_FILE}，请先运行 generate_rsa_keys.py"

    # 生成授权时间
    expiry_time_str = expiry_date.strftime("%Y-%m-%d 23:59:59")

    # 加密签名
    encrypted_expiry = aes_encrypt(expiry_time_str, LICENSE_AES_KEY)
    signature = rsa_sign(machine_code, private_key)

    # 组装文件
    sn_bytes = machine_code.encode("utf-8")
    sn_len = len(sn_bytes)
    license_data = struct.pack(">I", sn_len) + sn_bytes + signature.encode("utf-8") + b"|" + encrypted_expiry

    with open("license.dat", "wb") as f:
        f.write(license_data)

    return True, f"授权文件已生成：{os.path.abspath('license.dat')}\n过期时间：{expiry_time_str}"


def main():
    """GUI主函数"""
    import tkinter as tk
    from tkinter import ttk, messagebox

    # 检查私钥
    if not os.path.exists(PRIVATE_KEY_FILE):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("错误", f"未找到私钥文件 {PRIVATE_KEY_FILE}\n\n请先运行 generate_rsa_keys.py 生成密钥对")
        root.destroy()
        sys.exit(1)

    root = tk.Tk()
    root.title("授权文件生成器")
    root.geometry("550x400")
    root.resizable(False, False)
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - 550) // 2
    y = (screen_h - 400) // 2
    root.geometry(f"550x400+{x}+{y}")

    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 标题
    ttk.Label(main_frame, text="授权文件生成器", font=("Arial", 16, "bold")).pack(pady=(0, 10))

    # 机器码输入
    ttk.Label(main_frame, text="机器码：").pack(anchor=tk.W)
    machine_entry = ttk.Entry(main_frame, width=50, font=("Courier New", 10))
    machine_entry.pack(fill=tk.X, pady=(5, 10))
    ttk.Label(main_frame, text="（64位十六进制机器码，从用户处获取）", foreground="gray").pack(anchor=tk.W)

    # 日期选择
    ttk.Label(main_frame, text="授权截止日期：").pack(anchor=tk.W, pady=(10, 5))

    date_frame = ttk.Frame(main_frame)
    date_frame.pack(fill=tk.X, pady=5)

    # 年月日选择
    ttk.Label(date_frame, text="年：").pack(side=tk.LEFT)
    year_var = tk.StringVar(value=str(datetime.now().year))
    year_combo = ttk.Combobox(date_frame, textvariable=year_var, width=6, state="readonly")
    year_combo['values'] = tuple(str(y) for y in range(datetime.now().year, datetime.now().year + 10))
    year_combo.pack(side=tk.LEFT, padx=(0, 10))

    ttk.Label(date_frame, text="月：").pack(side=tk.LEFT)
    month_var = tk.StringVar(value=str(datetime.now().month))
    month_combo = ttk.Combobox(date_frame, textvariable=month_var, width=4, state="readonly")
    month_combo['values'] = tuple(str(m) for m in range(1, 13))
    month_combo.pack(side=tk.LEFT, padx=(0, 10))

    ttk.Label(date_frame, text="日：").pack(side=tk.LEFT)
    day_var = tk.StringVar(value=str(datetime.now().day))
    day_combo = ttk.Combobox(date_frame, textvariable=day_var, width=4, state="readonly")
    day_combo['values'] = tuple(str(d) for d in range(1, 32))
    day_combo.pack(side=tk.LEFT, padx=(0, 10))

    # 快捷按钮
    quick_frame = ttk.Frame(main_frame)
    quick_frame.pack(fill=tk.X, pady=10)

    def set_date(days):
        target = datetime.now() + timedelta(days=days)
        year_var.set(str(target.year))
        month_var.set(str(target.month))
        day_var.set(str(target.day))

    ttk.Button(quick_frame, text="1个月", command=lambda: set_date(30)).pack(side=tk.LEFT, padx=2)
    ttk.Button(quick_frame, text="3个月", command=lambda: set_date(90)).pack(side=tk.LEFT, padx=2)
    ttk.Button(quick_frame, text="半年", command=lambda: set_date(180)).pack(side=tk.LEFT, padx=2)
    ttk.Button(quick_frame, text="1年", command=lambda: set_date(365)).pack(side=tk.LEFT, padx=2)
    ttk.Button(quick_frame, text="永久", command=lambda: set_date(36500)).pack(side=tk.LEFT, padx=2)

    # 生成按钮
    def on_generate():
        machine_code = machine_entry.get().strip()
        if not machine_code:
            messagebox.showwarning("警告", "请输入机器码")
            return

        try:
            expiry_date = datetime(int(year_var.get()), int(month_var.get()), int(day_var.get()))
        except ValueError:
            messagebox.showerror("错误", "日期无效")
            return

        success, msg = create_license(machine_code, expiry_date)
        if success:
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("失败", msg)

    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill=tk.X, pady=(20, 0))

    ttk.Button(btn_frame, text="生成授权文件", command=on_generate).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="退出", command=root.destroy).pack(side=tk.LEFT, padx=5)

    root.mainloop()


if __name__ == '__main__':
    main()
