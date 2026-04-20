# -*- coding: utf-8 -*-
"""
免审批导出工具 - 授权文件生成器
用于为用户生成 license.dat 授权文件

使用方法：
    1. 用户运行 universal_extractor_gui.py，获取机器码
    2. 用户将机器码发给管理员
    3. 管理员运行本脚本，输入机器码，生成 license.dat
    4. 管理员将 license.dat 发给用户
"""
import os
import sys
import hashlib
import platform
import subprocess

# AES加密依赖
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ImportError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad

# 必须与 universal_extractor_gui.py 中的配置保持一致
LICENSE_FILE = "license.dat"
AES_KEY = b"GMCC_License_Key"  # 16字节


def aes_encrypt(plain_text):
    """AES加密"""
    import os
    iv = os.urandom(16)  # 随机生成IV
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    padded_data = pad(plain_text.encode("utf-8"), 16)
    encrypted_data = cipher.encrypt(padded_data)
    return iv + encrypted_data  # IV + 密文


def create_license(machine_code):
    """生成授权文件"""
    # 清理输入
    machine_code = machine_code.strip()
    
    # 验证机器码格式（应该是64位的SHA256哈希）
    if len(machine_code) != 64:
        print(f"错误：机器码长度应为64位，当前为{len(machine_code)}位")
        return False
    
    try:
        int(machine_code, 16)  # 验证是否为有效的十六进制
    except ValueError:
        print("错误：机器码包含非法字符")
        return False
    
    # 生成授权文件
    encrypted_fp = aes_encrypt(machine_code)
    with open(LICENSE_FILE, "wb") as f:
        f.write(encrypted_fp)
    
    print(f"\n授权文件已生成：{os.path.abspath(LICENSE_FILE)}")
    print(f"授权机器码：{machine_code}")
    return True


def main():
    """主函数"""
    if sys.version_info < (3, 6):
        print("要求Python 3.6及以上版本")
        sys.exit(1)
    
    print("=" * 60)
    print("   免审批导出工具 - 授权文件生成器")
    print("=" * 60)
    
    print("\n使用说明：")
    print("  1. 用户运行 universal_extractor_gui.py，获取机器码")
    print("  2. 用户将机器码发给管理员")
    print("  3. 管理员运行本脚本，输入机器码，生成 license.dat")
    print("  4. 管理员将 license.dat 发给用户")
    print("\n" + "=" * 60)
    
    # 获取用户输入
    machine_code = input("\n请输入用户的机器码：").strip()
    
    if not machine_code:
        print("错误：机器码不能为空")
        sys.exit(1)
    
    if create_license(machine_code):
        print("\n" + "=" * 60)
        print("完成！将 license.dat 文件发给用户即可。")
        print("=" * 60)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
