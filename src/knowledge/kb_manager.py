# -*- coding: utf-8 -*-
"""
@File    : kb_manager.py
@Time    : 2025/12/8 17:22
@Desc    : 
"""
import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import time
import logging
import threading

from .document_loaders import Document
from .knowledge_base import KnowledgeBase
from .kb_database import KnowledgeBaseDatabase

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self, config_dir: str = "./configs/knowledge_bases", use_database: bool = True):
        """
        初始化知识库管理器

        Args:
            config_dir: 配置文件目录
            use_database: 是否使用数据库存储元数据
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.use_database = use_database
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}

        # 统计信息缓存
        self.stats_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_lock = threading.RLock()
        self.cache_ttl = 300  # 缓存5分钟

        # 初始化数据库
        if self.use_database:
            self.db = KnowledgeBaseDatabase()
            # 首次运行时从文件系统迁移数据
            self._migrate_from_filesystem()
        else:
            self.db = None

        self.load_configs()

    def load_configs(self):
        """加载所有知识库配置"""
        if self.use_database and self.db:
            # 从数据库加载
            kb_configs = self.db.list_knowledge_bases()
            for kb_data in kb_configs:
                try:
                    # 从full_config字段获取完整配置
                    config = kb_data.get("full_config", {})
                    if not config:
                        # 如果没有完整配置，从数据库字段构建
                        config = self._build_config_from_db_data(kb_data)

                    kb_name = config.get("name", kb_data["name"])
                    self.create_knowledge_base(config, load_existing=True)

                except Exception as e:
                    logger.error(f"从数据库加载知识库失败 {kb_data.get('name', 'unknown')}: {str(e)}")
        else:
            # 从文件系统加载（向后兼容）
            config_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.json"))

            for config_file in config_files:
                try:
                    if config_file.suffix == ".yaml":
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f)
                    else:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)

                    kb_name = config.get("name", config_file.stem)
                    self.create_knowledge_base(config, load_existing=True)

                except Exception as e:
                    logger.error(f"加载配置失败 {config_file}: {str(e)}")

    def _migrate_from_filesystem(self):
        """从文件系统迁移数据到数据库"""
        if not self.db:
            return

        try:
            # 检查是否已经迁移过
            if self.db.list_knowledge_bases():
                logger.info("数据库中已有数据，跳过迁移")
                return

            # 执行迁移
            if self.db.migrate_from_filesystem(self.config_dir):
                logger.info("数据迁移完成")
            else:
                logger.error("数据迁移失败")

        except Exception as e:
            logger.error(f"迁移过程出错: {str(e)}")

    def _build_config_from_db_data(self, kb_data: Dict[str, Any]) -> Dict[str, Any]:
        """从数据库数据构建配置字典"""
        config = {
            "name": kb_data["name"],
            "description": kb_data.get("description", ""),
            "splitter_type": kb_data.get("splitter_type", "recursive"),
            "chunk_size": kb_data.get("chunk_size", 500),
            "chunk_overlap": kb_data.get("chunk_overlap", 50),
            "embedder": {
                "embedder_type": kb_data.get("embedder_type", "bge"),
                "model": kb_data.get("embedder_model", "")
            },
            "vector_store": {
                "store_type": kb_data.get("vector_store_type", "chroma"),
                "collection_name": kb_data.get("collection_name"),
                "persist_directory": kb_data.get("persist_directory")
            }
        }

        # 添加语义分割配置
        if kb_data.get("splitter_type") == "semantic":
            semantic_config = kb_data.get("semantic_config", {})
            if isinstance(semantic_config, str):
                semantic_config = json.loads(semantic_config)
            config.update(semantic_config)

        return config

    def create_knowledge_base(self,
                              config: Dict[str, Any],
                              load_existing: bool = True) -> KnowledgeBase:
        """
        创建知识库

        Args:
            config: 知识库配置
            load_existing: 是否加载已存在的向量存储

        Returns:
            知识库实例
        """
        kb_name = config["name"]

        if kb_name in self.knowledge_bases:
            print(f"知识库 '{kb_name}' 已存在，使用现有实例")
            return self.knowledge_bases[kb_name]

        # 创建知识库
        kb = KnowledgeBase(config)

        # 如果向量存储已存在且配置了加载现有，可以在这里加载
        if load_existing:
            # 检查向量存储是否存在
            vector_store_config = config.get("vector_store", {})
            persist_dir = vector_store_config.get("persist_directory", f"./data/vector_stores/{kb_name}")

            if Path(persist_dir).exists():
                print(f"检测到已存在的向量存储，知识库 '{kb_name}' 已加载")
                # 这里可以加载文档数量等统计信息
                # 实际应用中需要从向量存储中获取

        self.knowledge_bases[kb_name] = kb

        # 保存配置
        self._save_config(kb_name, config)

        # 保存到数据库
        if self.use_database and self.db:
            if not self.db.create_knowledge_base(config):
                logger.warning(f"保存知识库 {kb_name} 到数据库失败")

        return kb

    def get_knowledge_base(self, name: str) -> Optional[KnowledgeBase]:
        """获取知识库"""
        return self.knowledge_bases.get(name)

    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """列出所有知识库"""
        result = []

        for name, kb in self.knowledge_bases.items():
            stats = self._get_cached_stats(name, kb)
            result.append({
                "name": name,
                "description": stats.get("description", ""),
                "document_count": stats.get("document_count", 0),
                "last_updated": stats.get("last_updated"),
                "is_initialized": stats.get("is_initialized", False)
            })

        return result

    def _get_cached_stats(self, name: str, kb: KnowledgeBase) -> Dict[str, Any]:
        """获取缓存的统计信息"""
        with self.cache_lock:
            now = time.time()

            # 检查缓存是否有效
            if name in self.stats_cache:
                cached_data = self.stats_cache[name]
                if now - cached_data.get("timestamp", 0) < self.cache_ttl:
                    return cached_data["stats"]

            # 缓存失效或不存在，重新获取（使用快速模式）
            stats = kb.get_stats(detailed=False)

            # 存储到缓存
            self.stats_cache[name] = {
                "stats": stats,
                "timestamp": now
            }

            return stats

    def invalidate_stats_cache(self, name: Optional[str] = None):
        """使统计信息缓存失效"""
        with self.cache_lock:
            if name:
                self.stats_cache.pop(name, None)
            else:
                self.stats_cache.clear()

    def delete_knowledge_base(self, name: str, delete_data: bool = False):
        """
        删除知识库

        Args:
            name: 知识库名称
            delete_data: 是否删除数据文件
        """
        if name not in self.knowledge_bases:
            raise ValueError(f"知识库 '{name}' 不存在")

        kb = self.knowledge_bases[name]

        if delete_data:
            # 删除向量存储数据
            stats = kb.get_stats()
            vector_store_stats = stats.get("vector_store", {})
            persist_dir = vector_store_stats.get("persist_directory")

            if persist_dir and Path(persist_dir).exists():
                import shutil
                try:
                    shutil.rmtree(persist_dir)
                    print(f"已删除向量存储数据: {persist_dir}")
                except Exception as e:
                    print(f"删除向量存储数据失败: {str(e)}")

        # 删除配置
        config_file = self.config_dir / f"{name}.yaml"
        if config_file.exists():
            config_file.unlink()

        # 从数据库删除
        if self.use_database and self.db:
            if not self.db.delete_knowledge_base(name):
                logger.warning(f"从数据库删除知识库 {name} 失败")

        # 从内存中移除
        del self.knowledge_bases[name]

        # 使缓存失效
        self.invalidate_stats_cache(name)

    def _save_config(self, name: str, config: Dict[str, Any]):
        """保存配置到文件"""
        config_file = self.config_dir / f"{name}.yaml"

        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def bulk_add_documents(self,
                           kb_name: str,
                           file_paths: List[str],
                           **kwargs) -> Dict[str, Any]:
        """
        批量添加文档到知识库

        Args:
            kb_name: 知识库名称
            file_paths: 文件路径列表
            **kwargs: 其他参数传递给add_documents

        Returns:
            处理统计信息
        """
        if kb_name not in self.knowledge_bases:
            raise ValueError(f"知识库 '{kb_name}' 不存在")

        kb = self.knowledge_bases[kb_name]

        # 记录开始时间
        start_time = time.time()

        # 执行文档添加
        stats = kb.add_documents(file_paths, **kwargs)

        # 记录到数据库
        if self.use_database and self.db:
            # 更新统计信息
            self.db.update_statistics(kb_name, {
                "document_count": stats.get("document_count", 0),
                "total_chunks": stats.get("total_chunks", 0),
                "last_updated": datetime.now().isoformat(),
                "vector_count": stats.get("valid_chunks", 0)
            })

            # 记录文档操作历史
            processing_time = time.time() - start_time
            for file_path in file_paths:
                file_path_obj = Path(file_path)
                operation = {
                    "operation_type": "add",
                    "file_path": str(file_path),
                    "file_name": file_path_obj.name,
                    "file_size": file_path_obj.stat().st_size if file_path_obj.exists() else 0,
                    "chunk_count": 0,  # 这里可以根据实际处理情况计算
                    "status": "success" if stats.get("processed_files", 0) > 0 else "failed",
                    "processing_time": processing_time,
                    "tokens_processed": 0  # 可以后续扩展
                }
                self.db.record_document_operation(kb_name, operation)

        # 使缓存失效
        self.invalidate_stats_cache(kb_name)

        return stats

    def search(self,
               kb_name: str,
               query: str,
               k: int = 4,
               filter_dict: Optional[Dict] = None) -> List[Document]:
        """
        搜索知识库

        Args:
            kb_name: 知识库名称
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件

        Returns:
            相关文档列表
        """
        if kb_name not in self.knowledge_bases:
            raise ValueError(f"知识库 '{kb_name}' 不存在")

        kb = self.knowledge_bases[kb_name]

        # 记录搜索开始时间
        start_time = time.time()

        # 执行搜索
        results = kb.search(query, k, filter_dict)

        # 记录搜索历史到数据库
        if self.use_database and self.db:
            search_time = time.time() - start_time
            search_data = {
                "query_text": query,
                "result_count": len(results),
                "search_time": search_time,
                "search_params": {
                    "k": k,
                    "filter_dict": filter_dict
                }
            }
            self.db.record_search(kb_name, search_data)

        return results
