import os
import uuid
import subprocess
from flask_socketio import emit
from Common.Response import create_response
from flask import Flask, request
from functions.user import LoginFunction, RegisterFunction
from functions.speech_to_text import SpeechToTextFunction
from functions.doubao import DoubaoFunction
from functions.text_to_speech import TextToSpeechFunction, AUDIO_DIR, MAX_AUDIO_FILES
from functions.device_time_static import DeviceTimeStaticFunction
from functions.sedentary_reminder import SedentaryReminderFunction
from functions.notification_settings import NotificationSettingsFunction
from functions.bark_settings import BarkSettingsFunction
from functions.sedentary_daily_stats import SedentaryDailyStats
from functions.device_control import DeviceControlFunction
from functions.voice_clone import VoiceCloneFunction
from database.operateFunction import execuFunction
from flask_cors import CORS
from http import HTTPStatus

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

checkLogin = LoginFunction()
registerFunc = RegisterFunction()
db_function = execuFunction()
speech_to_text = SpeechToTextFunction()
doubao_func = DoubaoFunction()
tts_func = TextToSpeechFunction()
voice_clone = VoiceCloneFunction()
device_time_static = DeviceTimeStaticFunction()
sedentary_reminder = SedentaryReminderFunction()
notification_settings = NotificationSettingsFunction()
bark_settings = BarkSettingsFunction()
sedentary_daily_stats = SedentaryDailyStats()
device_control = DeviceControlFunction()

TextToSpeechFunction.start_tts_worker()
TextToSpeechFunction.start_mqtt_thread()

@app.route("/api/register/", methods=["POST"], strict_slashes=False)
def register():
    try:
        data = request.get_json()
        user = data.get('username')
        pwd = data.get('password')
        return registerFunc.register(user, pwd)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)

@app.route("/api/login/", methods=["POST"], strict_slashes=False)
def login():
    try:
        data = request.get_json()
        user = data.get('username')
        pwd = data.get('password')
        return checkLogin.checklogin(user, pwd)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


@app.route("/api/transcribe", methods=["POST"], strict_slashes=False)
def transcribe():
    try:
        audio_bytes = request.get_data()
        return speech_to_text.transcribe(audio_bytes)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# @app.route("/api/wake_detect", methods=["POST"], strict_slashes=False)
# def wake_detect():
#     try:
#         audio_bytes = request.get_data()
#         # 从查询参数获取 session_key，避免与 request.get_data() 冲突
#         session_key = request.args.get('session_key')
#
#         print(f"唤醒检测请求 - session_key: {session_key}")
#
#         # 调用唤醒检测
#         result = speech_to_text.wake_detect(audio_bytes, session_key=session_key)
#
#         # 获取响应数据
#         # result 是 (response_obj, status_code)
#         response_obj, status_code = result
#         response_data = response_obj.get_json()
#
#         if response_data and response_data.get('success'):
#             wake_data = response_data.get('data', {})
#
#             print(f"唤醒检测结果 - is_session_active: {wake_data.get('is_session_active')}, should_play_wake: {wake_data.get('should_play_wake')}")
#
#             # 检查是否需要播放唤醒提示语
#             if wake_data.get('should_play_wake'):
#                 # 播放"我在"提示音
#                 tts_func.text_to_speech("我在")
#             elif wake_data.get('is_session_active') and wake_data.get('text'):
#                 # 会话活跃且有文字，调用豆包API然后播放豆包回复
#                 text = wake_data.get('text')
#                 answer = doubao_func.chat_with_doubao(text)
#                 if answer:
#                     tts_func.text_to_speech(answer)
#
#         return result
#     except Exception as e:
#         return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)
#

@app.route("/api/transcribe_tts", methods=["POST"], strict_slashes=False)
def transcribe_tts():
    try:
        audio_bytes = request.get_data()
        if not audio_bytes:
            return create_response(HTTPStatus.BAD_REQUEST, "无音频数据", False)

        text, latency = speech_to_text._transcribe_text(audio_bytes)
        if not text:
            return create_response(HTTPStatus.BAD_REQUEST, "未识别到内容", False)

        device_id = request.args.get('device_id', '').strip() or None
        if device_id:
            synth_result = voice_clone.synthesize_now(device_id, text)
            status_code = HTTPStatus.OK if synth_result["success"] else HTTPStatus.INTERNAL_SERVER_ERROR
            return create_response(status_code, synth_result["message"], synth_result["success"], synth_result["data"])
        return tts_func.text_to_speech(text)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)

# ========== 接收 ESP32 上传的录音（保存为 MP3，顺便识别文字）==========
@app.route("/api/upload_audio", methods=["POST"], strict_slashes=False)
def upload_audio():
    try:
        audio_bytes = request.get_data()
        if not audio_bytes:
            return create_response(HTTPStatus.BAD_REQUEST, "无音频数据", False)

        # 可选 query: ?device_id=xxx&transcribe=1
        device_id       = request.args.get('device_id', '').strip() or None
        want_transcribe = request.args.get('transcribe', '1').lower() in ('1', 'true', 'yes')

        file_id  = str(uuid.uuid4())
        pcm_path = os.path.join(AUDIO_DIR, f"{file_id}_raw.pcm")
        mp3_path = os.path.join(AUDIO_DIR, f"{file_id}.mp3")

        # 1) 落盘原始 PCM（int16 LE 16kHz mono，ESP32 Flash 里 raw data 原样）
        with open(pcm_path, "wb") as f:
            f.write(audio_bytes)

        # 2) ffmpeg 转 MP3（22050Hz mono 48kbps，跟现有 TTS 一致风格）
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "s16le", "-ar", "16000", "-ac", "1",
                    "-i", pcm_path,
                    "-ar", "22050", "-ac", "1", "-b:a", "48k",
                    "-map_metadata", "-1",
                    "-codec:a", "libmp3lame",
                    mp3_path,
                ],
                check=True, capture_output=True, timeout=30,
            )
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode(errors="ignore") if e.stderr else ""
            if os.path.exists(pcm_path):
                os.remove(pcm_path)
            return create_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                f"MP3转码失败: {err[-200:]}", False,
            )

        # 删中间 pcm
        if os.path.exists(pcm_path):
            os.remove(pcm_path)

        if not os.path.exists(mp3_path):
            return create_response(
                HTTPStatus.INTERNAL_SERVER_ERROR, "MP3文件未生成", False,
            )

        size_mp3     = os.path.getsize(mp3_path)
        duration_sec = round(len(audio_bytes) / 2.0 / 16000.0, 2)

        # 3) 可选：顺便转文字（保留 ESP32 端识别体验）
        text    = None
        latency = 0
        if want_transcribe:
            text, latency = speech_to_text._transcribe_text(audio_bytes)
            if text:
                db_function.insert_text_stastic(text, 'upload_audio_transcribe', latency)

        # 4) 清理旧 mp3（保留最新 MAX_AUDIO_FILES 个）
        try:
            files = []
            for f in os.listdir(AUDIO_DIR):
                if f.endswith('.mp3'):
                    fp = os.path.join(AUDIO_DIR, f)
                    files.append((fp, os.path.getmtime(fp)))
            files.sort(key=lambda x: x[1], reverse=True)
            for fp, _ in files[MAX_AUDIO_FILES:]:
                try:
                    os.remove(fp)
                except Exception:
                    pass
        except Exception as e:
            print("[upload_audio] cleanup error:", e)

        return create_response(HTTPStatus.OK, "上传成功", True, data={
            "filename":     f"{file_id}.mp3",
            "size_bytes":   size_mp3,
            "duration_sec": duration_sec,
            "text":         text,
            "device_id":    device_id,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return create_response(
            HTTPStatus.INTERNAL_SERVER_ERROR, f"上传失败: {str(e)}", False,
        )


# 接入豆包
@app.route("/transcribe", methods=["POST"], strict_slashes=False)
def transcribe_dou_tts():
    try:
        audio_bytes = request.get_data()
        if not audio_bytes:
            return create_response(HTTPStatus.BAD_REQUEST, "无音频数据", False)

        text, latency = speech_to_text._transcribe_text(audio_bytes)
        if not text:
            return create_response(HTTPStatus.BAD_REQUEST, "未识别到内容", False)

        answer = doubao_func.chat_with_doubao(text)
        if not answer:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, "豆包处理失败", False)

        device_id = request.args.get('device_id', '').strip() or None
        if device_id:
            synth_result = voice_clone.synthesize_now(device_id, answer)
            status_code = HTTPStatus.OK if synth_result["success"] else HTTPStatus.INTERNAL_SERVER_ERROR
            return create_response(status_code, synth_result["message"], synth_result["success"], synth_result["data"])
        return tts_func.text_to_speech(answer)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


@app.route("/api/transcribe_dou", methods=["POST"], strict_slashes=False)
def transcribe_dou():
    try:
        audio_bytes = request.get_data()
        return doubao_func.transcribe_and_chat(audio_bytes)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


@app.route("/api/clear_history", methods=["POST"], strict_slashes=False)
def clear_history():
    try:
        return doubao_func.clear_history()
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)

# 使用文字转tts
@app.route("/api/tts", methods=["POST"], strict_slashes=False)
def text_to_speech():
    try:
        data = request.get_json()
        text = data.get('text', '')
        device_id = data.get('device_id', '').strip() or None
        if device_id:
            # 走克隆音色（内部已含降级逻辑）
            result = voice_clone.synthesize_now(device_id, text)
            status_code = HTTPStatus.OK if result["success"] else HTTPStatus.INTERNAL_SERVER_ERROR
            return create_response(status_code, result["message"], result["success"], result["data"])
        # 无 device_id → 维持原 edge-tts 行为
        return tts_func.text_to_speech(text)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


@app.route("/api/tts_dou", methods=["POST"], strict_slashes=False)
def text_to_speech_dou():
    try:
        data = request.get_json()
        text = data.get('text', '')
        device_id = data.get('device_id', '').strip() or None
        if not text or not text.strip():
            return create_response(HTTPStatus.BAD_REQUEST, "文本内容不能为空", False)

        from functions.doubao import DoubaoFunction
        doubao_func = DoubaoFunction()
        result = doubao_func.chat_with_doubao(text.strip())

        if not result:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, "豆包处理失败", False)

        if device_id:
            synth_result = voice_clone.synthesize_now(device_id, result)
            status_code = HTTPStatus.OK if synth_result["success"] else HTTPStatus.INTERNAL_SERVER_ERROR
            return create_response(status_code, synth_result["message"], synth_result["success"], synth_result["data"])
        return tts_func.text_to_speech(result)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)

# esp32 会下载我们的这个网址，然后再去进行播放
@app.route("/audio/<filename>", methods=["GET"], strict_slashes=False)
def serve_audio(filename):
    try:
        return tts_func.serve_audio(filename)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 设备时长统计接口
@app.route("/api/static_time", methods=["POST"], strict_slashes=False)
def static_time():
    try:
        data = request.get_json()
        result = device_time_static.process_device_event(data)

        # 如果需要提醒，播放语音
        response_obj, status_code = result
        response_data = response_obj.get_json()

        if response_data and response_data.get('success'):
            result_data = response_data.get('data', {})
            reminder_data = result_data.get('reminder', {})

            if reminder_data and reminder_data.get('success'):
                remind_info = reminder_data.get('data', {})
                if remind_info.get('need_remind') and remind_info.get('reminder_text'):
                    device_id = (data or {}).get('device_id') or remind_info.get('device_id')
                    reminder_text = remind_info.get('reminder_text')
                    if device_id:
                        voice_clone.synthesize_now(device_id, reminder_text)
                    else:
                        tts_func.text_to_speech(reminder_text)

        return result
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 获取设备统计数据
@app.route("/api/device_stats/<uuid>", methods=["GET"], strict_slashes=False)
def get_device_stats(uuid):
    try:
        return device_time_static.get_device_stats(uuid)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 获取久坐提醒设置
@app.route("/api/sedentary_settings/<device_id>", methods=["GET"], strict_slashes=False)
def get_sedentary_settings(device_id):
    try:
        return sedentary_reminder.get_settings(device_id)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 更新久坐提醒设置
@app.route("/api/sedentary_settings/<device_id>", methods=["POST"], strict_slashes=False)
def update_sedentary_settings(device_id):
    try:
        data = request.get_json()
        return sedentary_reminder.update_settings(device_id, data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)




# 获取久坐历史记录
@app.route("/api/sedentary_history", methods=["POST"], strict_slashes=False)
def get_sedentary_history():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        number = data.get('number', 10)
        return device_time_static.get_sedentary_history(device_id, number)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# Bark 推送接口
@app.route("/api/bark_notification", methods=["POST"], strict_slashes=False)
def bark_notification():
    try:
        from functions.bark_notice import bark_notice
        
        data = request.get_json()
        notification_type = data.get('type', 'normal')  # normal, simple, with_icon
        title = data.get('title', '')
        body = data.get('body', '')
        icon = data.get('icon', '')
        
        if notification_type == 'simple':
            # 简单通知（只有内容）
            if not body:
                return create_response(HTTPStatus.BAD_REQUEST, "内容不能为空", False)
            result = bark_notice.send_simple_notification(body)
        elif notification_type == 'with_icon':
            # 带图标通知
            if not title or not body or not icon:
                return create_response(HTTPStatus.BAD_REQUEST, "标题、内容和图标不能为空", False)
            result = bark_notice.send_notification_with_icon(title, body, icon)
        else:
            # 普通通知（带标题和内容）
            if not title or not body:
                return create_response(HTTPStatus.BAD_REQUEST, "标题和内容不能为空", False)
            result = bark_notice.send_notification(title, body, icon)
        
        if result.get('success'):
            return create_response(HTTPStatus.OK, result.get('message', '推送成功'), True)
        else:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, result.get('message', '推送失败'), False)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 获取通知设置
@app.route("/api/notification_settings/<device_id>", methods=["GET"], strict_slashes=False)
def get_notification_settings(device_id):
    try:
        return notification_settings.get_settings(device_id)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 更新通知设置
@app.route("/api/notification_settings/<device_id>", methods=["POST"], strict_slashes=False)
def update_notification_settings(device_id):
    try:
        data = request.get_json()
        return notification_settings.update_settings(device_id, data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 获取Bark通知设置
@app.route("/api/bark_settings/<device_id>", methods=["GET"], strict_slashes=False)
def get_bark_settings(device_id):
    try:
        return bark_settings.get_settings(device_id)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 更新Bark通知设置
@app.route("/api/bark_settings/<device_id>", methods=["POST"], strict_slashes=False)
def update_bark_settings(device_id):
    try:
        data = request.get_json()
        return bark_settings.update_settings(device_id, data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# ==================== 久坐每日统计 ====================

# ESP32 周期性上报久坐数据（每分钟）
@app.route("/api/sedentary_report", methods=["POST"], strict_slashes=False)
def sedentary_report():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        state = data.get('state', '无人')
        avg_distance_cm = data.get('avg_distance_cm', 0)
        max_distance_cm = data.get('max_distance_cm', 0)
        timestamp = data.get('timestamp')

        if not device_id:
            return create_response(HTTPStatus.BAD_REQUEST, "device_id 不能为空", False)
        if state not in ('有人', '无人'):
            return create_response(HTTPStatus.BAD_REQUEST, "state 必须为 '有人' 或 '无人'", False)

        result = sedentary_daily_stats.process_report(
            device_id=device_id,
            state=state,
            avg_distance_cm=avg_distance_cm,
            max_distance_cm=max_distance_cm,
            timestamp=timestamp
        )
        return create_response(HTTPStatus.OK, "上报成功", True, result)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 查询日统计
@app.route("/api/sedentary_daily/<device_id>", methods=["GET"], strict_slashes=False)
def get_sedentary_daily(device_id):
    try:
        date_str = request.args.get('date')  # 格式: 2026-05-30
        if not date_str:
            from datetime import date
            date_str = str(date.today())

        data = sedentary_daily_stats.get_daily_stats(device_id, date_str)
        return create_response(HTTPStatus.OK, "查询成功", True, data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 查询小时统计（某天24小时分布，前端画柱状图）
@app.route("/api/sedentary_hourly/<device_id>", methods=["GET"], strict_slashes=False)
def get_sedentary_hourly(device_id):
    try:
        date_str = request.args.get('date')  # 格式: 2026-05-30
        if not date_str:
            from datetime import date
            date_str = str(date.today())

        data = sedentary_daily_stats.get_hourly_stats(device_id, date_str)
        return create_response(HTTPStatus.OK, "查询成功", True, data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 查询周统计
@app.route("/api/sedentary_weekly/<device_id>", methods=["GET"], strict_slashes=False)
def get_sedentary_weekly(device_id):
    try:
        data = sedentary_daily_stats.get_weekly_stats(device_id)
        return create_response(HTTPStatus.OK, "查询成功", True, data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 查询月统计
@app.route("/api/sedentary_monthly/<device_id>", methods=["GET"], strict_slashes=False)
def get_sedentary_monthly(device_id):
    try:
        data = sedentary_daily_stats.get_monthly_stats(device_id)
        return create_response(HTTPStatus.OK, "查询成功", True, data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# ==================== 设备控制 ====================

# 获取可用LED模式列表
@app.route("/api/device_control/modes", methods=["GET"], strict_slashes=False)
def get_device_control_modes():
    try:
        return device_control.get_available_modes()
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 获取设备控制设置
@app.route("/api/device_control/<device_id>", methods=["GET"], strict_slashes=False)
def get_device_control_settings(device_id):
    try:
        return device_control.get_settings(device_id)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 更新设备控制设置
@app.route("/api/device_control/<device_id>", methods=["POST"], strict_slashes=False)
def update_device_control_settings(device_id):
    try:
        data = request.get_json()
        return device_control.update_settings(device_id, data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 测试发送控制命令（手动触发一次MQTT下发）
@app.route("/api/device_control/test/<device_id>", methods=["POST"], strict_slashes=False)
def test_device_control(device_id):
    try:
        data = request.get_json() or {}
        presence_duration = data.get('presence_duration', 1800)
        result = DeviceControlFunction.send_control_command(device_id, presence_duration)
        return create_response(HTTPStatus.OK, "测试命令已发送", True, result)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


@app.route("/api/device_control/direct/<device_id>", methods=["POST"])
def direct_device_control(device_id):
    try:
        data = request.get_json() or {}
        result = DeviceControlFunction.send_direct_control(
            device_id=device_id,
            led_mode=data.get('led_mode'),
            brightness=data.get('brightness', 2),
            interval_ms=data.get('interval_ms', 1000),
            byte_value=data.get('byte_value', 0),
            vibration_enabled=data.get('vibration_enabled', True),
            vibration_duration=data.get('vibration_duration', 500),
            vibration_interval=data.get('vibration_interval', 300)
        )
        
        if result["success"]:
            return create_response(HTTPStatus.OK, result["message"], True, result)
        else:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, result["message"], False)

    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(e), False)


# ==================== 音色克隆 ====================

# 查询音色档案
@app.route("/api/voice_clone/<device_id>", methods=["GET"], strict_slashes=False)
def get_voice_clone(device_id):
    try:
        return voice_clone.get_profile(device_id)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 注册音色（multipart 上传）
@app.route("/api/voice_clone/register", methods=["POST"], strict_slashes=False)
def register_voice_clone():
    try:
        device_id = request.form.get('device_id', '').strip()
        sample_text = request.form.get('sample_text', '').strip()
        if 'audio' not in request.files:
            return create_response(HTTPStatus.BAD_REQUEST, "缺少 audio 文件", False)
        audio_file = request.files['audio']
        return voice_clone.register_voice(device_id, audio_file.read(), audio_file.mimetype, sample_text)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 同步合成（带 device_id 走克隆，未注册则降级）
@app.route("/api/voice_clone/synthesize", methods=["POST"], strict_slashes=False)
def synthesize_voice_clone():
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', '').strip() or None
        text = data.get('text', '')
        result = voice_clone.synthesize_now(device_id, text)
        status_code = HTTPStatus.OK if result["success"] else HTTPStatus.INTERNAL_SERVER_ERROR
        return create_response(status_code, result["message"], result["success"], result["data"])
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 软删除（停用）
@app.route("/api/voice_clone/<device_id>", methods=["DELETE"], strict_slashes=False)
def delete_voice_clone(device_id):
    try:
        return voice_clone.delete_voice(device_id)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


if __name__ == '__main__':
    TextToSpeechFunction.start_tts_worker()
    TextToSpeechFunction.start_mqtt_thread()
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)