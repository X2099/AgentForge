# -*- coding: utf-8 -*-
"""
知识库元数据库管理
"""
import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseDatabase:
    """知识库SQLite数据库管理器"""

    def __init__(self, db_path: str = "./data/kb_metadata.db"):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_bases (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- 配置信息
                    splitter_type TEXT DEFAULT 'recursive',
                    chunk_size INTEGER DEFAULT 500,
                    chunk_overlap INTEGER DEFAULT 50,

                    -- 嵌入配置
                    embedder_type TEXT DEFAULT 'bge',
                    embedder_model TEXT,

                    -- 向量存储配置
                    vector_store_type TEXT DEFAULT 'chroma',
                    collection_name TEXT,
                    persist_directory TEXT,

                    -- 语义分割配置 (JSON)
                    semantic_config TEXT,

                    -- 完整配置 (JSON)
                    full_config TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS kb_statistics (
                    kb_id TEXT PRIMARY KEY REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                    document_count INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    last_updated TIMESTAMP,
                    vector_count INTEGER DEFAULT 0,
                    avg_document_length REAL DEFAULT 0.0,
                    total_tokens INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kb_id TEXT REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                    operation_type TEXT, -- 'add', 'delete', 'update', 'clear'
                    file_path TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    chunk_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- 操作结果
                    status TEXT DEFAULT 'success', -- 'success', 'failed', 'partial'
                    error_message TEXT,

                    -- 性能统计
                    processing_time REAL,
                    tokens_processed INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kb_id TEXT REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                    query_text TEXT,
                    result_count INTEGER DEFAULT 0,
                    search_time REAL, -- 搜索耗时(秒)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- 高级搜索参数 (JSON)
                    search_params TEXT
                )
            """)

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_name ON knowledge_bases(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_operations_kb_id ON document_operations(kb_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_operations_created ON document_operations(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_search_kb_id ON search_history(kb_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_search_created ON search_history(created_at)")

            conn.commit()

    # ==================== 知识库基本操作 ====================

    def create_knowledge_base(self, kb_config: Dict[str, Any]) -> bool:
        """创建知识库记录"""
        try:
            kb_id = kb_config.get("name", f"kb_{int(datetime.now().timestamp())}")
            semantic_config = {}
            if kb_config.get("splitter_type") == "semantic":
                semantic_config = {
                    "semantic_threshold": kb_config.get("semantic_threshold", 0.5),
                    "semantic_model": kb_config.get("semantic_model", "paraphrase-multilingual-MiniLM-L12-v2")
                }

            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO knowledge_bases
                    (id, name, description, splitter_type, chunk_size, chunk_overlap,
                     embedder_type, embedder_model, vector_store_type, collection_name,
                     persist_directory, semantic_config, full_config, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    kb_id,
                    kb_config.get("name", kb_id),
                    kb_config.get("description", ""),
                    kb_config.get("splitter_type", "recursive"),
                    kb_config.get("chunk_size", 500),
                    kb_config.get("chunk_overlap", 50),
                    kb_config.get("embedder", {}).get("embedder_type", "bge"),
                    kb_config.get("embedder", {}).get("model", ""),
                    kb_config.get("vector_store", {}).get("store_type", "chroma"),
                    kb_config.get("vector_store", {}).get("collection_name", kb_id),
                    kb_config.get("vector_store", {}).get("persist_directory", f"./data/vector_stores/{kb_id}"),
                    json.dumps(semantic_config),
                    json.dumps(kb_config)
                ))

                # 初始化统计信息
                conn.execute("""
                    INSERT OR IGNORE INTO kb_statistics (kb_id)
                    VALUES (?)
                """, (kb_id,))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"创建知识库记录失败: {str(e)}")
            return False

    def get_knowledge_base(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """获取知识库配置"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT * FROM knowledge_bases WHERE id = ? OR name = ?
                """, (kb_id, kb_id))

                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    kb_data = dict(zip(columns, row))

                    # 解析JSON字段
                    if kb_data.get("semantic_config"):
                        kb_data["semantic_config"] = json.loads(kb_data["semantic_config"])
                    if kb_data.get("full_config"):
                        kb_data["full_config"] = json.loads(kb_data["full_config"])

                    return kb_data
                return None

        except Exception as e:
            logger.error(f"获取知识库失败: {str(e)}")
            return None

    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """列出所有知识库"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT kb.*, stats.document_count, stats.last_updated
                    FROM knowledge_bases kb
                    LEFT JOIN kb_statistics stats ON kb.id = stats.kb_id
                    ORDER BY kb.created_at DESC
                """)

                kbs = []
                for row in cursor.fetchall():
                    columns = [desc[0] for desc in cursor.description]
                    kb_data = dict(zip(columns, row))

                    # 解析JSON字段
                    if kb_data.get("semantic_config"):
                        kb_data["semantic_config"] = json.loads(kb_data["semantic_config"])
                    if kb_data.get("full_config"):
                        kb_data["full_config"] = json.loads(kb_data["full_config"])

                    kbs.append(kb_data)

                return kbs

        except Exception as e:
            logger.error(f"列出知识库失败: {str(e)}")
            return []

    def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库记录"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("DELETE FROM knowledge_bases WHERE id = ? OR name = ?", (kb_id, kb_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"删除知识库失败: {str(e)}")
            return False

    # ==================== 统计信息操作 ====================

    def update_statistics(self, kb_id: str, stats: Dict[str, Any]) -> bool:
        """更新知识库统计信息"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO kb_statistics
                    (kb_id, document_count, total_chunks, last_updated,
                     vector_count, avg_document_length, total_tokens)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    kb_id,
                    stats.get("document_count", 0),
                    stats.get("total_chunks", 0),
                    datetime.now().isoformat(),
                    stats.get("vector_count", 0),
                    stats.get("avg_document_length", 0.0),
                    stats.get("total_tokens", 0)
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"更新统计信息失败: {str(e)}")
            return False

    def get_statistics(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """获取知识库统计信息"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT * FROM kb_statistics WHERE kb_id = ?
                """, (kb_id,))

                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None

        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return None

    # ==================== 文档操作历史 ====================

    def record_document_operation(self, kb_id: str, operation: Dict[str, Any]) -> bool:
        """记录文档操作"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    INSERT INTO document_operations
                    (kb_id, operation_type, file_path, file_name, file_size,
                     chunk_count, status, error_message, processing_time, tokens_processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kb_id,
                    operation.get("operation_type", "add"),
                    operation.get("file_path", ""),
                    operation.get("file_name", ""),
                    operation.get("file_size", 0),
                    operation.get("chunk_count", 0),
                    operation.get("status", "success"),
                    operation.get("error_message", ""),
                    operation.get("processing_time", 0.0),
                    operation.get("tokens_processed", 0)
                ))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"记录文档操作失败: {str(e)}")
            return False

    def get_operation_history(self, kb_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取文档操作历史"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT * FROM document_operations
                    WHERE kb_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (kb_id, limit))

                operations = []
                for row in cursor.fetchall():
                    columns = [desc[0] for desc in cursor.description]
                    operations.append(dict(zip(columns, row)))

                return operations

        except Exception as e:
            logger.error(f"获取操作历史失败: {str(e)}")
            return []

    # ==================== 搜索历史 ====================

    def record_search(self, kb_id: str, search_data: Dict[str, Any]) -> bool:
        """记录搜索历史"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    INSERT INTO search_history
                    (kb_id, query_text, result_count, search_time, search_params)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    kb_id,
                    search_data.get("query_text", ""),
                    search_data.get("result_count", 0),
                    search_data.get("search_time", 0.0),
                    json.dumps(search_data.get("search_params", {}))
                ))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"记录搜索历史失败: {str(e)}")
            return False

    def get_search_history(self, kb_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT * FROM search_history
                    WHERE kb_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (kb_id, limit))

                searches = []
                for row in cursor.fetchall():
                    columns = [desc[0] for desc in cursor.description]
                    search_data = dict(zip(columns, row))
                    # 解析搜索参数
                    if search_data.get("search_params"):
                        search_data["search_params"] = json.loads(search_data["search_params"])
                    searches.append(search_data)

                return searches

        except Exception as e:
            logger.error(f"获取搜索历史失败: {str(e)}")
            return []

    # ==================== 数据迁移 ====================

    def migrate_from_filesystem(self, config_dir: Path) -> bool:
        """从文件系统迁移数据到数据库"""
        try:
            logger.info("开始从文件系统迁移数据到数据库...")

            config_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.json"))
            migrated_count = 0

            for config_file in config_files:
                try:
                    import yaml

                    if config_file.suffix == ".yaml":
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f)
                    else:
                        import json
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)

                    kb_name = config.get("name", config_file.stem)

                    # 检查是否已存在
                    existing = self.get_knowledge_base(kb_name)
                    if existing:
                        logger.info(f"知识库 {kb_name} 已存在，跳过迁移")
                        continue

                    # 创建数据库记录
                    if self.create_knowledge_base(config):
                        logger.info(f"成功迁移知识库: {kb_name}")
                        migrated_count += 1
                    else:
                        logger.error(f"迁移知识库失败: {kb_name}")

                except Exception as e:
                    logger.error(f"迁移配置文件失败 {config_file}: {str(e)}")

            logger.info(f"数据迁移完成，共迁移 {migrated_count} 个知识库")
            return True

        except Exception as e:
            logger.error(f"数据迁移失败: {str(e)}")
            return False

    # ==================== 数据库维护 ====================

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # 知识库统计
                kb_count = conn.execute("SELECT COUNT(*) FROM knowledge_bases").fetchone()[0]

                # 文档操作统计
                op_stats = conn.execute("""
                    SELECT operation_type, COUNT(*) as count
                    FROM document_operations
                    GROUP BY operation_type
                """).fetchall()

                # 搜索统计
                search_count = conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]

                # 数据库文件大小
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

                return {
                    "knowledge_bases_count": kb_count,
                    "operations_stats": dict(op_stats),
                    "search_count": search_count,
                    "database_size_mb": db_size / (1024 * 1024),
                    "last_updated": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"获取数据库统计失败: {str(e)}")
            return {}

    def cleanup_old_data(self, days: int = 90) -> bool:
        """清理旧的搜索历史和操作记录"""
        try:
            cutoff_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) -
                           timedelta(days=days)).isoformat()

            with sqlite3.connect(str(self.db_path)) as conn:
                # 清理旧的搜索历史
                search_deleted = conn.execute("""
                    DELETE FROM search_history
                    WHERE created_at < ?
                """, (cutoff_date,)).rowcount

                # 清理旧的操作记录（保留最近的）
                op_deleted = conn.execute("""
                    DELETE FROM document_operations
                    WHERE created_at < ? AND id NOT IN (
                        SELECT id FROM document_operations
                        WHERE kb_id IN (SELECT id FROM knowledge_bases)
                        ORDER BY created_at DESC
                        LIMIT 1000  -- 为每个知识库保留最近1000条记录
                    )
                """, (cutoff_date,)).rowcount

                conn.commit()

                logger.info(f"清理完成: 删除 {search_deleted} 条搜索记录, {op_deleted} 条操作记录")
                return True

        except Exception as e:
            logger.error(f"清理旧数据失败: {str(e)}")
            return False
