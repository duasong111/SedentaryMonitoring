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
DOUBAO_SYSTEM = "你是一个可以聊天的朋友，回答问题比较简洁。"

# TTS配置
LOCAL_IP = "192.168.18.210"
LOCAL_PORT = 5001
TTS_VOICE = "zh-CN-XiaoyiNeural"

