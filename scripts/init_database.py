#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建AgentForge所需的所有数据库表
"""
import sqlite3
from pathlib import Path


def create_database():
    """创建数据库和表结构"""
    # 确保目录存在
    db_dir = Path("./data")
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "agentforge.db"

    print(f"创建数据库: {db_path}")

    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("创建表结构...")

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            avatar_url TEXT,
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            last_login_at TIMESTAMP
        )
    """)
    print("- 用户表创建完成")

    # 用户会话表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            model_name TEXT,
            kb_name TEXT,
            tools_config TEXT,
            total_messages INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            metadata TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    print("- 用户会话表创建完成")

    # 提交事务
    conn.commit()

    # 验证创建的表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print(f"\n成功创建 {len(tables)} 个表:")
    for table in tables:
        print(f"  - {table[0]}")

    conn.close()

    print("\n数据库初始化完成!")
    print(f"数据库位置: {db_path.absolute()}")
    print(f"文件大小: {db_path.stat().st_size} bytes")

    return True


def insert_sample_data():
    """插入示例数据"""
    db_path = Path("./data/agentforge.db")

    if not db_path.exists():
        print("数据库不存在，请先运行数据库创建")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("插入示例数据...")

    # 示例用户
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, display_name, email)
        VALUES (?, ?, ?, ?)
    """, ("user_demo", "demo_user", "演示用户", "demo@example.com"))

    # 示例会话
    cursor.execute("""
        INSERT OR IGNORE INTO user_sessions (session_id, user_id, title, model_name)
        VALUES (?, ?, ?, ?)
    """, ("session_demo", "user_demo", "示例对话", "gpt-3.5-turbo"))

    # 示例消息
    cursor.execute("""
        INSERT OR IGNORE INTO user_messages (message_id, session_id, user_id, role, content)
        VALUES (?, ?, ?, ?, ?)
    """, ("msg_demo_1", "session_demo", "user_demo", "user", "你好，AgentForge！"))

    cursor.execute("""
        INSERT OR IGNORE INTO user_messages (message_id, session_id, user_id, role, content, model_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "msg_demo_2", "session_demo", "user_demo", "assistant", "你好！我是AgentForge，很高兴为你服务！", "gpt-3.5-turbo"))

    conn.commit()
    conn.close()

    print("示例数据插入完成")
    return True


def main():
    """主函数"""
    print("AgentForge 数据库初始化工具")
    print("=" * 40)

    try:
        # 创建数据库
        success = create_database()

        if success:
            # 询问是否插入示例数据
            print("\n是否要插入示例数据? (y/n): ", end="")
            try:
                choice = input().strip().lower()
                if choice in ['y', 'yes']:
                    insert_sample_data()
            except EOFError:
                # 在非交互环境中跳过
                pass

            print("\n数据库初始化成功!")
            print("\n下一步:")
            print("1. 启动API服务器: python scripts/start_server.py --mode api")
            print("2. 运行演示脚本: python examples/user_session_demo.py")
            print("3. 启动Web界面: streamlit run src/webui/streamlit_app.py")

    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        return False

    return True


if __name__ == "__main__":
    main()
