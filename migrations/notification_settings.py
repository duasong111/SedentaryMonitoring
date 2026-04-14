import psycopg2
from database.Postgresql import get_postgres_connection

# 创建通知设置表
def create_notification_settings_table():
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            # 创建设置表
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL UNIQUE,
                    enable_voice BOOLEAN DEFAULT TRUE,
                    enable_bark BOOLEAN DEFAULT TRUE,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            cur.execute(create_table_sql)
            conn.commit()
            print("通知设置表创建成功")
    except Exception as e:
        print(f"创建通知设置表失败: {e}")

if __name__ == "__main__":
    create_notification_settings_table()