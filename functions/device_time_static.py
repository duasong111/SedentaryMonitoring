from http import HTTPStatus
from Common.Response import create_response
from database.operateFunction import execuFunction
import time
import threading

# 内存缓存，用于滚动窗口和临时数据
class MemoryCache:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
    
    def get(self, key):
        with self.lock:
            return self.cache.get(key)
    
    def set(self, key, value):
        with self.lock:
            self.cache[key] = value
    
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]

# 全局缓存实例
memory_cache = MemoryCache()

# 配置参数
WINDOW_MS = 25000  # 25秒滚动窗口
MIN_PRESENCE_SECONDS = 70  # 最小有人时间（秒）

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
            duration = data.get('duration', 0)  # 设备发送的有人持续时间

            if not device_id or not uuid or not state or not event_timestamp:
                return create_response(HTTPStatus.BAD_REQUEST, "缺少必要参数", False)

            # 生成缓存键
            cache_key = f"device:{device_id}:{uuid}"

            if state == "有人":
                # 处理有人状态
                self._handle_presence_state(cache_key, device_id, uuid, state, distance_cm, event_timestamp, duration)
            else:
                # 处理无人状态
                self._handle_absence_state(cache_key, device_id, uuid, state, distance_cm, event_timestamp, duration)

            # 只处理有人状态
            if state != "有人":
                return create_response(
                    HTTPStatus.OK,
                    "无人状态已忽略",
                    True,
                    data={
                        "device_id": device_id,
                        "uuid": uuid,
                        "state": state,
                        "message": "无人状态不统计"
                    }
                )

            # 只处理有人时长≥70秒的记录
            if duration < MIN_PRESENCE_SECONDS:
                return create_response(
                    HTTPStatus.OK,
                    "短时间有人记录已忽略",
                    True,
                    data={
                        "device_id": device_id,
                        "uuid": uuid,
                        "state": state,
                        "duration": duration,
                        "message": f"有人时长 {duration} 秒小于阈值 {MIN_PRESENCE_SECONDS} 秒，已忽略"
                    }
                )

            # 创建或更新设备时间记录
            result = db_exec.create_or_update_device_time(device_id, uuid, state, distance_cm, event_timestamp, duration)

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

    def _handle_presence_state(self, cache_key, device_id, uuid, state, distance_cm, event_timestamp, duration):
        """处理有人状态"""
        # 设备已经实现了滚动窗口，直接使用设备发送的 duration
        if duration < MIN_PRESENCE_SECONDS:
            # 有人时长小于阈值，不处理
            print(f"忽略短时间有人记录: device_id={device_id}, uuid={uuid}, duration={duration}秒")
            return
        
        # 有人时长达到阈值，更新缓存
        cache_data = memory_cache.get(cache_key) or {}
        cache_data['last_presence_time'] = event_timestamp
        cache_data['total_presence_time'] = duration
        memory_cache.set(cache_key, cache_data)

    def _handle_absence_state(self, cache_key, device_id, uuid, state, distance_cm, event_timestamp, duration):
        """处理无人状态"""
        # 清除缓存
        memory_cache.delete(cache_key)

    def _delete_short_presence_record(self, device_id, uuid):
        """删除短时间有人记录"""
        try:
            # 这里可以实现删除数据库记录的逻辑
            # 目前暂时只清除缓存，实际应用中可以根据需要删除数据库记录
            print(f"删除短时间有人记录: device_id={device_id}, uuid={uuid}")
        except Exception as e:
            print(f"删除短时间有人记录失败: {e}")

    def get_device_stats(self, device_id_or_uuid):
        """获取设备统计数据"""
        try:
            if not device_id_or_uuid:
                return create_response(HTTPStatus.BAD_REQUEST, "device_id或uuid不能为空", False)

            stats = db_exec.get_device_stats(device_id_or_uuid)

            # 过滤掉短时间有人记录
            filtered_stats = []
            for stat in stats:
                if stat.get('presence_duration', 0) >= MIN_PRESENCE_SECONDS:
                    filtered_stats.append(stat)

            # 计算总时长
            total_presence = sum(s.get('presence_duration', 0) for s in filtered_stats)
            total_absence = sum(s.get('absence_duration', 0) for s in filtered_stats)
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
                    "records": filtered_stats
                }
            )

        except Exception as e:
            return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"获取失败: {str(e)}", False)