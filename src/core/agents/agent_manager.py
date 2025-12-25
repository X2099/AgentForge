# -*- coding: utf-8 -*-
"""
@File    : agent_manager.py
@Time    : 2025/12/9 12:28
@Desc    : 
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

import sqlite3

from ...memory import CheckpointMemoryManager, CheckpointMemoryConfig


class AgentManager:
    """智能体管理器"""

    def __init__(self,
                 db_path: str = "./data/agentforge.db"):
        """
        初始化智能体管理器

        Args:
            db_path: 数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.memory_config = CheckpointMemoryConfig()
        # 使用默认的MemorySaver
        from langgraph.checkpoint.memory import MemorySaver
        self.memory_config.checkpointer = MemorySaver()
        self.memory_manager = CheckpointMemoryManager(
            checkpointer=self.memory_config.checkpointer,
            config=self.memory_config
        )

        # 活跃用户会话
        self.active_user_sessions: Dict[str, Dict[str, Any]] = {}

        # 初始化数据库
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,  -- 密码哈希
                display_name TEXT,
                avatar_url TEXT,
                preferences TEXT,  -- JSON格式的偏好设置
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                last_login_at TIMESTAMP
            )
        """)

        # 创建用户对话会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,  -- 会话标题
                model_name TEXT,  -- 使用的模型
                kb_name TEXT,  -- 使用的知识库
                graph_type TEXT, -- 工作流/Agent类型
                tools_config TEXT,  -- 工具配置，JSON格式
                total_messages INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                metadata TEXT,  -- 额外元数据，JSON格式
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    # ===== 用户管理方法 =====

    def create_user(self,
                    username: str,
                    password: str,
                    email: str = None,
                    display_name: str = None) -> str:
        """创建用户"""
        import uuid
        import hashlib
        user_id = str(uuid.uuid4())

        # 对密码进行哈希处理（生产环境应该使用bcrypt）
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (user_id, username, email, password_hash, display_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            username,
            email,
            password_hash,
            display_name or username,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return user_id

    def verify_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户密码"""
        import hashlib

        user = self.get_user_by_username(username)
        if not user:
            return None

        # 验证密码哈希
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user.get('password_hash') == password_hash:
            return user

        return None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, username, email, password_hash, display_name, avatar_url,
                   preferences, created_at, updated_at, is_active, last_login_at
            FROM users WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "email": row[2],
                "password_hash": row[3],  # 内部使用，不返回给前端
                "display_name": row[4],
                "avatar_url": row[5],
                "preferences": row[6],
                "created_at": row[7],
                "updated_at": row[8],
                "is_active": bool(row[9]),
                "last_login_at": row[10]
            }
        return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, username, email, password_hash, display_name, avatar_url,
                   preferences, created_at, updated_at, is_active, last_login_at
            FROM users WHERE username = ? AND is_active = 1
        """, (username,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "email": row[2],
                "password_hash": row[3],  # 内部使用，不返回给前端
                "display_name": row[4],
                "avatar_url": row[5],
                "preferences": row[6],
                "created_at": row[7],
                "updated_at": row[8],
                "is_active": bool(row[9]),
                "last_login_at": row[10]
            }
        return None

    def update_user_login(self, user_id: str):
        """更新用户最后登录时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET last_login_at = ?, updated_at = ?
            WHERE user_id = ?
        """, (
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            user_id
        ))

        conn.commit()
        conn.close()

    # ===== 用户会话管理方法 =====

    def create_user_session(self,
                            user_id: str,
                            title: str = None,
                            model_name: str = None,
                            kb_name: str = None,
                            graph_type: str = None,
                            tools_config: List[str] = None) -> str:
        """创建用户会话"""
        import uuid
        session_id = str(uuid.uuid4())

        if title is None:
            title = f"对话 {datetime.now().strftime('%m-%d %H:%M')}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_sessions (session_id, user_id, title, model_name, kb_name, graph_type, tools_config, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            user_id,
            title,
            model_name,
            kb_name,
            graph_type,
            json.dumps(tools_config or []),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return session_id

    def get_user_sessions(self, user_id: str, graph_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户的会话列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, user_id, title, model_name, kb_name, tools_config,
                   total_messages, created_at, updated_at, is_active, metadata
            FROM user_sessions
            WHERE user_id = ? AND graph_type = ? AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT ?
        """, (user_id, graph_type, limit))

        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            sessions.append({
                "session_id": row[0],
                "user_id": row[1],
                "title": row[2],
                "model_name": row[3],
                "kb_name": row[4],
                "tools_config": json.loads(row[5]) if row[5] else [],
                "total_messages": row[6],
                "created_at": row[7],
                "updated_at": row[8],
                "is_active": bool(row[9]),
                "metadata": row[10]
            })

        return sessions

    def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取单个会话详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, user_id, title, model_name, kb_name, tools_config,
                   total_messages, created_at, updated_at, is_active, metadata
            FROM user_sessions WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "session_id": row[0],
                "user_id": row[1],
                "title": row[2],
                "model_name": row[3],
                "kb_name": row[4],
                "tools_config": json.loads(row[5]) if row[5] else [],
                "total_messages": row[6],
                "created_at": row[7],
                "updated_at": row[8],
                "is_active": bool(row[9]),
                "metadata": row[10]
            }
        return None

    def update_user_session(self,
                            session_id: str,
                            title: str = None,
                            total_messages: int = None,
                            metadata: Dict[str, Any] = None):
        """更新用户会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)

        if total_messages is not None:
            updates.append("total_messages = ?")
            params.append(total_messages)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())

            query = f"UPDATE user_sessions SET {', '.join(updates)} WHERE session_id = ?"
            params.append(session_id)

            cursor.execute(query, params)
            conn.commit()

        conn.close()

    def delete_user_session(self, session_id: str):
        """删除用户会话（软删除）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_sessions
            SET is_active = 0, updated_at = ?
            WHERE session_id = ?
        """, (
            datetime.now().isoformat(),
            session_id
        ))

        conn.commit()
        conn.close()
