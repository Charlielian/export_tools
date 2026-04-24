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

### 方法一：直接使用已构建的 EXE（推荐）

1. 访问 GitHub 仓库的 [Actions](https://github.com/Charlielian/export_tools/actions) 页面
2. 选择最新的成功构建
3. 下载 `universal-extractor-exe` 构建产物
4. 解压后运行 `universal_extractor_gui.exe`

### 方法二：从源码运行

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
├── README.md                    # 项目说明文档
├── 授权工具/                     # 授权相关工具
│   ├── generate_rsa_keys.py     # RSA密钥生成
│   ├── license_creator_gui.py   # 许可证创建GUI
│   ├── license_records.json     # 许可证记录
│   ├── private_key.pem          # 私钥文件
│   ├── public_key.pem           # 公钥文件
│   └── universal_extractor_gui_license_creator.py  # 许可证创建器
├── captcha_images/             # 验证码图片目录
├── cookies/                     # Cookie存储目录
├── data_output/                 # 数据输出目录
└── logs/                        # 日志目录
```

## 依赖说明

- `requests>=2.28.0` - HTTP请求库
- `pandas>=1.5.0` - 数据处理
- `openpyxl>=3.0.0` - 用于Excel导出
- `pycryptodome>=3.15.0` - RSA加密
- `lxml>=4.9.0` - XML/HTML解析
- `Pillow>=9.0.0` - 图片处理
- `pyyaml>=6.0` - YAML配置文件解析
- `pyinstaller>=6.0.0` - 用于打包EXE

## 自动构建

项目使用 GitHub Actions 自动构建 EXE 文件。每次推送到 `master` 分支时，系统会自动：

1. 安装依赖
2. 创建配置文件
3. 使用 PyInstaller 打包 EXE
4. 上传构建产物

## 授权说明

项目包含授权工具，用于生成和管理许可证。授权工具位于 `授权工具/` 目录下，包含密钥生成和许可证创建功能。

## License

MIT License