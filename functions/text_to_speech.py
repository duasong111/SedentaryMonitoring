import os
import uuid
import asyncio
import json
import hashlib
import threading
import queue
import edge_tts
import paho.mqtt.client as mqtt
from http import HTTPStatus
from Common.Response import create_response
from config import MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASS, SUB_TOPIC, PUB_TOPIC, LOCAL_IP, LOCAL_PORT, TTS_VOICE
from database.operateFunction import execuFunction

# 初始化数据库操作实例
db_exec = execuFunction()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

MAX_AUDIO_FILES = 20

tts_queue = queue.Queue()
mqtt_client_ref = None
audio_cache = {}


def _cleanup_old_audio():
    try:
        files = []
        for f in os.listdir(AUDIO_DIR):
            if f.endswith('.mp3'):
                filepath = os.path.join(AUDIO_DIR, f)
                files.append((filepath, os.path.getmtime(filepath)))

        files.sort(key=lambda x: x[1], reverse=True)

        for filepath, _ in files[MAX_AUDIO_FILES:]:
            try:
                os.remove(filepath)
                print("清理旧音频:", filepath)
            except Exception as e:
                print("清理失败:", e)

    except Exception as e:
        print("清理音频出错:", e)


def _get_text_hash(text):
    return hashlib.md5(text.encode()).hexdigest()


class TextToSpeechFunction:

    @staticmethod
    async def _generate_tts_fast(text, filepath):
        communicate = edge_tts.Communicate(text=text, voice=TTS_VOICE)
        await communicate.save(filepath)

    @staticmethod
    async def _compress_audio_async(input_path, output_path):
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", input_path,
            "-ar", "22050",
            "-ac", "1",
            "-b:a", "48k",
            "-map_metadata", "-1",
            "-af", "volume=0.6",
            "-codec:a", "libmp3lame",
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode != 0:
            raise Exception("音频压缩失败")

    @staticmethod
    def _tts_worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            task = tts_queue.get()
            try:
                text = task["text"]
                text_hash = _get_text_hash(text)

                if text_hash in audio_cache:
                    filename = audio_cache[text_hash]
                    filepath = os.path.join(AUDIO_DIR, filename)
                    if os.path.exists(filepath):
                        url = f"http://{LOCAL_IP}:{LOCAL_PORT}/audio/{filename}"
                        response = {"type": "play", "url": url}
                        if mqtt_client_ref:
                            mqtt_client_ref.publish(PUB_TOPIC, json.dumps(response))
                            print("使用缓存音频:", url)
                        continue

                file_id = str(uuid.uuid4())
                filename = f"{file_id}.mp3"
                filepath = os.path.join(AUDIO_DIR, filename)

                raw_path = filepath.replace(".mp3", "_raw.mp3")

                loop.run_until_complete(TextToSpeechFunction._generate_tts_fast(text, raw_path))

                loop.run_until_complete(TextToSpeechFunction._compress_audio_async(raw_path, filepath))

                if os.path.exists(raw_path):
                    os.remove(raw_path)

                if not os.path.exists(filepath):
                    print("文件生成失败")
                    continue

                audio_cache[text_hash] = filename
                if len(audio_cache) > 100:
                    keys = list(audio_cache.keys())[:50]
                    for k in keys:
                        del audio_cache[k]

                _cleanup_old_audio()

                url = f"http://{LOCAL_IP}:{LOCAL_PORT}/audio/{filename}"
                response = {"type": "play", "url": url}

                if mqtt_client_ref:
                    mqtt_client_ref.publish(PUB_TOPIC, json.dumps(response))
                    print("已发送播放URL:", url)
                else:
                    print("MQTT client未就绪")

            except Exception as e:
                print("TTS工作线程出错:", e)
            finally:
                tts_queue.task_done()

    @staticmethod
    def _on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode()
            print("\n收到MQTT:", payload)
            data = json.loads(payload)

            if data.get("type") != "speak":
                return

            text = data.get("text", "").strip()
            if not text:
                print("text为空，跳过")
                return

            print("加入TTS队列:", text)
            tts_queue.put({"text": text})

        except Exception as e:
            print("处理MQTT出错:", e)

    @staticmethod
    def start_mqtt():
        global mqtt_client_ref
        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASS)
        client.on_message = TextToSpeechFunction._on_message
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(SUB_TOPIC)
        mqtt_client_ref = client
        print("MQTT已连接，监听:", SUB_TOPIC)
        client.loop_forever()

    @staticmethod
    def start_tts_worker():
        worker_thread = threading.Thread(target=TextToSpeechFunction._tts_worker, daemon=True)
        worker_thread.start()
        return worker_thread

    @staticmethod
    def start_mqtt_thread():
        mqtt_thread = threading.Thread(target=TextToSpeechFunction.start_mqtt, daemon=True)
        mqtt_thread.start()
        return mqtt_thread

    def text_to_speech(self, text):
        try:
            if not text or not text.strip():
                return create_response(HTTPStatus.BAD_REQUEST, "文本内容不能为空", False)

            tts_queue.put({"text": text.strip()})
            print("加入TTS队列:", text.strip())

            # 记录统计数据
            db_exec.insert_text_stastic(text.strip(), 'text_to_speech')

            return create_response(HTTPStatus.OK, "已加入TTS队列", True)

        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"TTS失败: {str(e)}", False)

    def serve_audio(self, filename):
        try:
            file_path = os.path.join(AUDIO_DIR, filename)
            if not os.path.exists(file_path):
                print("文件不存在:", file_path)
                return create_response(HTTPStatus.NOT_FOUND, "文件不存在", False)

            from flask import send_from_directory
            return send_from_directory(AUDIO_DIR, filename, mimetype="audio/mpeg")

        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"获取音频失败: {str(e)}", False)
