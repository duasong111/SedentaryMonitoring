import time
import requests
import warnings
import numpy as np
from faster_whisper import WhisperModel
from http import HTTPStatus
from Common.Response import create_response
from config import DOUBAO_API_KEY, DOUBAO_MODEL, DOUBAO_URL, DOUBAO_SYSTEM
from database.operateFunction import execuFunction

# 初始化数据库操作实例
db_exec = execuFunction()

warnings.filterwarnings("ignore", category=RuntimeWarning)

MODEL_SIZE = "small"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"


class DoubaoFunction:
    _model = None
    _conversation_history = []

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            cls._model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        return cls._model

    def _transcribe_audio(self, audio_bytes):
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
        print(f"语音识别 [{latency}ms]: {text}")
        return text, latency

    def chat_with_doubao(self, user_text):
        DoubaoFunction._conversation_history.append({"role": "user", "content": user_text})

        if len(DoubaoFunction._conversation_history) > 10:
            DoubaoFunction._conversation_history = DoubaoFunction._conversation_history[-10:]

        messages = [{"role": "system", "content": DOUBAO_SYSTEM}] + DoubaoFunction._conversation_history

        try:
            resp = requests.post(
                DOUBAO_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {DOUBAO_API_KEY}"
                },
                json={"model": DOUBAO_MODEL, "messages": messages},
                timeout=15
            )
            result = resp.json()
            answer = result["choices"][0]["message"]["content"]
            DoubaoFunction._conversation_history.append({"role": "assistant", "content": answer})
            return answer
        except Exception as e:
            return None

    def transcribe_and_chat(self, audio_bytes):
        try:
            if not audio_bytes:
                return create_response(HTTPStatus.BAD_REQUEST, "无音频数据", False)

            stt_text, stt_latency = self._transcribe_audio(audio_bytes)

            if not stt_text:
                return create_response(HTTPStatus.BAD_REQUEST, "未识别到内容", False)

            doubao_start = time.time()
            answer = self.chat_with_doubao(stt_text)
            doubao_latency = round((time.time() - doubao_start) * 1000, 2)

            if not answer:
                answer = "抱歉，我现在无法回答。"

            # 记录统计数据
            db_exec.insert_text_stastic(stt_text, 'speech_to_text', stt_latency)
            db_exec.insert_text_stastic(answer, 'doubao_chat', doubao_latency)

            return create_response(
                HTTPStatus.OK,
                "处理成功",
                True,
                data={
                    "stt_text": stt_text,
                    "answer": answer,
                    "stt_latency_ms": stt_latency,
                    "doubao_latency_ms": doubao_latency
                }
            )

        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"处理失败: {str(e)}", False)

    def clear_history(self):
        DoubaoFunction._conversation_history = []
        return create_response(HTTPStatus.OK, "对话历史已清空", True)
