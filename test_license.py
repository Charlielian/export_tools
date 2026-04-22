# -*- coding: utf-8 -*-
"""测试授权验证"""
import os
import sys
import hashlib
import platform
import subprocess

# AES加密依赖
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad

LICENSE_FILE = "license.dat"
AES_KEY = b"GMCC_License_Key"

def get_macos_hw_info():
    """获取macOS硬件信息"""
    hw_info = {"cpu_id": "", "board_sn": "", "disk_sn": "", "mac": ""}
    try:
        cmd = ["ioreg", "-l", "-w0", "-r", "-c", "IOPlatformExpertDevice", "-d", "2"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        hw_info["board_sn"] = output.split('"IOPlatformSerialNumber" = ')[1].split('"')[1].strip()
    except:
        hw_info["board_sn"] = "unknown_board"
    try:
        cmd = ["sysctl", "-n", "machdep.cpu.brand_string"]
        hw_info["cpu_id"] = subprocess.check_output(cmd).decode("utf-8").strip()
    except:
        hw_info["cpu_id"] = "unknown_cpu"
    try:
        cmd = ["diskutil", "info", "/"]
        output = subprocess.check_output(cmd).decode("utf-8")
        hw_info["disk_sn"] = output.split("Volume UUID:")[1].split("\n")[0].strip()
    except:
        hw_info["disk_sn"] = "unknown_disk"
    try:
        cmd = ["ifconfig", "en0"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        hw_info["mac"] = output.split("ether")[1].split(" ")[1].strip().replace(":", "")
    except:
        hw_info["mac"] = "unknown_mac"
    return hw_info

def get_hw_info():
    """跨平台获取硬件信息"""
    system = platform.system()
    if system == "Windows":
        return {"cpu_id": "win_cpu", "board_sn": "win_board", "disk_sn": "win_disk", "mac": "win_mac"}
    elif system == "Darwin":
        return get_macos_hw_info()
    elif system == "Linux":
        return {"cpu_id": "linux_cpu", "board_sn": "linux_board", "disk_sn": "linux_disk", "mac": "linux_mac"}
    else:
        return {"cpu_id": "unknown", "board_sn": "unknown", "disk_sn": "unknown", "mac": "unknown"}

def generate_machine_fingerprint(hw_info):
    """生成机器指纹"""
    raw_str = f"{hw_info['cpu_id']}-{hw_info['board_sn']}-{hw_info['disk_sn']}-{hw_info['mac']}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

def aes_decrypt(encrypted_data):
    """AES解密"""
    iv = encrypted_data[:16]
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_data[16:]), 16)
    return decrypted_data.decode("utf-8")

# 测试
print(f"当前目录: {os.getcwd()}")
print(f"LICENSE_FILE: {LICENSE_FILE}")
print(f"文件存在: {os.path.exists(LICENSE_FILE)}")

hw_info = get_hw_info()
print(f"硬件信息: {hw_info}")
fp = generate_machine_fingerprint(hw_info)
print(f"机器码: {fp}")
