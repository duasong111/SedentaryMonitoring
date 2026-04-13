import numpy as np
import time
import warnings
from faster_whisper import WhisperModel
from http import HTTPStatus
from Common.Response import create_response
from database.operateFunction import execuFunction

# 初始化数据库操作实例
db_exec = execuFunction()

warnings.filterwarnings("ignore", category=RuntimeWarning)

MODEL_SIZE = "small"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# # 会话超时时间（秒）
# SESSION_TIMEOUT = 120  # 2分钟内不需要唤醒词

# # 会话状态管理
# _sessions = {}
# _session_lock = __import__('threading').Lock()


class SpeechToTextFunction:
    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            cls._model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        return cls._model

    # @classmethod
    # def _is_session_active(cls, session_key):
    #     """检查会话是否活跃"""
    #     with _session_lock:
    #         if session_key in _sessions:
    #             last_time = _sessions[session_key]
    #             if time.time() - last_time < SESSION_TIMEOUT:
    #                 # 更新会话时间
    #                 _sessions[session_key] = time.time()
    #                 return True
    #             else:
    #                 # 会话超时，移除
    #                 del _sessions[session_key]
    #     return False

    # @classmethod
    # def _start_session(cls, session_key):
    #     """开始新会话"""
    #     with _session_lock:
    #         _sessions[session_key] = time.time()

    # @classmethod
    # def _clear_inactive_sessions(cls):
    #     """清理不活跃的会话"""
    #     current_time = time.time()
    #     with _session_lock:
    #         keys_to_remove = []
    #         for key, last_time in _sessions.items():
    #             if current_time - last_time > SESSION_TIMEOUT:
    #                 keys_to_remove.append(key)
    #         for key in keys_to_remove:
    #             del _sessions[key]

    def _transcribe_text(self, audio_bytes):
        if not audio_bytes:
            return None, 0

        start = time.time()
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        model = self._get_model()
        segments, _ = model.transcribe(
            audio_np,
            language="zh",
            beam_size=5,
            vad_filter=True,
            word_timestamps=False
        )
        text = " ".join(s.text for s in segments).strip()
        latency = round((time.time() - start) * 1000, 2)
        print(f"语音转文字 [{latency}ms]: {text}")
        return text, latency

    def transcribe(self, audio_bytes):
        try:
            if not audio_bytes:
                return create_response(HTTPStatus.BAD_REQUEST, "无音频数据", False)

            text, latency = self._transcribe_text(audio_bytes)

            if not text:
                return create_response(HTTPStatus.BAD_REQUEST, "未识别到内容", False)

            # 记录统计数据
            db_exec.insert_text_stastic(text, 'speech_to_text', latency)

            return create_response(
                HTTPStatus.OK,
                "语音转文字成功",
                True,
                data={
                    "text": text,
                    "latency_ms": latency
                }
            )

        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"语音转文字失败: {str(e)}", False)

    # def wake_detect(self, audio_bytes, wake_words=None, session_key=None):
    #     """唤醒词检测
    #     
    #     Args:
    #         audio_bytes: 音频数据
    #         wake_words: 唤醒词列表
    #         session_key: 会话标识符（如设备ID或UUID）
    #         
    #     Returns:
    #         response: 包含唤醒结果和会话状态
    #     """
    #     try:
    #         if not audio_bytes:
    #             return create_response(HTTPStatus.BAD_REQUEST, "无音频数据", False)
    # 
    #         # 默认唤醒词列表（包含谐音防误识别）
    #         if wake_words is None:
    #             wake_words = ["大炮", "大跑", "达炮", "打炮", "搭炮"]
    # 
    #         # 转录音频
    #         text, latency = self._transcribe_text(audio_bytes)
    # 
    #         # 检查会话是否活跃
    #         is_session_active = False
    #         if session_key:
    #             is_session_active = self._is_session_active(session_key)
    # 
    #         woke = False
    #         should_play_wake = False
    # 
    #         if text:
    #             if is_session_active:
    #                 # 会话活跃，不需要唤醒词
    #                 woke = True
    #                 print(f"会话活跃: '{text}' → ✅已在会话中")
    #             else:
    #                 # 判断是否包含唤醒词
    #                 woke = any(w in text for w in wake_words)
    #                 if woke:
    #                     # 唤醒成功，开始新会话
    #                     if session_key:
    #                         self._start_session(session_key)
    #                     should_play_wake = True
    #                     print(f"唤醒检测: '{text}' → ✅唤醒")
    #                 else:
    #                     print(f"唤醒检测: '{text}' → ❌未唤醒")
    # 
    #         # 记录统计数据
    #         if text:
    #             db_exec.insert_text_stastic(text, 'wake_detect', latency)
    # 
    #         return create_response(
    #             HTTPStatus.OK,
    #             "唤醒检测完成",
    #             True,
    #             data={
    #                 "wake": woke,
    #                 "text": text,
    #                 "latency_ms": latency,
    #                 "is_session_active": is_session_active,
    #                 "should_play_wake": should_play_wake
    #             }
    #         )
    # 
    #     except Exception as e:
    #         return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"唤醒检测失败: {str(e)}", False)
