# 配置有关的静态文件
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'gsm200818534',
        'HOST': '10.1.1.197',
        'PORT': '5432',
    }
}

securityCode = "rewcef10fSd08FDS3ADVTSSA"
CODE_ERROR = 400
CODE_SUCCESS = 200

# 树莓派测试环境
REDIS_HOST = "10.1.1.197"
REDIS_PORT = 6379
REDIS_PASSWORD = "gsm200818534"
REDIS_DB = 5

REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# 服务器代理
FRPS_IP = "8.134.128.64"
FRPS_PORT = 6000
MAX_WORKERS = 20
CONNECTION_TIMEOUT = 15
COMMAND_TIMEOUT = 15
CONFIG_FILE = "Common/config_frp.txt"

