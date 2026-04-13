from http import HTTPStatus
from Common.Response import create_response
from database.operateFunction import execuFunction

db_exec = execuFunction()


class DeviceTimeStaticFunction:
    def process_device_event(self, data):
        """处理设备事件并统计时长"""
        try:
            device_id = data.get('device_id')
            uuid = data.get('uuid')
            state = data.get('state')
            distance_cm = data.get('distance_cm')
            event_timestamp = data.get('timestamp')

            if not device_id or not uuid or not state or not event_timestamp:
                return create_response(HTTPStatus.BAD_REQUEST, "缺少必要参数", False)

            # 创建或更新设备时间记录
            result = db_exec.create_or_update_device_time(device_id, uuid, state, distance_cm, event_timestamp)

            if not result.get('success'):
                return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, result.get('message', '处理失败'), False)

            return create_response(
                HTTPStatus.OK,
                "事件处理成功",
                True,
                data=result.get('data')
            )

        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"处理失败: {str(e)}", False)

    def get_device_stats(self, device_id_or_uuid):
        """获取设备统计数据"""
        try:
            if not device_id_or_uuid:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id或uuid不能为空", False)

            stats = db_exec.get_device_stats(device_id_or_uuid)

            # 计算总时长
            total_presence = sum(s.get('presence_duration', 0) for s in stats)
            total_absence = sum(s.get('absence_duration', 0) for s in stats)
            total_duration = total_presence + total_absence

            return create_response(
                HTTPStatus.OK,
                "获取统计成功",
                True,
                data={
                    "device_id_or_uuid": device_id_or_uuid,
                    "total_presence_seconds": total_presence,
                    "total_absence_seconds": total_absence,
                    "total_duration_seconds": total_duration,
                    "records": stats
                }
            )

        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"获取失败: {str(e)}", False)