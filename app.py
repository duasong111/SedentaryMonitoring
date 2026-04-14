from flask_socketio import emit
from Common.Response import create_response
from flask import Flask, request
from functions.user import LoginFunction, RegisterFunction
from functions.speech_to_text import SpeechToTextFunction
from functions.doubao import DoubaoFunction
from functions.text_to_speech import TextToSpeechFunction
from functions.device_time_static import DeviceTimeStaticFunction
from functions.sedentary_reminder import SedentaryReminderFunction
from functions.notification_settings import NotificationSettingsFunction
from functions.bark_settings import BarkSettingsFunction
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
device_time_static = DeviceTimeStaticFunction()
sedentary_reminder = SedentaryReminderFunction()
notification_settings = NotificationSettingsFunction()
bark_settings = BarkSettingsFunction()

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

        return tts_func.text_to_speech(text)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


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
        return tts_func.text_to_speech(text)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


@app.route("/api/tts_dou", methods=["POST"], strict_slashes=False)
def text_to_speech_dou():
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text or not text.strip():
            return create_response(HTTPStatus.BAD_REQUEST, "文本内容不能为空", False)

        from functions.doubao import DoubaoFunction
        doubao_func = DoubaoFunction()
        result = doubao_func.chat_with_doubao(text.strip())

        if not result:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, "豆包处理失败", False)

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
                    tts_func.text_to_speech(remind_info.get('reminder_text'))
        
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


if __name__ == '__main__':
    TextToSpeechFunction.start_tts_worker()
    TextToSpeechFunction.start_mqtt_thread()
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)