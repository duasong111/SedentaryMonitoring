import os
import uuid
import time
import base64
import asyncio
import json
import requests
from http import HTTPStatus
from Common.Response import create_response
from config import (
    LOCAL_IP, LOCAL_PORT, PUB_TOPIC,
    VOLCENGINE_APPID, VOLCENGINE_TOKEN, VOLCENGINE_CLUSTER, VOLCENGINE_CLONE_RESOURCE_ID,
    VOLC_TTS_UPLOAD_URL, VOLC_TTS_TTS_URL,
    VOICE_CLONE_REF_DIR, VOICE_CLONE_AUDIO_PREFIX,
    VOICE_CLONE_MIN_DURATION_MS, VOICE_CLONE_MAX_DURATION_MS, VOICE_CLONE_TIMEOUT,
)
from database.operateFunction import execuFunction

# 初始化数据库操作实例
db_exec = execuFunction()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
REF_DIR = os.path.join(AUDIO_DIR, VOICE_CLONE_REF_DIR)

MAX_CLONE_AUDIO_FILES = 20


# ----- 模块级工具 -----

def _cleanup_old_clone_audio():
    """清理过期的 clone_*.mp3，保留最新 20 个（与 edge-tts 同步策略）"""
    try:
        files = []
        for f in os.listdir(AUDIO_DIR):
            if f.startswith(VOICE_CLONE_AUDIO_PREFIX) and f.endswith('.mp3'):
                fp = os.path.join(AUDIO_DIR, f)
                files.append((fp, os.path.getmtime(fp)))

        files.sort(key=lambda x: x[1], reverse=True)

        for fp, _ in files[MAX_CLONE_AUDIO_FILES:]:
            try:
                os.remove(fp)
                print("清理旧克隆音频:", fp)
            except Exception as e:
                print("清理失败:", e)
    except Exception as e:
        print("清理克隆音频出错:", e)


async def _ffmpeg_to_wav(src, dst):
    """ffmpeg 转 16k 单声道 WAV（异步子进程，复用 text_to_speech 的写法）"""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", src,
        "-ar", "16000",
        "-ac", "1",
        dst,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    if proc.returncode != 0:
        raise Exception("ffmpeg 转 WAV 失败")


def _probe_duration_ms(path):
    """用 ffprobe 读音频时长（毫秒）。失败返回 None"""
    try:
        import subprocess
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path
        ], stderr=subprocess.STDOUT).decode().strip()
        return int(float(out) * 1000)
    except Exception:
        return None


def _fallback_to_edge_tts(text):
    """降级到 edge-tts，返回原 text_to_speech 的响应数据"""
    from functions.text_to_speech import tts_func
    resp = tts_func.text_to_speech(text.strip())
    resp_data = resp[0].get_json() if isinstance(resp, tuple) else {}
    return {
        "success": resp_data.get("success", False),
        "message": resp_data.get("message", ""),
        "data": None,
    }


# ----- 业务类 -----

class VoiceCloneFunction:

    def register_voice(self, device_id, audio_bytes, mime_type, sample_text):
        try:
            if not device_id or not device_id.strip():
                return create_response(HTTPStatus.BAD_REQUEST, "device_id 不能为空", False)
            if not audio_bytes:
                return create_response(HTTPStatus.BAD_REQUEST, "音频不能为空", False)
            if not sample_text or not sample_text.strip():
                return create_response(HTTPStatus.BAD_REQUEST, "sample_text 不能为空", False)

            # 1) 保存原文件到 audio/ref/{device_id}/{ts}_raw.{ext}
            os.makedirs(os.path.join(REF_DIR, device_id), exist_ok=True)
            ts = int(time.time())
            ext = "wav" if (mime_type and "wav" in mime_type.lower()) else "mp3"
            raw_path = os.path.join(REF_DIR, device_id, f"{ts}_raw.{ext}")
            with open(raw_path, "wb") as f:
                f.write(audio_bytes)

            # 2) ffmpeg 转 16k 单声道 WAV（云服务侧要求）
            wav_path = os.path.join(REF_DIR, device_id, f"{ts}.wav")
            try:
                asyncio.run(_ffmpeg_to_wav(raw_path, wav_path))
            except Exception as e:
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"音频转码失败: {str(e)}", False)

            if not os.path.exists(wav_path):
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, "音频转码失败", False)

            # 3) 时长校验
            duration_ms = _probe_duration_ms(wav_path)
            if duration_ms is None:
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, "无法读取音频时长（需安装 ffprobe）", False)
            if duration_ms < VOICE_CLONE_MIN_DURATION_MS:
                return create_response(HTTPStatus.BAD_REQUEST,
                    f"音频太短（{duration_ms/1000:.1f}s），至少 {VOICE_CLONE_MIN_DURATION_MS/1000:.0f} 秒", False)
            if duration_ms > VOICE_CLONE_MAX_DURATION_MS:
                return create_response(HTTPStatus.BAD_REQUEST,
                    f"音频太长（{duration_ms/1000:.1f}s），最多 {VOICE_CLONE_MAX_DURATION_MS/1000:.0f} 秒", False)

            # 4) 入库（先 training 状态）
            voice_type = f"user_{device_id}_{ts}"
            result = db_exec.create_or_update_voice_clone_profile(
                device_id=device_id,
                provider="volcengine_mega_tts",
                voice_type=voice_type,
                reference_audio_path=os.path.relpath(wav_path, AUDIO_DIR),
                reference_sample_text=sample_text.strip(),
                reference_duration_ms=duration_ms,
                status="training",
            )
            if not result.get("success"):
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                    f"入库失败: {result.get('message')}", False)

            # 5) 调火山引擎上传+训练
            with open(wav_path, "rb") as f:
                wav_b64 = base64.b64encode(f.read()).decode()
            try:
                resp = requests.post(VOLC_TTS_UPLOAD_URL,
                    headers={
                        "Content-Type": "application/json",
                        "X-Api-App-Key": VOLCENGINE_APPID,
                        "X-Api-Access-Token": VOLCENGINE_TOKEN,
                        "X-Api-Resource-Id": VOLCENGINE_CLONE_RESOURCE_ID,
                    },
                    json={
                        "appid": VOLCENGINE_APPID,
                        "token": VOLCENGINE_TOKEN,
                        "cluster": VOLCENGINE_CLUSTER,
                        "voice_type": voice_type,
                        "audio": {"data": wav_b64},
                        "audio_format": "wav",
                        "audio_sample_rate_hz": 16000,
                        "text": sample_text.strip(),
                        "source": 2,
                    },
                    timeout=VOICE_CLONE_TIMEOUT,
                )
                try:
                    data = resp.json()
                except Exception:
                    data = {}
            except Exception as e:
                db_exec.update_voice_clone_status(device_id, status="failed", error_message=f"上传异常: {e}")
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"上传到云端失败: {str(e)}", False)

            voice_id = (data or {}).get("voice_id") or (data or {}).get("data", {}).get("voice_id")
            if resp.status_code != 200 or not voice_id:
                err = (data or {}).get("message") or resp.text[:200]
                db_exec.update_voice_clone_status(device_id, status="failed", error_message=str(err))
                return create_response(HTTPStatus.BAD_GATEWAY, f"云端训练失败: {err}", False)

            # 6) 更新为 active
            db_exec.update_voice_clone_status(device_id, status="active", voice_id=voice_id)

            # 记录统计数据
            db_exec.insert_text_stastic(sample_text.strip(), 'voice_clone_register')

            return create_response(HTTPStatus.OK, "音色注册成功", True, data={
                "device_id": device_id,
                "voice_id": voice_id,
                "voice_type": voice_type,
                "status": "active",
                "reference_audio_path": os.path.relpath(wav_path, AUDIO_DIR),
                "duration_ms": duration_ms,
            })

        except Exception as e:
            import traceback
            print(f"[ERROR] 音色注册失败: {e}")
            traceback.print_exc()
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"音色注册失败: {str(e)}", False)

    def get_profile(self, device_id):
        try:
            if not device_id or not device_id.strip():
                return create_response(HTTPStatus.BAD_REQUEST, "device_id 不能为空", False)

            profile = db_exec.get_voice_clone_profile(device_id)
            if not profile:
                return create_response(HTTPStatus.NOT_FOUND, "尚未注册音色", False)
            return create_response(HTTPStatus.OK, "查询成功", True, data=profile)
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"查询失败: {str(e)}", False)

    def synthesize_now(self, device_id, text):
        """同步合成；返回 {success, message, data:{url, filename, voice_id, used_clone, fallback}}"""
        try:
            if not text or not text.strip():
                return {"success": False, "message": "文本为空", "data": None}

            # 1) 没传 device_id → 走 edge-tts 降级
            if not device_id:
                _fallback_to_edge_tts(text)
                return {
                    "success": True,
                    "message": "未传 device_id，已使用默认音色",
                    "data": {"used_clone": False, "fallback": "edge_tts"},
                }

            # 2) 查 profile
            profile = db_exec.get_voice_clone_profile(device_id)
            if not profile or profile.get("status") != "active" or not profile.get("voice_id"):
                _fallback_to_edge_tts(text)
                return {
                    "success": True,
                    "message": "未注册克隆音色，已使用默认音色",
                    "data": {"used_clone": False, "fallback": "edge_tts_no_profile"},
                }

            # 3) 调火山引擎合成
            t0 = time.time()
            try:
                resp = requests.post(VOLC_TTS_TTS_URL,
                    headers={
                        "Content-Type": "application/json",
                        "X-Api-App-Key": VOLCENGINE_APPID,
                        "X-Api-Access-Token": VOLCENGINE_TOKEN,
                        "X-Api-Resource-Id": VOLCENGINE_CLONE_RESOURCE_ID,
                    },
                    json={
                        "appid": VOLCENGINE_APPID,
                        "token": VOLCENGINE_TOKEN,
                        "cluster": VOLCENGINE_CLUSTER,
                        "voice_type": profile["voice_id"],
                        "text": text.strip(),
                        "encoding": "mp3",
                        "speed_ratio": 1.0,
                        "volume_ratio": 1.0,
                        "pitch_ratio": 1.0,
                    },
                    timeout=VOICE_CLONE_TIMEOUT,
                )
                try:
                    data = resp.json()
                except Exception:
                    data = {}
            except Exception as e:
                # 云端异常 → 降级
                _fallback_to_edge_tts(text)
                db_exec.insert_text_stastic(text.strip(), 'voice_clone_tts',
                                            round((time.time()-t0)*1000, 2), status='fallback')
                return {
                    "success": True,
                    "message": f"云端异常已降级: {str(e)}",
                    "data": {"used_clone": False, "fallback": "cloud_error"},
                }

            # mega_tts 返回结构兼容：可能在 data 或 data.data
            mp3_b64 = None
            if isinstance(data, dict):
                mp3_b64 = data.get("data")
                if not mp3_b64 and isinstance(data.get("data"), dict):
                    mp3_b64 = data["data"].get("data")

            if resp.status_code != 200 or not mp3_b64:
                _fallback_to_edge_tts(text)
                return {
                    "success": True,
                    "message": f"云端返回异常已降级: {(data or {}).get('message', '') or resp.text[:100]}",
                    "data": {"used_clone": False, "fallback": "bad_response"},
                }

            # 4) 存 mp3 到 audio/clone_{uuid}.mp3
            filename = f"{VOICE_CLONE_AUDIO_PREFIX}{uuid.uuid4()}.mp3"
            filepath = os.path.join(AUDIO_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(mp3_b64))

            # 5) 走 MQTT 播放（与 edge-tts 完全一致的指令格式）
            url = f"http://{LOCAL_IP}:{LOCAL_PORT}/audio/{filename}"
            from functions.text_to_speech import mqtt_client_ref
            if mqtt_client_ref:
                mqtt_client_ref.publish(PUB_TOPIC, json.dumps({"type": "play", "url": url}))
                print("克隆语音已下发:", url)
            else:
                print("MQTT client未就绪，跳过下发")

            _cleanup_old_clone_audio()
            db_exec.touch_voice_clone_used(device_id)
            db_exec.insert_text_stastic(text.strip(), 'voice_clone_tts',
                                        round((time.time()-t0)*1000, 2), status='success')

            return {
                "success": True,
                "message": "克隆语音已合成",
                "data": {
                    "url": url,
                    "filename": filename,
                    "voice_id": profile["voice_id"],
                    "used_clone": True,
                },
            }

        except Exception as e:
            import traceback
            print(f"[ERROR] 克隆语音合成失败: {e}")
            traceback.print_exc()
            # 兜底降级
            try:
                _fallback_to_edge_tts(text)
            except Exception:
                pass
            return {
                "success": True,
                "message": f"异常已降级: {str(e)}",
                "data": {"used_clone": False, "fallback": "exception"},
            }

    def delete_voice(self, device_id):
        try:
            if not device_id or not device_id.strip():
                return create_response(HTTPStatus.BAD_REQUEST, "device_id 不能为空", False)

            profile = db_exec.get_voice_clone_profile(device_id)
            if not profile:
                return create_response(HTTPStatus.NOT_FOUND, "未找到音色档案", False)

            result = db_exec.update_voice_clone_status(device_id, status="disabled")
            if not result.get("success"):
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, result.get("message"), False)
            return create_response(HTTPStatus.OK, "已停用克隆音色", True)
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"删除失败: {str(e)}", False)
