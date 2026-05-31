from database.Postgresql import get_postgres_connection
from psycopg2.extras import DictCursor


class SedentaryDailyStats:
    """久坐统计：存分钟原始数据，查询时聚合出小时/日/周/月"""

    # ==================== 写入操作 ====================

    def insert_minute_record(self, device_id, state, avg_distance_cm, max_distance_cm, timestamp):
        """插入一条分钟级原始记录"""
        try:
            conn = get_postgres_connection()
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO sedentary_minute_records
                        (device_id, state, avg_distance_cm, max_distance_cm, event_timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cur.execute(sql, (device_id, state, avg_distance_cm, max_distance_cm, timestamp))
                conn.commit()
                return {"success": True}
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            return {"success": False, "message": f"写入失败: {str(e)}"}

    # ==================== 查询统计 ====================

    def get_hourly_stats(self, device_id, date_str):
        """查询某天24小时的统计分布（从分钟数据聚合，前端画柱状图）"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                sql = """
                    SELECT
                        EXTRACT(HOUR FROM created_time)::INTEGER AS stat_hour,
                        COUNT(*) FILTER (WHERE state = '有人') AS sedentary_minute_count,
                        COUNT(*) FILTER (WHERE state = '有人') * 60 AS total_sedentary_seconds,
                        COUNT(*) FILTER (WHERE state = '无人') AS absence_minute_count,
                        COUNT(*) FILTER (WHERE state = '无人') * 60 AS absence_seconds,
                        COUNT(*) FILTER (
                            WHERE state = '无人'
                            AND LAG(state) OVER (ORDER BY created_time) = '有人'
                        ) AS leave_count,
                        AVG(avg_distance_cm) FILTER (WHERE state = '有人') AS avg_distance_cm,
                        MAX(max_distance_cm) FILTER (WHERE state = '有人') AS max_distance_cm
                    FROM sedentary_minute_records
                    WHERE device_id = %s AND created_time::DATE = %s::DATE
                    GROUP BY EXTRACT(HOUR FROM created_time)
                    ORDER BY stat_hour ASC
                """
                cur.execute(sql, (device_id, date_str))
                rows = cur.fetchall()
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            return []

    def get_daily_stats(self, device_id, date_str):
        """查询某一天的统计（从分钟数据聚合）"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                sql = """
                    SELECT
                        device_id,
                        created_time::DATE AS stat_date,
                        COUNT(*) FILTER (WHERE state = '有人') AS total_sedentary_minutes,
                        COUNT(*) FILTER (WHERE state = '有人') * 60 AS total_sedentary_seconds,
                        COUNT(*) FILTER (WHERE state = '无人') AS total_absence_minutes,
                        COUNT(*) FILTER (WHERE state = '无人') * 60 AS total_absence_seconds,
                        COUNT(DISTINCT EXTRACT(HOUR FROM created_time)) AS active_hours,
                        AVG(avg_distance_cm) FILTER (WHERE state = '有人') AS avg_distance_cm
                    FROM sedentary_minute_records
                    WHERE device_id = %s AND created_time::DATE = %s::DATE
                    GROUP BY device_id, created_time::DATE
                """
                cur.execute(sql, (device_id, date_str))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            return None

    def get_range_stats(self, device_id, start_date, end_date):
        """查询日期范围内的每日统计"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                sql = """
                    SELECT
                        created_time::DATE AS stat_date,
                        COUNT(*) FILTER (WHERE state = '有人') AS total_sedentary_minutes,
                        COUNT(*) FILTER (WHERE state = '有人') * 60 AS total_sedentary_seconds,
                        COUNT(*) FILTER (WHERE state = '无人') AS total_absence_minutes,
                        COUNT(*) FILTER (WHERE state = '无人') * 60 AS total_absence_seconds
                    FROM sedentary_minute_records
                    WHERE device_id = %s
                      AND created_time >= %s
                      AND created_time < %s
                    GROUP BY created_time::DATE
                    ORDER BY stat_date ASC
                """
                cur.execute(sql, (device_id, start_date, end_date))
                rows = cur.fetchall()
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            return []

    def get_weekly_stats(self, device_id):
        """查询本周统计"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                sql = """
                    SELECT
                        device_id,
                        COUNT(*) FILTER (WHERE state = '有人') AS total_sedentary_minutes,
                        COUNT(*) FILTER (WHERE state = '有人') * 60 AS total_sedentary_seconds,
                        COUNT(*) FILTER (WHERE state = '无人') AS total_absence_minutes,
                        COUNT(*) FILTER (WHERE state = '无人') * 60 AS total_absence_seconds,
                        COUNT(DISTINCT created_time::DATE) AS active_days
                    FROM sedentary_minute_records
                    WHERE device_id = %s
                      AND created_time >= DATE_TRUNC('week', CURRENT_DATE)
                      AND created_time < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '1 week'
                    GROUP BY device_id
                """
                cur.execute(sql, (device_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            return None

    def get_monthly_stats(self, device_id):
        """查询本月统计"""
        try:
            conn = get_postgres_connection()
            with conn.cursor(cursor_factory=DictCursor) as cur:
                sql = """
                    SELECT
                        device_id,
                        COUNT(*) FILTER (WHERE state = '有人') AS total_sedentary_minutes,
                        COUNT(*) FILTER (WHERE state = '有人') * 60 AS total_sedentary_seconds,
                        COUNT(*) FILTER (WHERE state = '无人') AS total_absence_minutes,
                        COUNT(*) FILTER (WHERE state = '无人') * 60 AS total_absence_seconds,
                        COUNT(DISTINCT created_time::DATE) AS active_days
                    FROM sedentary_minute_records
                    WHERE device_id = %s
                      AND created_time >= DATE_TRUNC('month', CURRENT_DATE)
                      AND created_time < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
                    GROUP BY device_id
                """
                cur.execute(sql, (device_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            return None

    # ==================== ESP32 上报处理 ====================

    def process_report(self, device_id, state, avg_distance_cm=0, max_distance_cm=0, timestamp=None):
        """处理ESP32的每分钟上报，直接存入分钟记录表"""
        return self.insert_minute_record(device_id, state, avg_distance_cm, max_distance_cm, timestamp)
