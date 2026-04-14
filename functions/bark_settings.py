from http import HTTPStatus
from Common.Response import create_response
from database.operateFunction import execuFunction
from config import (
    DEFAULT_BARK_SEDENTARY_THRESHOLD,
    DEFAULT_BARK_REMINDER_INTERVAL,
    DEFAULT_BARK_VOICE
)


db_exec = execuFunction()


class BarkSettingsFunction:
    def _get_default_settings(self, device_id):
        """获取默认设置"""
        return {
            'device_id': device_id,
            'bark_sedentary_threshold': DEFAULT_BARK_SEDENTARY_THRESHOLD,
            'bark_reminder_interval': DEFAULT_BARK_REMINDER_INTERVAL,
            'bark_voice': DEFAULT_BARK_VOICE
        }

    def _fill_default_values(self, settings, device_id):
        """填充默认值"""
        if not settings:
            return self._get_default_settings(device_id)
        
        # 填充默认值
        if settings.get('bark_sedentary_threshold') is None:
            settings['bark_sedentary_threshold'] = DEFAULT_BARK_SEDENTARY_THRESHOLD
        
        if settings.get('bark_reminder_interval') is None:
            settings['bark_reminder_interval'] = DEFAULT_BARK_REMINDER_INTERVAL
        
        if settings.get('bark_voice') is None:
            settings['bark_voice'] = DEFAULT_BARK_VOICE
        
        return settings

    def get_settings(self, device_id):
        """获取设备Bark通知设置"""
        try:
            if not device_id:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id不能为空", False)

            settings = db_exec.get_bark_settings(device_id)
            
            # 填充默认值
            settings = self._fill_default_values(settings, device_id)

            return create_response(
                HTTPStatus.OK,
                "获取设置成功",
                True,
                data=settings
            )
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"获取失败: {str(e)}", False)

    def update_settings(self, device_id, data):
        """更新Bark通知设置"""
        try:
            if not device_id:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id不能为空", False)

            bark_sedentary_threshold = data.get('bark_sedentary_threshold')
            bark_reminder_interval = data.get('bark_reminder_interval')
            bark_voice = data.get('bark_voice')

            # 验证参数
            if bark_sedentary_threshold is not None and bark_sedentary_threshold <= 0:
                return create_response(HTTPStatus.BAD_REQUEST, "Bark久坐阈值必须大于0", False)
            if bark_reminder_interval is not None and bark_reminder_interval <= 0:
                return create_response(HTTPStatus.BAD_REQUEST, "Bark提醒间隔必须大于0", False)

            result = db_exec.create_or_update_bark_settings(
                device_id,
                bark_sedentary_threshold=bark_sedentary_threshold,
                bark_reminder_interval=bark_reminder_interval,
                bark_voice=bark_voice
            )

            if not result.get('success'):
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, result.get('message', '更新失败'), False)

            # 填充默认值后返回
            settings = result.get('data')
            settings = self._fill_default_values(settings, device_id)

            return create_response(
                HTTPStatus.OK,
                "更新设置成功",
                True,
                data=settings
            )
        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"更新失败: {str(e)}", False)


# 全局实例
bark_settings = BarkSettingsFunction()