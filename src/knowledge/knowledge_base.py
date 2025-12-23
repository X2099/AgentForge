# -*- coding: utf-8 -*-
"""
@File    : knowledge_base.py
@Time    : 2025/12/9
@Desc    : 基于LangChain标准组件的知识库实现
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from .knowledge_models import KnowledgeConfig
from .langchain.splitters import SplitterFactory
from .langchain.loaders import DocumentLoaderFactory
from .langchain.embeddings import EmbedderFactory
from .vectorstores import VectorStoreFactory

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    基于LangChain标准组件的知识库
    """

    def __init__(self, config: KnowledgeConfig):
        """
        初始化知识库

        Args:
            config: 知识库配置
        """
        # self.config = config
        self.name = config.name
        self.description = config.description
        # 文档分割器
        self.splitter = SplitterFactory.create_splitter(
            splitter_type=config.splitter_type,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        # 嵌入模型
        self.embedding = EmbedderFactory.create_embedder(
            embedder_type=config.embedding_type,
            **config.embedding_config
        )
        # 向量存储
        self.vector_store = VectorStoreFactory.create_store(
            store_type=config.vectorstore_type,
            embeddings=self.embedding,
            persist_dir=config.persist_directory,
            **config.vectorstore_config
        )
        # 知识库状态
        self.persist_directory = config.persist_directory
        self.is_initialized = False
        self.document_count = 0
        self.last_updated = None

    def load_state(self, state: dict):
        self.is_initialized = state["is_initialized"]
        self.document_count = state["document_count"]
        self.last_updated = state["last_updated"]

    def add_documents(
            self,
            file_paths: List[str],
            batch_size: int = 10,
            show_progress: bool = True,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        添加文档到知识库（同步）
        
        Args:
            file_paths: 文件路径列表
            batch_size: 批处理大小
            show_progress: 是否显示进度
            metadata: 额外的元数据
            
        Returns:
            处理统计信息
        """
        all_documents = []
        processed_files = []
        failed_files = []

        total_files = len(file_paths)

        if show_progress:
            print(f"开始处理 {total_files} 个文件...")

        # 加载文档
        for i, file_path in enumerate(file_paths, 1):
            try:
                if show_progress:
                    print(f"[{i}/{total_files}] 加载: {file_path}")

                loader = DocumentLoaderFactory.create_loader(file_path)
                documents = loader.load()
                # 添加文件路径到元数据
                for doc in documents:
                    doc.metadata["source"] = str(file_path)
                    if metadata:
                        doc.metadata.update(metadata)

                # 分割文档
                split_documents = self.splitter.split_documents(documents)
                all_documents.extend(split_documents)

                processed_files.append({
                    "path": file_path,
                    "original_docs": len(documents),
                    "split_docs": len(split_documents)
                })

                logger.info(f"成功处理文件: {file_path}, 生成 {len(split_documents)} 个chunk")

            except Exception as e:
                error_msg = f"处理文件失败 {file_path}: {str(e)}"
                logger.error(error_msg)
                failed_files.append({
                    "path": file_path,
                    "error": str(e)
                })

        # 添加到向量存储
        if all_documents:
            if show_progress:
                print(f"添加 {len(all_documents)} 个文档块到向量存储...")

            try:
                self.vector_store.add_documents(all_documents)
                self.document_count += len(all_documents)
                if show_progress:
                    print(f"成功添加 {len(all_documents)} 个文档块")
            except Exception as e:
                logger.error(f"添加文档到向量存储失败: {str(e)}")

        self.last_updated = datetime.now()
        self.is_initialized = True

        return {
            "total_files": total_files,
            "processed_files": len(processed_files),
            "failed_files": len(failed_files),
            "total_chunks": len(all_documents),
            "document_count": self.document_count,
            "processed_files_detail": processed_files,
            "failed_files_detail": failed_files,
            "is_initialized": self.is_initialized,
            "last_updated": self.last_updated
        }

    def search(
            self,
            query: str,
            k: int = 4,
            filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件
            
        Returns:
            相关文档列表
        """
        try:
            # 使用向量存储的相似度搜索
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            raise e
            logger.error(f"搜索失败: {str(e)}")
            return []

    def as_retriever(
            self,
            search_type: str = "similarity",
            search_kwargs: Optional[Dict[str, Any]] = None
    ) -> BaseRetriever:
        """
        创建Retriever接口
        
        Args:
            search_type: 搜索类型（similarity, mmr等）
            search_kwargs: 搜索参数
            
        Returns:
            LangChain Retriever
        """
        search_kwargs = search_kwargs or {"k": 4}
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            # 尝试获取集合统计信息
            if hasattr(self.vector_store, "_collection"):
                count = self.vector_store._collection.count()
            else:
                count = self.document_count
        except Exception as e:
            logger.error(f"获取向量库中文档数时异常：{e}")
            count = self.document_count

        return {
            "name": self.name,
            "description": self.description,
            "document_count": count,
            "embedding_model": str(self.embedding) if hasattr(self.embedding, "__class__") else "unknown",
            "vector_store_type": type(self.vector_store).__name__,
            "is_initialized": self.is_initialized,
            "last_updated": self.last_updated
        }

    def delete_documents(self, ids: List[str]):
        """删除文档"""
        if hasattr(self.vector_store, "delete"):
            self.vector_store.delete(ids)
            logger.info(f"删除 {len(ids)} 个文档")
        else:
            logger.warning("向量存储不支持删除操作")
