# 配置有关的静态文件
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'SedentaryMonitoring',
        'USER': 'postgres',
        'PASSWORD': 'gsm200818534',
        'HOST': '192.168.18.204',
        'PORT': '5432',
    }
}


# 树莓派测试环境
REDIS_HOST = "192.168.18.204"
REDIS_PORT = 6379
REDIS_PASSWORD = "gsm200818534"
REDIS_DB = 5

REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# MQTT配置
MQTT_BROKER = "60.205.140.163"
MQTT_PORT = 1883
MQTT_USER = "admin"
MQTT_PASS = "password"
SUB_TOPIC = "control/esp32"
PUB_TOPIC = "devices/esp32_001/control"

# 豆包配置
DOUBAO_API_KEY = "ecc1665a-1a3c-4a3f-a92a-3bce10398509"
DOUBAO_MODEL = "doubao-seed-2-0-lite-260215"
DOUBAO_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_SYSTEM = "你是一个可以聊天的朋友，回答问题比较简洁。不要使用表情"

# TTS配置
LOCAL_IP = "192.168.18.210"
LOCAL_PORT = 5001
TTS_VOICE = "zh-CN-XiaoyiNeural"

# 久坐提醒配置
DEFAULT_SEDENTARY_THRESHOLD = 1800
DEFAULT_REMINDER_INTERVAL = 300
DEFAULT_REMINDER_VOICE = "您已经久坐了，起来活动一下吧"
DEFAULT_VOICE_LIST = [
    "您已经久坐了，起来活动一下吧",
    "休息一下，站一会儿吧",
    "久坐有害健康，去喝杯水吧",
    "动一动，身体更健康",
    "该休息了，拉伸一下吧"
]

# Bark 推送配置
BARK_DEVICE_KEY = "NHoXrpKTK482FwxHkN8WmG"  # 替换为你的Bark设备密钥

# Bark 通知默认配置
DEFAULT_BARK_SEDENTARY_THRESHOLD = 3600  # 60分钟
DEFAULT_BARK_REMINDER_INTERVAL = 600  # 10分钟
DEFAULT_BARK_VOICE = "您已经久坐了，请注意休息"

