from database.Postgresql import get_postgres_connection

def create_device_time_table():
    """创建设备时长统计表（单表）"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            # 创建设备时长统计表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS device_time (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    uuid VARCHAR(255) NOT NULL,
                    state VARCHAR(50) NOT NULL,
                    distance_cm INTEGER,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    last_update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    presence_duration INTEGER DEFAULT 0,
                    absence_duration INTEGER DEFAULT 0,
                    event_timestamp BIGINT NOT NULL
                );
            """)
            print("✅ 表 device_time 已创建或已存在")

            # 创建索引
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_device_time_uuid ON device_time(uuid);
            """)
            print("✅ 索引 idx_device_time_uuid 已创建或已存在")

            conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f" 创建表失败: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    create_device_time_table()