
from database.Postgresql import get_postgres_connection
def create_device_tables():
    """创建 Device、DeviceRunSession 和 User 三个表"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            # 1. 创建用户表 (User) 
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "user" (
                    name VARCHAR(255) PRIMARY KEY,
                    password BYTEA NOT NULL,
                    salt TEXT NOT NULL,
                    avatar_path VARCHAR(500) DEFAULT NULL,
                    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """)
            print("✅ 表 \"user\" 已创建或已存在")

            conn.commit()


    except Exception as e:
        if conn:
            conn.rollback()
        print(f" 创建表失败: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    create_device_tables()