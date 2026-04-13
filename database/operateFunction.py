from datetime import datetime
import psycopg2
import psycopg2.extras
from psycopg2.extras import DictCursor
from database.Postgresql import get_postgres_connection

class execuFunction():
    def _quote_identifier(self, identifier: str) -> str:
        """安全地给表名或列名加双引号"""
        if not identifier:
            raise ValueError("标识符不能为空")
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    def add_data(self, dbName: str, insertData: list[dict]):
        """通用插入"""
        if not insertData:
            return {"success": True, "message": "无数据插入", "inserted_count": 0}

        try:
            conn = get_postgres_connection()
            with conn.cursor() as cur:
                table = self._quote_identifier(dbName)
                columns = list(insertData[0].keys())
                quoted_columns = [self._quote_identifier(col) for col in columns]

                sql = f"INSERT INTO {table} ({', '.join(quoted_columns)}) VALUES %s"
                values = [tuple(d.get(col) for col in columns) for d in insertData]

                psycopg2.extras.execute_values(cur, sql, values)
                conn.commit()
                return {
                    "success": True,
                    "message": "数据添加成功",
                    "inserted_count": len(insertData)
                }
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            return {"success": False, "message": str(e)}

    def query_individual_users(self, dbName: str, queryParams: str, queryData):
        """查询单个用户"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                table = self._quote_identifier(dbName)
                column = self._quote_identifier(queryParams)
                sql = f"SELECT * FROM {table} WHERE {column} = %s LIMIT 1"
                cur.execute(sql, (queryData,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            return None   # 或者返回 {"error": str(e)}，由上层决定

    def update_user_key_value(self, db_name: str, key_value: str, username: str, new_data, key_type: str):
        """更新单个字段"""
        try:
            if not key_value or not key_type:
                return {"success": False, "message": "key_value 和 key_type 不能为空"}

            conn = get_postgres_connection()
            with conn.cursor() as cur:
                table = self._quote_identifier(db_name)
                where_col = self._quote_identifier(key_value)   # 通常是 'name'
                set_col = self._quote_identifier(key_type)      # 要更新的字段，如 'updated_time'

                sql = f"UPDATE {table} SET {set_col} = %s WHERE {where_col} = %s"
                cur.execute(sql, (new_data, username))
                conn.commit()
                affected = cur.rowcount
                return {
                    "success": affected > 0,
                    "message": f"{key_type} 更新成功" if affected > 0 else f"未找到用户 {username}"
                }
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            return {"success": False, "message": f"更新失败: {str(e)}"}

    def insert_text_stastic(self, content, type_, latency_ms=0, status='success'):
        """插入文本统计数据"""
        if not content:
            return {"success": False, "message": "内容不能为空"}

        try:
            conn = get_postgres_connection()
            with conn.cursor() as cur:
                query = """
                    INSERT INTO user_text_stastic (content, type, status, latency_ms, created_time)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """
                cur.execute(query, (content, type_, status, latency_ms))
                conn.commit()
                return {"success": True, "message": "插入成功"}
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            return {"success": False, "message": f"插入失败: {str(e)}"}

    def get_device_time(self, uuid):
        """获取设备时间记录"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                sql = """
                    SELECT * FROM device_time
                    WHERE uuid = %s
                """
                cur.execute(sql, (uuid,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            return None

    def create_or_update_device_time(self, device_id, uuid, state, distance_cm, event_timestamp, duration=0):
        """创建或更新设备时间记录"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # 检查记录是否存在
                existing = self.get_device_time(uuid)

                if existing:
                    # 更新记录
                    presence_duration = existing['presence_duration']
                    absence_duration = existing['absence_duration']

                    # 如果是有人状态且有duration，直接使用设备发送的duration
                    if state == '有人' and duration > 0:
                        presence_duration = duration
                    else:
                        # 否则计算时间差
                        last_timestamp = existing['event_timestamp']
                        time_delta = event_timestamp - last_timestamp
                        last_state = existing['state']

                        if time_delta > 0:
                            if last_state == '有人':
                                presence_duration += time_delta
                            else:
                                absence_duration += time_delta

                    sql = """
                        UPDATE device_time
                        SET state = %s,
                            distance_cm = %s,
                            last_update_time = CURRENT_TIMESTAMP,
                            presence_duration = %s,
                            absence_duration = %s,
                            event_timestamp = %s
                        WHERE uuid = %s
                        RETURNING *
                    """
                    cur.execute(sql, (state, distance_cm, presence_duration, absence_duration, event_timestamp, uuid))
                    conn.commit()
                    updated_row = cur.fetchone()
                    return {"success": True, "data": dict(updated_row) if updated_row else None}
                else:
                    # 创建新记录
                    presence_duration = duration if state == '有人' and duration > 0 else 0
                    sql = """
                        INSERT INTO device_time (device_id, uuid, state, distance_cm, start_time, last_update_time, presence_duration, absence_duration, event_timestamp)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, 0, %s)
                        RETURNING *
                    """
                    cur.execute(sql, (device_id, uuid, state, distance_cm, presence_duration, event_timestamp))
                    conn.commit()
                    new_row = cur.fetchone()
                    return {"success": True, "data": dict(new_row) if new_row else None}
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            return {"success": False, "message": f"操作失败: {str(e)}"}

    def get_device_stats(self, device_id_or_uuid):
        """获取设备统计数据"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                sql = """
                    SELECT
                        id,
                        device_id,
                        uuid,
                        state,
                        distance_cm,
                        start_time,
                        last_update_time,
                        presence_duration,
                        absence_duration,
                        (presence_duration + absence_duration) as total_duration,
                        event_timestamp
                    FROM device_time
                    WHERE device_id = %s OR uuid = %s
                    ORDER BY start_time DESC
                """
                cur.execute(sql, (device_id_or_uuid, device_id_or_uuid))
                rows = cur.fetchall()
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            return []