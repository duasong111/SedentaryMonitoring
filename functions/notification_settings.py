from http import HTTPStatus
from Common.Response import create_response
from database.operateFunction import execuFunction


db_exec = execuFunction()


class NotificationSettingsFunction:
    def get_settings(self, device_id):
        """获取设备通知设置"""
        try:
            if not device_id:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id不能为空", False)

            settings = db_exec.get_notification_settings(device_id)
            
            # 如果没有设置，返回默认值
            if not settings:
                settings = {
                    'device_id': device_id,
                    'enable_voice': True,
                    'enable_bark': True
                }

            return create_response(
                HTTPStatus.OK,
                "获取设置成功",
                True,
                data=settings
            )
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"获取失败: {str(e)}", False)

    def update_settings(self, device_id, data):
        """更新通知设置"""
        try:
            if not device_id:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id不能为空", False)

            enable_voice = data.get('enable_voice')
            enable_bark = data.get('enable_bark')

            # 验证参数
            if enable_voice is not None and not isinstance(enable_voice, bool):
                return create_response(HTTPStatus.BAD_REQUEST, "enable_voice必须是布尔值", False)
            if enable_bark is not None and not isinstance(enable_bark, bool):
                return create_response(HTTPStatus.BAD_REQUEST, "enable_bark必须是布尔值", False)

            result = db_exec.create_or_update_notification_settings(
                device_id,
                enable_voice=enable_voice,
                enable_bark=enable_bark
            )

            if not result.get('success'):
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, result.get('message', '更新失败'), False)

            settings = result.get('data')

            return create_response(
                HTTPStatus.OK,
                "更新设置成功",
                True,
                data=settings
            )
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"更新失败: {str(e)}", False)


# 全局实例
notification_settings = NotificationSettingsFunction()