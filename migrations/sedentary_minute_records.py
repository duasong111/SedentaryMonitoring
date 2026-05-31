from database.Postgresql import get_postgres_connection

def create_sedentary_minute_records_table():
    """创建久坐分钟记录表（原始数据）"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            # 创建分钟记录表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sedentary_minute_records (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    state VARCHAR(50) NOT NULL,
                    avg_distance_cm FLOAT DEFAULT 0,
                    max_distance_cm INTEGER DEFAULT 0,
                    event_timestamp BIGINT,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """)
            print("✅ 表 sedentary_minute_records 已创建或已存在")

            # 按设备+时间查询的索引
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_minute_records_device_time
                ON sedentary_minute_records(device_id, created_time);
            """)
            print("✅ 索引 idx_minute_records_device_time 已创建或已存在")

            conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 创建表失败: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    create_sedentary_minute_records_table()
