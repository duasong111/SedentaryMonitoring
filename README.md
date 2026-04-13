# 久坐监测系统后端

一个基于 Flask 的智能语音交互和设备监测系统后端。

## 功能特性

### 1. 用户管理
- 用户注册
- 用户登录

### 2. 语音识别
- 语音转文字（Whisper）
- 语音识别后直接播放
- 语音识别 + 豆包对话 + 播放

### 3. 语音合成
- 文字转语音（Edge TTS）
- MQTT 消息驱动
- 音频缓存优化

### 4. 豆包对话
- 语音识别 + 豆包对话
- 文字输入 + 豆包对话
- 对话历史保留

### 5. 设备监测
- 设备时长统计（有人/无人）
- 设备数据上报

## 项目结构

```
SedentaryMonitoring/
├── app.py                 # 主应用入口
├── config.py              # 配置文件
├── Common/
│   └── Response.py        # 统一响应格式
├── database/
│   ├── Postgresql.py      # PostgreSQL 连接
│   └── operateFunction.py # 数据库操作
├── functions/
│   ├── user.py            # 用户功能
│   ├── speech_to_text.py  # 语音转文字
│   ├── doubao.py          # 豆包对话
│   ├── text_to_speech.py  # 文字转语音
│   └── device_time_static.py  # 设备时长统计
├── migrations/
│   ├── user_table.py      # 用户表初始化
│   ├── user_text_stastic.py  # 文本统计表初始化
│   └── device_time_static.py  # 设备时间表初始化
└── audio/                 # 音频文件存储
```

## 环境要求

- Python 3.9+
- PostgreSQL 12+
- ffmpeg（音频处理）

## 安装依赖

```bash
pip install flask flask-cors flask-socketio psycopg2-binary faster-whisper numpy edge-tts paho-mqtt requests
```

**安装 ffmpeg：**
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`

## 配置说明

编辑 `config.py` 文件配置：

```python
# 数据库配置
DATABASES = {
    'default': {
        'NAME': '数据库名',
        'USER': '用户名',
        'PASSWORD': '密码',
        'HOST': '主机地址',
        'PORT': '端口',
    }
}

# MQTT 配置
MQTT_BROKER = "MQTT Broker 地址"
MQTT_PORT = 1883
MQTT_USER = "用户名"
MQTT_PASS = "密码"

# 豆包配置
DOUBAO_API_KEY = "你的 API Key"
DOUBAO_MODEL = "模型名称"

# TTS 配置
LOCAL_IP = "本机 IP"
LOCAL_PORT = 5001
```

## 初始化数据库

```bash
# 创建用户表
python migrations/user_table.py

# 创建文本统计表
python migrations/user_text_stastic.py

# 创建设备时间表
python migrations/device_time_static.py
```

## 运行项目

```bash
python app.py
```

或使用 Flask CLI：

```bash
flask run --host=0.0.0.0 --port=5001
```

## API 接口

### 用户相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/register/` | POST | 用户注册 |
| `/api/login/` | POST | 用户登录 |

### 语音识别相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/transcribe` | POST | 语音转文字 |
| `/api/transcribe_tts` | POST | 语音转文字 + 播放 |
| `/api/transcribe_dou` | POST | 语音转文字 + 豆包对话 |
| `/api/transcribe_dou_tts` | POST | 语音转文字 + 豆包对话 + 播放 |

### 语音合成相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/tts` | POST | 文字转语音 |
| `/api/tts_dou` | POST | 文字 + 豆包对话 + 播放 |
| `/audio/<filename>` | GET | 获取音频文件 |

### 豆包对话相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/clear_history` | POST | 清空对话历史 |

### 设备监测相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/static_time` | POST | 上报设备数据 |
| `/api/device_stats/<uuid_or_device_id>` | GET | 获取设备统计 |

## API 使用示例

### 1. 用户注册

```bash
curl -X POST http://localhost:5001/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'
```

### 2. 语音转文字

```bash
curl -X POST http://localhost:5001/api/transcribe \
  --data-binary @audio.raw
```

### 3. 文字转语音

```bash
curl -X POST http://localhost:5001/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，很高兴认识你"}'
```

### 4. 设备数据上报

```bash
curl -X POST http://localhost:5001/api/static_time \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "esp32_001",
    "uuid": "session-001",
    "state": "有人",
    "distance_cm": 50,
    "timestamp": 1712937600
  }'
```

### 5. 获取设备统计

```bash
curl http://localhost:5001/api/device_stats/esp32_001
```

## MQTT 使用

### 订阅主题
- `control/esp32`：接收设备控制指令

### 发布主题
- `devices/esp32_001/control`：发送播放指令

### 消息格式

**TTS 播放指令：**
```json
{
  "type": "play",
  "url": "http://192.168.18.210:5001/audio/xxx.mp3"
}
```

**设备状态上报（设备发送）：**
```json
{
  "device_id": "esp32_001",
  "uuid": "session-001",
  "state": "有人",
  "distance_cm": 50,
  "timestamp": 1712937600
}
```

## 注意事项

1. 确保 PostgreSQL 数据库已启动并可连接
2. 确保 MQTT Broker 可访问
3. 确保 ffmpeg 已正确安装
4. 音频文件最多保留 20 个，自动清理旧文件
5. 设备时长统计同一 uuid 只更新记录，不插入新记录

## 许可证

MIT License
