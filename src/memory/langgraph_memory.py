# -*- coding: utf-8 -*-
"""
@File    : langgraph_memory.py
@Time    : 2025/12/9 12:22
@Desc    : 
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
from enum import Enum

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver
import sqlite3


class MemoryStoreType(str, Enum):
    """记忆存储类型"""
    SQLITE = "sqlite"
    MEMORY = "memory"
    POSTGRES = "postgres"


@dataclass
class MemoryConfig:
    """记忆配置"""
    store_type: MemoryStoreType = MemoryStoreType.SQLITE
    db_path: str = "./data/memory/memory.db"
    table_name: str = "agent_memories"
    max_memories_per_session: int = 100
    memory_ttl_hours: Optional[int] = None  # None表示永不过期


class LangGraphMemoryStore:
    """基于LangGraph Checkpointer的记忆存储"""

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.checkpointer: Optional[BaseCheckpointSaver] = None
        self._initialize_store()

    def _initialize_store(self):
        """初始化存储"""
        if self.config.store_type == MemoryStoreType.SQLITE:
            self.checkpointer = SqliteSaver.from_conn(
                conn=sqlite3.connect(self.config.db_path),
                table_name=self.config.table_name
            )
        elif self.config.store_type == MemoryStoreType.MEMORY:
            self.checkpointer = MemorySaver()
        else:
            raise ValueError(f"Unsupported store type: {self.config.store_type}")

        # 初始化数据库表
        self._init_tables()

    def _init_tables(self):
        """初始化数据库表（增强功能）"""
        if self.config.store_type == MemoryStoreType.SQLITE:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()

            # 创建记忆元数据表
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.config.table_name}_metadata (
                    thread_id TEXT,
                    memory_id TEXT PRIMARY KEY,
                    memory_type TEXT,
                    importance INTEGER,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    metadata TEXT,
                    FOREIGN KEY (thread_id) REFERENCES {self.config.table_name}(thread_id)
                )
            """)

            # 创建记忆索引表
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.config.table_name}_index (
                    memory_id TEXT,
                    keyword TEXT,
                    embedding BLOB,
                    PRIMARY KEY (memory_id, keyword),
                    FOREIGN KEY (memory_id) REFERENCES {self.config.table_name}_metadata(memory_id)
                )
            """)

            conn.commit()
            conn.close()

    async def save_memory(self,
                          thread_id: str,
                          state: Dict[str, Any],
                          metadata: Optional[Dict[str, Any]] = None,
                          config: Optional[Dict[str, Any]] = None) -> str:
        """保存记忆"""
        # 生成记忆ID
        memory_id = hashlib.md5(
            f"{thread_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()

        # 准备元数据
        memory_metadata = {
            "memory_id": memory_id,
            "created_at": datetime.now().isoformat(),
            "accessed_at": datetime.now().isoformat(),
            "access_count": 0,
            "type": metadata.get("type", "conversation") if metadata else "conversation",
            "importance": metadata.get("importance", 1) if metadata else 1,
            "tags": metadata.get("tags", []) if metadata else [],
            "summary": metadata.get("summary", "") if metadata else ""
        }

        # 保存到checkpointer
        config = config or {}
        await self.checkpointer.aput(
            config,
            thread_id,
            checkpoint={
                "state": state,
                "metadata": memory_metadata
            }
        )

        # 保存额外元数据到SQLite（如果使用SQLite）
        if self.config.store_type == MemoryStoreType.SQLITE:
            self._save_metadata(thread_id, memory_id, memory_metadata)

        return memory_id

    def _save_metadata(self, thread_id: str, memory_id: str, metadata: Dict[str, Any]):
        """保存元数据到SQLite"""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            INSERT INTO {self.config.table_name}_metadata 
            (thread_id, memory_id, memory_type, importance, created_at, accessed_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            thread_id,
            memory_id,
            metadata["type"],
            metadata["importance"],
            metadata["created_at"],
            metadata["accessed_at"],
            json.dumps(metadata)
        ))

        conn.commit()
        conn.close()

    async def load_memory(self,
                          thread_id: str,
                          memory_id: Optional[str] = None,
                          config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """加载记忆"""
        try:
            checkpoint = await self.checkpointer.aget(
                config or {},
                thread_id,
                checkpoint_id=memory_id
            )

            if checkpoint:
                # 更新访问记录
                if self.config.store_type == MemoryStoreType.SQLITE:
                    self._update_access_record(memory_id or thread_id)

                return checkpoint
        except Exception as e:
            print(f"Error loading memory: {str(e)}")

        return None

    def _update_access_record(self, memory_id: str):
        """更新访问记录"""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            UPDATE {self.config.table_name}_metadata 
            SET accessed_at = ?, access_count = access_count + 1
            WHERE memory_id = ?
        """, (datetime.now().isoformat(), memory_id))

        conn.commit()
        conn.close()

    async def search_memories(self,
                              thread_id: str,
                              query: Optional[str] = None,
                              memory_type: Optional[str] = None,
                              limit: int = 10) -> List[Dict[str, Any]]:
        """搜索记忆"""
        memories = []

        if self.config.store_type == MemoryStoreType.SQLITE:
            # SQLite支持高级搜索
            memories = self._search_sqlite(thread_id, query, memory_type, limit)
        else:
            # 内存存储简单搜索
            memories = await self._search_memory(thread_id, limit)

        return memories

    def _search_sqlite(self,
                       thread_id: str,
                       query: Optional[str],
                       memory_type: Optional[str],
                       limit: int) -> List[Dict[str, Any]]:
        """SQLite搜索"""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()

        sql = f"""
            SELECT memory_id, memory_type, importance, created_at, accessed_at, access_count, metadata
            FROM {self.config.table_name}_metadata
            WHERE thread_id = ?
        """
        params = [thread_id]

        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)

        if query:
            sql += " AND metadata LIKE ?"
            params.append(f"%{query}%")

        sql += " ORDER BY importance DESC, accessed_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        memories = []
        for row in rows:
            memories.append({
                "memory_id": row[0],
                "type": row[1],
                "importance": row[2],
                "created_at": row[3],
                "accessed_at": row[4],
                "access_count": row[5],
                "metadata": json.loads(row[6]) if row[6] else {}
            })

        conn.close()
        return memories

    async def _search_memory(self, thread_id: str, limit: int) -> List[Dict[str, Any]]:
        """内存存储搜索"""
        # 对于内存存储，我们只能获取最新的记忆
        memories = []

        # 尝试获取所有检查点
        try:
            checkpoints = await self.checkpointer.alist(thread_id)

            for cp in checkpoints[:limit]:
                checkpoint = await self.checkpointer.aget({}, thread_id, cp)
                if checkpoint:
                    memories.append({
                        "checkpoint_id": cp,
                        "metadata": checkpoint.get("metadata", {})
                    })
        except:
            pass

        return memories

    async def delete_memory(self,
                            thread_id: str,
                            memory_id: str,
                            config: Optional[Dict[str, Any]] = None):
        """删除记忆"""
        try:
            await self.checkpointer.adelete(config or {}, thread_id, memory_id)

            if self.config.store_type == MemoryStoreType.SQLITE:
                self._delete_metadata(memory_id)
        except Exception as e:
            print(f"Error deleting memory: {str(e)}")

    def _delete_metadata(self, memory_id: str):
        """删除元数据"""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()

        cursor.execute(f"DELETE FROM {self.config.table_name}_metadata WHERE memory_id = ?", (memory_id,))
        cursor.execute(f"DELETE FROM {self.config.table_name}_index WHERE memory_id = ?", (memory_id,))

        conn.commit()
        conn.close()
