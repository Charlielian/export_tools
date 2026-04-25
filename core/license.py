# -*- coding: utf-8 -*-
"""
授权管理模块
负责硬件信息获取、机器码生成和授权验证
"""

import hashlib
import platform
import subprocess
import os
import struct
import base64

from datetime import datetime

from utils.config import LICENSE_FILE, EXPIRY_DATE
from utils.crypto import aes_decrypt


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
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
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


def get_windows_hw_info():
    """获取Windows硬件信息"""
    try:
        import wmi
        c = wmi.WMI()
        hw_info = {"cpu_id": "", "board_sn": "", "disk_sn": "", "mac": ""}
        cpu_list = c.Win32_Processor()
        hw_info["cpu_id"] = cpu_list[0].ProcessorId.strip() if (cpu_list and cpu_list[0].ProcessorId) else "unknown_cpu"
        board_list = c.Win32_BaseBoard()
        hw_info["board_sn"] = board_list[0].SerialNumber.strip() if (board_list and board_list[0].SerialNumber) else "unknown_board"
        disk_list = c.Win32_DiskDrive()
        hw_info["disk_sn"] = disk_list[0].SerialNumber.strip() if (disk_list and disk_list[0].SerialNumber) else "unknown_disk"
        nic_list = c.Win32_NetworkAdapterConfiguration(IPEnabled=True)
        hw_info["mac"] = nic_list[0].MACAddress.strip().replace(":", "") if (nic_list and nic_list[0].MACAddress) else "unknown_mac"
        return hw_info
    except:
        return {"cpu_id": "unknown", "board_sn": "unknown", "disk_sn": "unknown", "mac": "unknown"}


def get_linux_hw_info():
    """获取Linux硬件信息"""
    hw_info = {"cpu_id": "", "board_sn": "", "disk_sn": "", "mac": ""}
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f.readlines():
                if "serial" in line.lower():
                    hw_info["cpu_id"] = line.split(":")[1].strip()
                    break
        hw_info["cpu_id"] = hw_info["cpu_id"] if hw_info["cpu_id"] else "unknown_cpu"
    except:
        hw_info["cpu_id"] = "unknown_cpu"
    try:
        with open("/sys/devices/virtual/dmi/id/board_serial", "r") as f:
            hw_info["board_sn"] = f.read().strip()
    except:
        hw_info["board_sn"] = "unknown_board"
    try:
        cmd = ["lsblk", "-o", "SERIAL", "-n", "/dev/sda"]
        hw_info["disk_sn"] = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
    except:
        hw_info["disk_sn"] = "unknown_disk"
    try:
        for path in ["/sys/class/net/eth0/address", "/sys/class/net/ens33/address"]:
            if os.path.exists(path):
                with open(path, "r") as f:
                    hw_info["mac"] = f.read().strip().replace(":", "")
                break
        hw_info["mac"] = hw_info.get("mac", "unknown_mac")
    except:
        hw_info["mac"] = "unknown_mac"
    return hw_info


def get_hw_info():
    """跨平台获取硬件信息"""
    system = platform.system()
    if system == "Windows":
        return get_windows_hw_info()
    elif system == "Darwin":
        return get_macos_hw_info()
    elif system == "Linux":
        return get_linux_hw_info()
    else:
        return {"cpu_id": "unknown", "board_sn": "unknown", "disk_sn": "unknown", "mac": "unknown"}


def generate_machine_code(hw_info):
    """生成机器码（基于硬件信息）"""
    raw_str = f"{hw_info['cpu_id']}-{hw_info['board_sn']}-{hw_info['disk_sn']}-{hw_info['mac']}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def get_public_key():
    """获取公钥文件内容"""
    public_key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '授权工具', 'public_key.pem')
    if not os.path.exists(public_key_path):
        return None
    with open(public_key_path, 'r') as f:
        content = f.read()
        return content.replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', '').replace('\n', '')


def load_license():
    """加载本地license文件"""
    license_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', LICENSE_FILE)
    if not os.path.exists(license_path):
        return None
    try:
        with open(license_path, 'rb') as f:
            return f.read()
    except Exception:
        return None


def verify_license(machine_code):
    """验证授权 - 返回(True, None)表示有效，(False, 错误信息)表示无效"""
    import os

    license_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', LICENSE_FILE)

    if not os.path.exists(license_file):
        return False, "未找到授权文件"

    try:
        with open(license_file, 'rb') as f:
            license_data = f.read()

        parts = license_data.split(b'|')
        if len(parts) < 2:
            return False, "授权文件格式错误"

        sn_len_bytes = parts[0]
        sn_len = struct.unpack(">I", sn_len_bytes)[0]
        sn = parts[1][:sn_len].decode('utf-8')
        signature = parts[1][sn_len:].decode('utf-8')
        encrypted_data = parts[2]

        if sn != machine_code:
            return False, "机器码不匹配"

        AES_KEY = b"GMCCLicenseV2Key"
        decrypted = aes_decrypt(encrypted_data, AES_KEY)
        expiry_str = decrypted.split('|')[0]

        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiry_date:
            return False, f"授权已过期（{expiry_str}）"

        return True, None

    except Exception as e:
        return False, f"授权验证失败: {str(e)}"
