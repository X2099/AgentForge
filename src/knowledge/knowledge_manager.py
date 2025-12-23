# -*- coding: utf-8 -*-
"""
@File    : knowledge_manager.py
@Time    : 2025/12/8 17:22
@Desc    : 
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import time
import logging
import threading

from langchain_core.documents import Document

from .knowledge_models import SplitterType, EmbedderType, VectorStoreType, KnowledgeConfig
from .knowledge_base import KnowledgeBase
from .knowledge_database import KnowledgeBaseDatabase

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self):
        """
        初始化知识库管理器
        """

        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        # 统计信息缓存
        self.stats_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_lock = threading.RLock()
        self.cache_ttl = 300  # 缓存5分钟
        # 初始化数据库
        self.db = KnowledgeBaseDatabase()
        self.load_configs()

    def load_configs(self):
        """从数据库加载所有知识库配置"""

        kb_configs = self.db.list_knowledge_bases()
        for kb_data in kb_configs:
            kb_data.pop("id", None)
            kb_data.pop("created_at", None)
            kb_data.pop("updated_at", None)
            kb_data["splitter_type"] = SplitterType(kb_data["splitter_type"])
            kb_data["embedding_type"] = EmbedderType(kb_data["embedding_type"])
            kb_data["vectorstore_type"] = VectorStoreType(kb_data["vectorstore_type"])
            config = KnowledgeConfig(**kb_data)
            try:
                self.create_knowledge_base(config)
            except Exception as e:
                logger.error(f"从数据库加载知识库失败 {kb_data.get('name', 'unknown')}: {str(e)}")

    def load_state(self, name: str) -> dict:
        """从数据库加载知识库状态"""
        statistics = self.db.get_statistics(name)
        return statistics if statistics else {}

    def create_knowledge_base(self, config: KnowledgeConfig) -> KnowledgeBase:
        """
        创建知识库

        Args:
            config: 知识库配置
        Returns:
            知识库实例
        """
        kb_name = config.name

        if kb_name in self.knowledge_bases:
            print(f"知识库 '{kb_name}' 已存在，使用现有实例")
            return self.knowledge_bases[kb_name]

        # 创建知识库
        kb = KnowledgeBase(config)

        # 从数据库中加载知识库状态
        state = self.load_state(kb_name)
        kb.load_state(state)
        self.knowledge_bases[kb_name] = kb

        # 保存配置到数据库
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
            stats = kb.get_stats()
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

        # 从数据库删除
        if not self.db.delete_knowledge_base(name):
            logger.warning(f"从数据库删除知识库 {name} 失败")

        # 从内存中移除
        del self.knowledge_bases[name]

        # 使缓存失效
        self.invalidate_stats_cache(name)

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

        # 更新统计信息到数据库
        self.db.update_statistics(kb_name, {
            "document_count": stats.get("document_count", 0),
            "total_chunks": stats.get("total_chunks", 0),
            "is_initialized": stats.get("is_initialized", False),
            "last_updated": stats.get("last_updated", datetime.now()),
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
