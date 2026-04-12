from database.Postgresql import get_postgres_connection

def create_user_text_stastic_table():
    """创建用户文本统计表格"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            # 创建用户文本统计表格
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_text_stastic (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    type VARCHAR(50) NOT NULL,  -- speech_to_text, text_to_speech, doubao_chat
                    status VARCHAR(20) DEFAULT 'success',
                    latency_ms FLOAT DEFAULT 0,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """)
            print("✅ 表 user_text_stastic 已创建或已存在")

            conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f" 创建表失败: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    create_user_text_stastic_table()