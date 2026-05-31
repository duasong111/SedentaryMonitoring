from database.Postgresql import get_postgres_connection

def create_device_control_settings_table():
    """创建设备控制设置表"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS device_control_settings (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL UNIQUE,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    vibration_enabled BOOLEAN DEFAULT TRUE,
                    vibration_duration INTEGER DEFAULT 500,
                    vibration_interval INTEGER DEFAULT 300,
                    led_mode VARCHAR(50) DEFAULT 'progressive',
                    led_interval INTEGER DEFAULT 1000,
                    led_intensity INTEGER DEFAULT 8,
                    led_brightness INTEGER DEFAULT 2,
                    sedentary_threshold INTEGER DEFAULT 1800,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """)
            print("✅ 表 device_control_settings 已创建或已存在")

            conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 创建表失败: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    create_device_control_settings_table()
