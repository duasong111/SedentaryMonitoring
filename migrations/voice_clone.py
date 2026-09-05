from database.Postgresql import get_postgres_connection


def create_voice_clone_tables():
    """创建音色克隆相关表"""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            # 创建音色档案表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS voice_clone_profiles (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    provider VARCHAR(32) NOT NULL DEFAULT 'volcengine_mega_tts',
                    voice_id TEXT,
                    voice_type VARCHAR(64),
                    reference_audio_path TEXT NOT NULL,
                    reference_sample_text TEXT,
                    reference_duration_ms INTEGER,
                    status VARCHAR(16) NOT NULL DEFAULT 'training',
                    error_message TEXT,
                    last_used_time TIMESTAMP,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """)
            print("✅ 表 voice_clone_profiles 已创建或已存在")

            # 创建索引
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_clone_profiles_device
                    ON voice_clone_profiles(device_id);
            """)
            print("✅ 索引 idx_voice_clone_profiles_device 已创建或已存在")

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_voice_clone_profiles_status
                    ON voice_clone_profiles(status);
            """)
            print("✅ 索引 idx_voice_clone_profiles_status 已创建或已存在")

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_voice_clone_profiles_voice_id
                    ON voice_clone_profiles(voice_id);
            """)
            print("✅ 索引 idx_voice_clone_profiles_voice_id 已创建或已存在")

            conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f" 创建表失败: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    create_voice_clone_tables()
