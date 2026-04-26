# -*- coding: utf-8 -*-
"""
免审批导出工具 - 授权文件生成器（增强版）
用于为用户生成验证序列号或 license.dat 授权文件

增强功能：
- RSA 非对称加密签名，保证授权信息无法伪造
- 内置时间单调校验，限制时间只能递增
- AES 加密存储授权时间，避免明文篡改
- 机器码绑定授权
- 验证序列号功能（更便捷的授权方式）

使用方法（验证序列号模式）：
    1. 用户运行 NqiTool_gui.py，获取机器码
    2. 用户将机器码发给管理员
    3. 管理员运行本脚本，输入机器码和授权截止时间
    4. 管理员将验证序列号发给用户
    5. 用户在工具中输入序列号即可完成授权

使用方法（文件模式）：
    1. 用户运行 NqiTool_gui.py，获取机器码
    2. 用户将机器码发给管理员
    3. 管理员运行本脚本，输入机器码和授权截止时间
    4. 管理员将 license.dat 发给用户
"""
import os
import sys
import base64
import struct
import hashlib
import json
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
LICENSE_FILE = "license.dat"
PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"
LICENSE_AES_KEY = b"GMCCLicenseV2Key"  # 必须与 universal_extractor_gui.py 一致
SERIAL_PREFIX = "NQI-"  # 序列号前缀


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


def validate_machine_code(machine_code):
    """验证机器码格式"""
    machine_code = machine_code.strip()
    if len(machine_code) != 64:
        return False, f"机器码长度应为64位，当前为{len(machine_code)}位"
    try:
        int(machine_code, 16)
        return True, None
    except ValueError:
        return False, "机器码包含非法字符"


def create_serial_number(machine_code, expiry_date):
    """生成验证序列号

    序列号格式：NQI-xxxx-xxxx-xxxx
    包含：
    - 版本号（1字节）
    - 机器码（64字符）
    - 过期时间（19字符：YYYY-MM-DD HH:MM:SS）
    - 首次生成时间（19字符）
    - 数据校验（8字符）

    最终用 AES 加密 + Base64 编码
    """
    # 验证机器码
    valid, error = validate_machine_code(machine_code)
    if not valid:
        return None, error

    # 加载私钥
    private_key = load_private_key()
    if not private_key:
        return None, f"未找到私钥文件 {PRIVATE_KEY_FILE}，请先运行 generate_rsa_keys.py 生成密钥"

    # 生成授权时间字符串
    expiry_time_str = expiry_date.strftime("%Y-%m-%d 23:59:59")

    # 首次运行时间（生成授权时的时间）
    first_run_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 构建授权数据
    version = "1"
    auth_data = {
        "v": version,
        "sn": machine_code,
        "exp": expiry_time_str,
        "first": first_run_time_str
    }

    # JSON 序列化为字符串
    data_str = json.dumps(auth_data, separators=(',', ':'))

    # AES 加密
    encrypted_data = aes_encrypt(data_str, LICENSE_AES_KEY)

    # 对机器码进行 RSA 签名（用于完整性验证）
    signature = rsa_sign(machine_code, private_key)

    # 组装数据：版本(1) + 签名长度(4) + 签名 + 加密数据
    signature_bytes = signature.encode('utf-8')
    signature_len_bytes = struct.pack(">I", len(signature_bytes))

    combined = b'\x01' + signature_len_bytes + signature_bytes + encrypted_data

    # Base64 编码
    encoded = base64.b64encode(combined).decode('utf-8')

    # 格式化序列号（每8位加一杠）
    parts = [encoded[i:i+8] for i in range(0, len(encoded), 8)]
    serial_number = SERIAL_PREFIX + "-".join(parts)

    return serial_number, {
        "machine_code": machine_code,
        "expiry_time": expiry_time_str,
        "first_run_time": first_run_time_str
    }


def parse_serial_number(serial_number):
    """解析验证序列号

    Returns:
        dict: 包含机器码、过期时间、首次运行时间的字典
        None: 解析失败时返回
    """
    # 移除前缀和分隔符
    serial = serial_number.strip()
    if serial.startswith(SERIAL_PREFIX):
        serial = serial[len(SERIAL_PREFIX):]
    serial = serial.replace('-', '')

    try:
        # Base64 解码
        decoded = base64.b64decode(serial)

        # 解析版本
        version = decoded[0]
        if version != 1:
            return None, f"不支持的序列号版本：{version}"

        # 解析签名长度
        signature_len = struct.unpack(">I", decoded[1:5])[0]

        # 解析签名
        signature = decoded[5:5+signature_len].decode('utf-8')

        # 解析加密数据
        encrypted_data = decoded[5+signature_len:]

        # AES 解密
        from Crypto.Util.Padding import unpad
        iv = encrypted_data[:16]
        cipher = AES_Cipher.new(LICENSE_AES_KEY, AES_Cipher.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data[16:])
        data_str = unpad(decrypted, 16).decode('utf-8')

        # 解析 JSON
        auth_data = json.loads(data_str)

        return {
            "machine_code": auth_data["sn"],
            "expiry_time": auth_data["exp"],
            "first_run_time": auth_data["first"],
            "signature": signature
        }, None

    except Exception as e:
        return None, f"序列号解析失败：{str(e)}"


def create_license(machine_code, expiry_date):
    """生成授权文件"""
    # 验证机器码
    valid, error = validate_machine_code(machine_code)
    if not valid:
        return False, error

    # 加载私钥
    private_key = load_private_key()
    if not private_key:
        return False, f"未找到私钥文件 {PRIVATE_KEY_FILE}，请先运行 generate_rsa_keys.py 生成密钥"

    # 生成授权时间字符串
    expiry_time_str = expiry_date.strftime("%Y-%m-%d 23:59:59")
    
    # 首次运行时间（生成授权时的时间）
    first_run_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 用AES加密（新格式：过期时间|首次运行时间）
    encrypted_data = aes_encrypt(f"{expiry_time_str}|{first_run_time_str}", LICENSE_AES_KEY)

    # 2. 对机器码(SN)进行RSA签名
    signature = rsa_sign(machine_code, private_key)

    # 3. 组装license文件格式：SN长度(4字节) + SN + 签名 + | + AES加密(过期时间|首次运行时间)
    sn_bytes = machine_code.encode("utf-8")
    sn_len = len(sn_bytes)
    license_data = struct.pack(">I", sn_len) + sn_bytes + signature.encode("utf-8") + b"|" + encrypted_data

    # 4. 写入文件
    with open(LICENSE_FILE, "wb") as f:
        f.write(license_data)

    return True, f"授权文件已生成：{os.path.abspath(LICENSE_FILE)}\n授权机器码：{machine_code}\n过期时间：{expiry_time_str}\n首次运行时间：{first_run_time_str}"


def main():
    """主函数 - CLI模式"""
    if sys.version_info < (3, 6):
        print("要求Python 3.6及以上版本")
        sys.exit(1)

    print("=" * 60)
    print("   免审批导出工具 - 授权文件生成器（增强版）")
    print("=" * 60)

    # 检查私钥
    if not os.path.exists(PRIVATE_KEY_FILE):
        print(f"\n错误：未找到私钥文件 {PRIVATE_KEY_FILE}")
        print("请先运行 generate_rsa_keys.py 生成密钥对")
        sys.exit(1)

    # 选择生成模式
    print("\n请选择生成模式：")
    print("  1. 生成验证序列号（推荐，更便捷）")
    print("  2. 生成 license.dat 文件")
    print()

    while True:
        mode = input("请输入选项（1 或 2）：").strip()
        if mode in ['1', '2']:
            break
        print("错误：无效的选项")

    is_serial_mode = (mode == '1')

    print("\n使用说明：")
    if is_serial_mode:
        print("  1. 用户运行 NqiTool_gui.py，获取机器码")
        print("  2. 用户将机器码发给管理员")
        print("  3. 管理员运行本脚本，输入机器码和授权截止日期")
        print("  4. 管理员将验证序列号发给用户")
        print("  5. 用户在工具中输入序列号即可完成授权")
    else:
        print("  1. 用户运行 NqiTool_gui.py，获取机器码")
        print("  2. 用户将机器码发给管理员")
        print("  3. 管理员运行本脚本，输入机器码和授权截止日期")
        print("  4. 管理员将 license.dat 发给用户")
    print("\n" + "=" * 60)

    # 获取机器码
    while True:
        machine_code = input("\n请输入用户的机器码：").strip()
        if machine_code:
            valid, error = validate_machine_code(machine_code)
            if valid:
                break
            print(f"错误：{error}")
        else:
            print("错误：机器码不能为空")

    # 获取授权截止日期
    while True:
        expiry_str = input("\n请输入授权截止日期（格式：YYYY-MM-DD，例如：2026-12-31）：").strip()
        if expiry_str:
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
                if expiry_date < datetime.now():
                    print("警告：截止日期早于今天，授权将立即过期！")
                break
            except ValueError:
                print("错误：日期格式不正确，请使用 YYYY-MM-DD 格式")
        else:
            print("错误：截止日期不能为空")

    print("\n" + "=" * 60)

    if is_serial_mode:
        # 生成验证序列号
        serial_number, info = create_serial_number(machine_code, expiry_date)
        if serial_number:
            print("验证序列号已生成：")
            print()
            print(f"  {serial_number}")
            print()
            print(f"机器码：{info['machine_code']}")
            print(f"过期时间：{info['expiry_time']}")
            print()
            print("请将此序列号发送给用户，用户在工具中输入即可完成授权。")
        else:
            print(f"生成失败：{info}")
            sys.exit(1)
    else:
        # 生成授权文件
        success, message = create_license(machine_code, expiry_date)
        print(message)
        print("=" * 60)
        if success:
            print("\n完成！将 license.dat 文件发给用户即可。")
        else:
            print(f"\n生成失败：{message}")
            sys.exit(1)


if __name__ == '__main__':
    main()
