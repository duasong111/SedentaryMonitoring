from database.Postgresql import get_postgres_connection


def create_sedentary_reminder_tables():
    """创建久坐提醒相关表"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            # 创建提醒设置表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sedentary_reminder_settings (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    sedentary_threshold INTEGER DEFAULT 1800 NOT NULL,
                    reminder_interval INTEGER DEFAULT 300 NOT NULL,
                    reminder_voice TEXT,
                    voice_list TEXT,
                    is_enabled BOOLEAN DEFAULT true,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """)
            print("✅ 表 sedentary_reminder_settings 已创建或已存在")

            # 创建提醒记录表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sedentary_reminder_records (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    uuid VARCHAR(255) NOT NULL,
                    sedentary_duration INTEGER NOT NULL,
                    reminder_text TEXT,
                    reminder_voice TEXT,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """)
            print("✅ 表 sedentary_reminder_records 已创建或已存在")

            # 创建索引
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_sedentary_settings_device ON sedentary_reminder_settings(device_id);
            """)
            print("✅ 索引 idx_sedentary_settings_device 已创建或已存在")

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sedentary_records_device ON sedentary_reminder_records(device_id);
            """)
            print("✅ 索引 idx_sedentary_records_device 已创建或已存在")

            conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f" 创建表失败: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    create_sedentary_reminder_tables()
