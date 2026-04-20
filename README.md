# 免审批导出工具

通用数据提取工具，支持多种数据表的自动导出，包括4G干扰小区、5G干扰小区、5G小区容量报表等。

## 功能特点

- **图形界面操作**：简洁易用的GUI界面
- **自动化导出**：支持定时自动导出数据
- **验证码识别**：集成验证码识别功能，减少人工干预
- **多种数据源支持**：
  - 4G干扰小区
  - 5G干扰小区
  - 5G小区容量报表
  - 告警KPI数据
  - 配置数据

## 环境要求

- Python 3.7+
- Windows/Linux/macOS

## 安装步骤

1. 克隆项目
```bash
git clone https://github.com/Charlielian/export_tools.git
cd export_tools
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置文件
编辑 `config.yaml` 文件，配置您的用户名、密码等信息。

## 使用方法

```bash
python universal_extractor_gui.py
```

## 项目结构

```
.
├── universal_extractor_gui.py    # 主程序入口（GUI版本）
├── requirements.txt             # Python依赖列表
├── config.yaml                  # 配置文件
├── captcha_images/             # 验证码图片目录
├── cookies/                     # Cookie存储目录
├── data_output/                 # 数据输出目录
└── logs/                        # 日志目录
```

## 依赖说明

- `requests` - HTTP请求库
- `pandas` - 数据处理
- `pycryptodome` - RSA加密
- `lxml` - XML/HTML解析
- `Pillow` - 图片处理
- `pyyaml` - YAML配置文件解析

## License

MIT License
