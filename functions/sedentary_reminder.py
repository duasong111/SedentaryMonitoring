import json
import time
import redis
from http import HTTPStatus
from Common.Response import create_response
from database.operateFunction import execuFunction
from config import (
    DEFAULT_SEDENTARY_THRESHOLD,
    DEFAULT_REMINDER_INTERVAL,
    DEFAULT_REMINDER_VOICE,
    DEFAULT_VOICE_LIST,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_DB
)

db_exec = execuFunction()

# 初始化 Redis 连接
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=REDIS_DB,
    decode_responses=True
)

# 延迟导入，避免循环导入
def get_bark_notice():
    from functions.bark_notice import bark_notice
    return bark_notice

def get_tts_func():
    from functions.text_to_speech import TextToSpeechFunction
    return TextToSpeechFunction()


class SedentaryReminderFunction:
    def _get_default_settings(self, device_id):
        """获取默认设置"""
        return {
            'device_id': device_id,
            'sedentary_threshold': DEFAULT_SEDENTARY_THRESHOLD,
            'reminder_interval': DEFAULT_REMINDER_INTERVAL,
            'reminder_voice': DEFAULT_REMINDER_VOICE,
            'voice_list': DEFAULT_VOICE_LIST,
            'is_enabled': True
        }

    def _fill_default_values(self, settings, device_id):
        """填充默认值"""
        if not settings:
            return self._get_default_settings(device_id)
        
        # 填充默认值
        if settings.get('reminder_voice') is None:
            settings['reminder_voice'] = DEFAULT_REMINDER_VOICE
        
        if settings.get('voice_list') is None:
            settings['voice_list'] = DEFAULT_VOICE_LIST
        else:
            # 解析 voice_list
            try:
                if isinstance(settings['voice_list'], str):
                    settings['voice_list'] = json.loads(settings['voice_list'])
            except:
                settings['voice_list'] = DEFAULT_VOICE_LIST
        
        if settings.get('is_enabled') is None:
            settings['is_enabled'] = True
        
        return settings

    def get_settings(self, device_id):
        """获取设备提醒设置"""
        try:
            if not device_id:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id不能为空", False)

            settings = db_exec.get_sedentary_reminder_settings(device_id)
            
            # 填充默认值
            settings = self._fill_default_values(settings, device_id)

            return create_response(
                HTTPStatus.OK,
                "获取设置成功",
                True,
                data=settings
            )
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"获取失败: {str(e)}", False)

    def _clear_voice_cache(self, device_id):
        """清除语音消息缓存"""
        try:
            cache_key = f"sedentary_voice:{device_id}"
            redis_client.delete(cache_key)
            print(f"清除设备 {device_id} 的语音缓存")
        except Exception as e:
            print(f"清除缓存失败: {e}")

    def update_settings(self, device_id, data):
        """更新提醒设置"""
        try:
            if not device_id:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id不能为空", False)

            sedentary_threshold = data.get('sedentary_threshold')
            reminder_interval = data.get('reminder_interval')
            reminder_voice = data.get('reminder_voice')
            voice_list = data.get('voice_list')
            is_enabled = data.get('is_enabled')

            # 验证参数
            if sedentary_threshold is not None and sedentary_threshold <= 0:
                return create_response(HTTPStatus.BAD_REQUEST, "久坐阈值必须大于0", False)
            if reminder_interval is not None and reminder_interval <= 0:
                return create_response(HTTPStatus.BAD_REQUEST, "提醒间隔必须大于0", False)

            # 转换 voice_list 为 JSON 字符串
            voice_list_str = None
            if voice_list is not None:
                if isinstance(voice_list, list):
                    voice_list_str = json.dumps(voice_list, ensure_ascii=False)
                else:
                    return create_response(HTTPStatus.BAD_REQUEST, "voice_list必须是数组", False)

            result = db_exec.create_or_update_sedentary_settings(
                device_id,
                sedentary_threshold=sedentary_threshold,
                reminder_interval=reminder_interval,
                reminder_voice=reminder_voice,
                voice_list=voice_list_str,
                is_enabled=is_enabled
            )

            if not result.get('success'):
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, result.get('message', '更新失败'), False)

            # 清除语音消息缓存，确保新设置立即生效
            self._clear_voice_cache(device_id)

            # 填充默认值后返回
            settings = result.get('data')
            settings = self._fill_default_values(settings, device_id)

            return create_response(
                HTTPStatus.OK,
                "更新设置成功",
                True,
                data=settings
            )
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"更新失败: {str(e)}", False)

    def _get_cached_voice(self, device_id):
        """从 Redis 获取缓存的语音消息"""
        try:
            cache_key = f"sedentary_voice:{device_id}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"Redis 获取缓存失败: {e}")
        return None

    def _cache_voice(self, device_id, voice_data):
        """缓存语音消息到 Redis"""
        try:
            cache_key = f"sedentary_voice:{device_id}"
            # 缓存 5 分钟
            redis_client.setex(cache_key, 300, json.dumps(voice_data, ensure_ascii=False))
        except Exception as e:
            print(f"Redis 缓存失败: {e}")

    def check_and_remind(self, device_id, uuid, presence_duration):
        """检查是否需要提醒"""
        try:
            if not device_id or not uuid:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id和uuid不能为空", False)

            # 获取通知设置
            notification_settings = db_exec.get_notification_settings(device_id)
            enable_voice = True
            enable_bark = True
            
            if notification_settings:
                enable_voice = notification_settings.get('enable_voice', True)
                enable_bark = notification_settings.get('enable_bark', True)

            # 如果都不启用，直接返回
            if not enable_voice and not enable_bark:
                return create_response(
                    HTTPStatus.OK,
                    "通知功能未启用",
                    True,
                    data={'need_remind': False}
                )

            # 获取声音通知设置
            voice_settings = db_exec.get_sedentary_reminder_settings(device_id)
            voice_settings = self._fill_default_values(voice_settings, device_id)

            # 获取Bark通知设置
            from database.operateFunction import execuFunction
            db_exec_local = execuFunction()
            bark_settings = db_exec_local.get_bark_settings(device_id)
            
            # 填充Bark默认值
            from config import DEFAULT_BARK_SEDENTARY_THRESHOLD, DEFAULT_BARK_REMINDER_INTERVAL, DEFAULT_BARK_VOICE
            if not bark_settings:
                bark_settings = {
                    'bark_sedentary_threshold': DEFAULT_BARK_SEDENTARY_THRESHOLD,
                    'bark_reminder_interval': DEFAULT_BARK_REMINDER_INTERVAL,
                    'bark_voice': DEFAULT_BARK_VOICE
                }

            # 检查声音通知
            need_voice_reminder = False
            if enable_voice:
                voice_threshold = voice_settings.get('sedentary_threshold', DEFAULT_SEDENTARY_THRESHOLD)
                voice_interval = voice_settings.get('reminder_interval', DEFAULT_REMINDER_INTERVAL)
                
                if presence_duration >= voice_threshold:
                    # 检查声音通知间隔
                    last_voice_remind = db_exec_local.get_last_reminder_time(device_id)
                    if not last_voice_remind:
                        need_voice_reminder = True
                    else:
                        time_since_voice = time.time() - last_voice_remind.timestamp()
                        if time_since_voice >= voice_interval:
                            need_voice_reminder = True

            # 检查Bark通知
            need_bark_reminder = False
            if enable_bark:
                bark_threshold = bark_settings.get('bark_sedentary_threshold', DEFAULT_BARK_SEDENTARY_THRESHOLD)
                bark_interval = bark_settings.get('bark_reminder_interval', DEFAULT_BARK_REMINDER_INTERVAL)
                
                if presence_duration >= bark_threshold:
                    # 检查Bark通知间隔
                    last_bark_remind = db_exec_local.get_last_reminder_time(device_id)
                    if not last_bark_remind:
                        need_bark_reminder = True
                    else:
                        time_since_bark = time.time() - last_bark_remind.timestamp()
                        if time_since_bark >= bark_interval:
                            need_bark_reminder = True

            # 如果都不需要提醒，返回
            if not need_voice_reminder and not need_bark_reminder:
                return create_response(
                    HTTPStatus.OK,
                    "未达到提醒条件",
                    True,
                    data={'need_remind': False}
                )

            # 准备提醒内容
            voice_reminder_text = None
            bark_reminder_text = None

            # 处理声音提醒
            if need_voice_reminder:
                # 尝试从 Redis 缓存获取语音消息
                cached_voice = self._get_cached_voice(device_id)
                
                if cached_voice:
                    # 使用缓存的语音消息
                    voice_reminder_text = cached_voice.get('reminder_text')
                    print(f"使用缓存的语音消息: {voice_reminder_text}")
                else:
                    # 选择提醒语音（优先级：自定义语音 > 语音列表 > 默认语音）
                    voice_reminder_text = voice_settings.get('reminder_voice')
                    voice_list = voice_settings.get('voice_list', DEFAULT_VOICE_LIST)

                    # 如果没有设置自定义语音，从列表中随机选择
                    if not voice_reminder_text and voice_list and len(voice_list) > 0:
                        import random
                        voice_reminder_text = random.choice(voice_list)
                    
                    # 如果还是没有，使用默认语音
                    if not voice_reminder_text:
                        voice_reminder_text = DEFAULT_REMINDER_VOICE

                    # 缓存语音消息
                    self._cache_voice(device_id, {
                        'reminder_text': voice_reminder_text,
                        'device_id': device_id,
                        'timestamp': time.time()
                    })
                    print(f"生成新的语音消息并缓存: {voice_reminder_text}")

            # 处理Bark提醒
            if need_bark_reminder:
                bark_reminder_text = bark_settings.get('bark_voice', DEFAULT_BARK_VOICE)

            # 插入提醒记录
            if need_voice_reminder or need_bark_reminder:
                reminder_text = voice_reminder_text or bark_reminder_text
                db_exec.insert_sedentary_reminder_record(
                    device_id, uuid, presence_duration, reminder_text, reminder_text
                )

            # 根据通知设置发送提醒
            if need_voice_reminder:
                try:
                    tts_func = get_tts_func()
                    tts_func.text_to_speech(voice_reminder_text)
                    print(f"播放语音提醒: {voice_reminder_text}")
                except Exception as e:
                    print(f"播放语音失败: {e}")

            if need_bark_reminder:
                try:
                    bark_notice = get_bark_notice()
                    bark_result = bark_notice.send_notification(
                        "久坐提醒",
                        f"您已经久坐{presence_duration}秒了，{bark_reminder_text}"
                    )
                    if bark_result.get('success'):
                        print("Bark 推送成功")
                    else:
                        print(f"Bark 推送失败: {bark_result.get('message')}")
                except Exception as e:
                    print(f"Bark 推送失败: {e}")

            return create_response(
                HTTPStatus.OK,
                "需要提醒",
                True,
                data={
                    'need_remind': True,
                    'voice_reminder_text': voice_reminder_text,
                    'bark_reminder_text': bark_reminder_text,
                    'sedentary_duration': presence_duration,
                    'notification_settings': {
                        'enable_voice': enable_voice,
                        'enable_bark': enable_bark,
                        'need_voice_reminder': need_voice_reminder,
                        'need_bark_reminder': need_bark_reminder
                    }
                }
            )
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"检查失败: {str(e)}", False)
