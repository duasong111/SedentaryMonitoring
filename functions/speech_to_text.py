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


class SpeechToTextFunction:
    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            cls._model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        return cls._model

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
