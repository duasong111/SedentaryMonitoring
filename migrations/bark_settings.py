import psycopg2
from database.Postgresql import get_postgres_connection

# 创建Bark通知设置表
def create_bark_settings_table():
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            # 创建设置表
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS bark_notification_settings (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL UNIQUE,
                    bark_sedentary_threshold INTEGER DEFAULT 3600,
                    bark_reminder_interval INTEGER DEFAULT 600,
                    bark_voice TEXT DEFAULT '您已经久坐了，请注意休息',
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            cur.execute(create_table_sql)
            conn.commit()
            print("Bark通知设置表创建成功")
    except Exception as e:
        print(f"创建Bark通知设置表失败: {e}")

if __name__ == "__main__":
    create_bark_settings_table()