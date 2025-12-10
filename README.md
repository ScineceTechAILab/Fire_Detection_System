# 🔥 Fire Detection System (基于 YOLO 的火灾检测系统)

这是一个基于 **Python** 和 **YOLOv8** 开发的实时火灾检测系统。
当系统通过摄像头检测到火焰或烟雾时，会自动触发报警逻辑，通过 **飞书群机器人** 和 **SMS 短信/电话** 通知相关人员，并自动保存现场截图作为证据。

## 📂 项目结构说明

本项目采用模块化设计，目录结构如下：

```text
FireDetectionSystem/
├── .venv/                 # Python 虚拟环境 (自动生成，勿动)
├── core/                  # 核心业务逻辑包
│   ├── communication/     # 📡 通信模块 (负责对外发送信息)
│   │   ├── feishu.py      # [待实现] 飞书 Webhook 报警逻辑
│   │   └── sms.py         # [待实现] 短信/电话 API 调用逻辑
│   └── yolo/              # 👁️ 视觉模块 (负责识别)
│       └── detector.py    # [待实现] YOLO 模型加载与推理逻辑
├── output/                # 💾 结果保存
│   └── captured_imgs/     # 存放检测到火灾时的自动截图
├── utils/                 # 🛠️ 通用工具包
│   └── logger.py          # [可选] 日志记录工具
├── weights/               # 🧠 模型权重文件
│   └── best.pt            # [必需] 训练好的 YOLO 火灾检测模型
├── .env                   # 🔐 环境变量 (存放 API Key 等敏感信息)
├── .gitignore             # Git 忽略配置
├── config.py              # ⚙️ 全局配置文件 (阈值、开关等)
├── main.py                # 🚀 程序主入口
└── requirements.txt       # 📦 项目依赖列表
```

## 🛠️ 环境准备

### 1. 安装依赖
请确保你已经激活了虚拟环境（PyCharm 默认会自动激活），然后在终端运行：

```bash
pip install -r requirements.txt
```

> **建议的 `requirements.txt` 内容：**
> ```text
> ultralytics
> opencv-python
> requests
> python-dotenv
> ```

### 2. 准备模型
你需要将训练好的 YOLO 模型文件（通常是 `.pt` 后缀）放入 `weights/` 文件夹中。
*   如果没有自训练模型，可以暂时使用 YOLOv8 官方模型测试：`yolov8n.pt`。

## ⚙️ 配置说明

### 1. 敏感信息配置 (.env)
在项目根目录创建一个名为 `.env` 的文件（**不要**上传到 GitHub），填入以下内容：

```ini
# 飞书机器人 Webhook 地址
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx

# 短信服务商配置 (以阿里云/腾讯云或你的服务商为准)
SMS_API_KEY=your_api_key_here
SMS_API_SECRET=your_api_secret_here
```

### 2. 参数调整 (config.py)
在 `config.py` 中调整系统运行参数：

```python
# 检测置信度阈值 (0.0 - 1.0)，越高越严格
CONFIDENCE_THRESHOLD = 0.5

# 报警冷却时间 (秒)，防止短时间内连续发送报警
ALERT_INTERVAL = 60

# 摄像头索引 (0 通常为本机自带，1 为外接 USB)
CAMERA_INDEX = 0
```

## 🚀 如何运行

在配置好环境和参数后，运行 `main.py` 启动系统：

```bash
python main.py
```

按键盘上的 **`q`** 键可退出程序。

## 📝 开发计划 (To-Do List)

- [ ] **Step 1**: 完成 `requirements.txt` 安装依赖。
- [ ] **Step 2**: 编写 `core/yolo/detector.py`，实现调用摄像头并显示画面。
- [ ] **Step 3**: 集成 YOLO 模型，在画面上画出检测框。
- [ ] **Step 4**: 编写 `core/communication`，打通飞书和短信接口。
- [ ] **Step 5**: 在 `main.py` 中整合逻辑：`检测 -> 判断 -> 报警`。

## ⚠️ 注意事项

*   **测试报警功能时**，请务必先将 `config.py` 中的 `ALERT_INTERVAL` 设置长一点，以免耗尽短信额度或造成骚扰。
*   `output/` 文件夹中的图片会随时间增加，建议定期清理。
