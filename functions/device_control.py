import json
from http import HTTPStatus
from Common.Response import create_response
from database.operateFunction import execuFunction

db_exec = execuFunction()

# 所有可用的 LED 模式
LED_MODES = {
    "progressive": {
        "name": "渐进",
        "description": "随久坐时间递增亮灯，8级渐进提示",
        "params": ["led_intensity"]
    },
    "blink": {
        "name": "全闪",
        "description": "8个灯一起闪烁，可配置速度",
        "params": ["led_interval"]
    },
    "chase": {
        "name": "追逐",
        "description": "单个灯依次跑动，可配置速度",
        "params": ["led_interval"]
    },
    "on": {
        "name": "全亮",
        "description": "8个灯全亮常亮",
        "params": []
    },
    "off": {
        "name": "全灭",
        "description": "8个灯全灭",
        "params": []
    },
    "breathe": {
        "name": "呼吸",
        "description": "由少到多再到少，模拟呼吸效果",
        "params": ["led_interval"]
    },
}


class DeviceControlFunction:
    """设备控制：LED灯 + 震动马达，通过MQTT下发指令"""

    def get_settings(self, device_id):
        """获取设备控制设置"""
        if not device_id:
            return create_response(HTTPStatus.BAD_REQUEST, "device_id不能为空", False)

        settings = db_exec.get_device_control_settings(device_id)
        if not settings:
            # 返回默认设置
            settings = {
                "device_id": device_id,
                "is_enabled": True,
                "vibration_enabled": True,
                "vibration_duration": 500,
                "vibration_interval": 300,
                "led_mode": "progressive",
                "led_interval": 1000,
                "led_intensity": 8,
                "led_brightness": 2,
                "sedentary_threshold": 1800,
            }
        return create_response(HTTPStatus.OK, "查询成功", True, settings)

    def update_settings(self, device_id, data):
        """更新设备控制设置"""
        if not device_id:
            return create_response(HTTPStatus.BAD_REQUEST, "device_id不能为空", False)

        led_mode = data.get('led_mode')
        if led_mode and led_mode not in LED_MODES:
            return create_response(HTTPStatus.BAD_REQUEST,
                                   f"无效的LED模式: {led_mode}，可选: {list(LED_MODES.keys())}", False)

        led_intensity = data.get('led_intensity')
        if led_intensity is not None and (led_intensity < 1 or led_intensity > 8):
            return create_response(HTTPStatus.BAD_REQUEST, "led_intensity 必须在 1-8 之间", False)

        led_brightness = data.get('led_brightness')
        if led_brightness is not None and led_brightness not in (1, 2, 3):
            return create_response(HTTPStatus.BAD_REQUEST, "led_brightness 必须为 1, 2 或 3", False)

        result = db_exec.create_or_update_device_control_settings(
            device_id=device_id,
            is_enabled=data.get('is_enabled'),
            vibration_enabled=data.get('vibration_enabled'),
            vibration_duration=data.get('vibration_duration'),
            vibration_interval=data.get('vibration_interval'),
            led_mode=led_mode,
            led_interval=data.get('led_interval'),
            led_intensity=led_intensity,
            led_brightness=led_brightness,
            sedentary_threshold=data.get('sedentary_threshold'),
        )

        if result.get("success"):
            return create_response(HTTPStatus.OK, "更新成功", True, result.get("data"))
        else:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                   result.get("message", "更新失败"), False)

    def get_available_modes(self):
        """获取所有可用的LED模式"""
        modes = []
        for code, info in LED_MODES.items():
            modes.append({
                "code": code,
                "name": info["name"],
                "description": info["description"],
                "params": info["params"]
            })
        return create_response(HTTPStatus.OK, "查询成功", True, modes)

    # ==================== LED byte 计算 ====================

    @staticmethod
    def compute_led_byte(led_mode, presence_duration, threshold=1800, led_intensity=8,
                         led_interval_ms=1000):
        """
        根据模式和当前久坐时长计算 LED byte

        返回: int (0x00 - 0xFF)
        """
        if led_mode == "off":
            return 0x00

        if led_mode == "on":
            return 0xFF

        if led_mode == "progressive":
            # 渐进：按比例亮灯
            # 例: threshold=1800, intensity=8 → 每级225秒
            # presence=1200 → 1200/225=5 → 前5个灯亮 → 0x1F
            if threshold <= 0:
                return 0xFF
            seconds_per_level = threshold / led_intensity
            current_level = min(int(presence_duration / seconds_per_level), led_intensity)
            if current_level <= 0:
                return 0x00
            return (1 << current_level) - 1

        if led_mode == "blink":
            # 全闪：根据时间奇偶决定全亮或全灭
            # 用 presence_duration 和 interval 计算当前应该亮还是灭
            interval_sec = max(led_interval_ms / 1000, 0.5)
            phase = int(presence_duration / interval_sec)
            return 0xFF if phase % 2 == 0 else 0x00

        if led_mode == "chase":
            # 追逐：单灯依次跑
            interval_sec = max(led_interval_ms / 1000, 0.5)
            position = int(presence_duration / interval_sec) % 8
            return 1 << position

        if led_mode == "breathe":
            # 呼吸：0→1→3→7→F→1F→3F→7F→FF→7F→3F→1F→F→7→3→1→0
            pattern = [0x00, 0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F,
                       0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01]
            interval_sec = max(led_interval_ms / 1000, 0.5)
            idx = int(presence_duration / interval_sec) % len(pattern)
            return pattern[idx]

        return 0x00

    # ==================== MQTT 下发 ====================

    @staticmethod
    def send_control_command(device_id, presence_duration):
        """
        读取设备控制设置，计算 LED byte，通过 MQTT 下发控制命令

        Args:
            device_id: 设备ID
            presence_duration: 当前久坐时长(秒)

        Returns:
            dict: 发送结果
        """
        try:
            import functions.text_to_speech as tts_module

            if not tts_module.mqtt_client_ref:
                return {"success": False, "message": "MQTT client未就绪"}

            # 读取设备控制设置
            settings = db_exec.get_device_control_settings(device_id)
            if not settings:
                return {"success": True, "message": "设备未配置控制设置，跳过"}

            if not settings.get("is_enabled", True):
                return {"success": True, "message": "设备控制未启用"}

            # 检查是否达到阈值
            threshold = settings.get("sedentary_threshold", 1800)
            if presence_duration < threshold:
                return {"success": True, "message": f"未达阈值({presence_duration}/{threshold})"}

            # 计算 LED byte
            led_mode = settings.get("led_mode", "progressive")
            led_intensity = settings.get("led_intensity", 8)
            led_interval = settings.get("led_interval", 1000)
            led_byte = DeviceControlFunction.compute_led_byte(
                led_mode, presence_duration, threshold, led_intensity, led_interval
            )

            # 构造 MQTT 消息
            command = {
                "type": "device_control",
                "vibration": {
                    "enabled": settings.get("vibration_enabled", True),
                    "duration_ms": settings.get("vibration_duration", 500),
                    "interval_sec": settings.get("vibration_interval", 300),
                },
                "led": {
                    "mode": led_mode,
                    "byte_value": led_byte,
                    "brightness": settings.get("led_brightness", 2),
                    "interval_ms": led_interval,
                }
            }

            # MQTT 下发
            topic = f"control/{device_id}"
            pub_result = tts_module.mqtt_client_ref.publish(topic, json.dumps(command))
            if pub_result.rc != 0:
                return {"success": False, "message": f"MQTT发送失败，返回码: {pub_result.rc}"}
            print(f"设备控制命令已下发 → {topic}: LED={led_mode}(0x{led_byte:02X})")

            return {"success": True, "command": command}

        except Exception as e:
            return {"success": False, "message": f"下发控制命令失败: {str(e)}"}

    @staticmethod
    def send_direct_control(device_id: str, led_mode: str = None, brightness: int = 2,
                            interval_ms: int = 1000, byte_value: int = 0,
                            vibration_enabled: bool = True, vibration_duration: int = 500,
                            vibration_interval: int = 300):
        """ 直接下发控制命令 """
        try:
            import functions.text_to_speech as tts_module

            if not tts_module.mqtt_client_ref:
                return {"success": False, "message": "MQTT client未就绪"}

            final_mode = led_mode or "progressive"

            command = {
                "type": "device_control",
                "vibration": {
                    "enabled": vibration_enabled,
                    "duration_ms": vibration_duration,
                    "interval_sec": vibration_interval,
                },
                "led": {
                    "mode": final_mode,
                    "byte_value": byte_value,
                    "brightness": brightness,
                    "interval_ms": interval_ms,
                }
            }

            topic = f"control/{device_id}"        # ← 改为动态

            pub_result = tts_module.mqtt_client_ref.publish(
                topic, json.dumps(command), qos=1, retain=False
            )

            rc = pub_result.rc if hasattr(pub_result, 'rc') else pub_result

            if rc == 0:
                return {
                    "success": True,
                    "message": "控制命令已下发",
                    "topic": topic,
                    "command": command
                }
            else:
                return {"success": False, "message": f"MQTT发送失败，返回码: {rc}"}

        except Exception as e:
            return {"success": False, "message": f"下发失败: {str(e)}"}