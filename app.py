from flask_socketio import emit
from Common.Response import create_response
from flask import Flask, request
from functions.user import LoginFunction, RegisterFunction
from functions.speech_to_text import SpeechToTextFunction
from functions.doubao import DoubaoFunction
from functions.text_to_speech import TextToSpeechFunction
from functions.device_time_static import DeviceTimeStaticFunction
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
        return device_time_static.process_device_event(data)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)


# 获取设备统计数据
@app.route("/api/device_stats/<uuid>", methods=["GET"], strict_slashes=False)
def get_device_stats(uuid):
    try:
        return device_time_static.get_device_stats(uuid)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)




if __name__ == '__main__':
    TextToSpeechFunction.start_tts_worker()
    TextToSpeechFunction.start_mqtt_thread()
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)