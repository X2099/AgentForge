# -*- coding: utf-8 -*-
"""
@File    : knowledge_base.py
@Time    : 2025/12/8 15:25
@Desc    : 
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .document_loaders import DocumentLoaderFactory
from .text_splitters import RecursiveTextSplitter, SemanticTextSplitter
from .embeddings import EmbedderFactory
from .vector_stores import VectorStoreFactory
from .document_loaders.base_loader import Document

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """知识库主类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化知识库

        Args:
            config: 知识库配置字典
        """
        self.config = config
        self.name = config.get("name", "default_kb")
        self.description = config.get("description", "")

        # 初始化组件
        self._init_splitter()
        self._init_embedder()
        self._init_vector_store()

        # 知识库状态
        self.is_initialized = False
        self.document_count = 0
        self.last_updated = None

    def _init_splitter(self):
        """初始化文本分割器"""
        splitter_type = self.config.get("splitter_type", "recursive")
        chunk_size = self.config.get("chunk_size", 500)
        chunk_overlap = self.config.get("chunk_overlap", 50)

        if splitter_type == "semantic":
            model_name = self.config.get("semantic_model", "paraphrase-multilingual-MiniLM-L12-v2")
            threshold = self.config.get("semantic_threshold", 0.5)
            self.splitter = SemanticTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                model_name=model_name,
                threshold=threshold
            )
        else:
            self.splitter = RecursiveTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

    def _init_embedder(self):
        """初始化嵌入器"""
        embedder_config = self.config.get("embedder", {})
        if not embedder_config:
            # 默认配置
            embedder_config = {
                "embedder_type": "openai",
                "model": "text-embedding-3-small"
            }

        self.embedder = EmbedderFactory.create_embedder(**embedder_config)

    def _init_vector_store(self):
        """初始化向量存储"""
        store_config = self.config.get("vector_store", {})
        if not store_config:
            # 默认配置
            store_config = {
                "store_type": "chroma",
                "collection_name": self.name,
                "persist_directory": f"./data/vector_stores/{self.name}"
            }

        # 添加嵌入器配置
        embedder_config = self.config.get("embedder", {})

        self.vector_store = VectorStoreFactory.create_store(
            embedder_config=embedder_config,
            **store_config
        )

    def add_documents(self,
                      file_paths: List[str],
                      batch_size: int = 10,
                      show_progress: bool = True) -> Dict[str, Any]:
        """
        添加文档到知识库

        Args:
            file_paths: 文件路径列表
            batch_size: 批处理大小
            show_progress: 是否显示进度

        Returns:
            处理统计信息
        """
        all_documents = []
        processed_files = []
        failed_files = []

        total_files = len(file_paths)

        if show_progress:
            print(f"开始处理 {total_files} 个文件...")

        for i, file_path in enumerate(file_paths, 1):
            try:
                if show_progress:
                    print(f"[{i}/{total_files}] 处理: {file_path}")

                # 加载文档
                loader = DocumentLoaderFactory.create_loader(file_path)
                documents = loader.load()

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

        # 批量处理文档
        if all_documents:
            total_chunks = len(all_documents)

            if show_progress:
                print(f"开始嵌入 {total_chunks} 个chunk...")

            # 批量嵌入
            embeddings = []
            for i in range(0, total_chunks, batch_size):
                batch_docs = all_documents[i:i + batch_size]
                batch_texts = [doc.content for doc in batch_docs]

                if show_progress:
                    progress = min(i + batch_size, total_chunks)
                    print(f"嵌入进度: {progress}/{total_chunks}")

                try:
                    batch_embeddings = self.embedder.embed_documents(batch_texts)
                    embeddings.extend(batch_embeddings)
                except Exception as e:
                    logger.error(f"嵌入失败: {str(e)}")
                    # 为失败的批次填充None
                    embeddings.extend([None] * len(batch_docs))

            # 过滤掉嵌入失败的文档
            valid_documents = []
            valid_embeddings = []

            for doc, emb in zip(all_documents, embeddings):
                if emb is not None:
                    valid_documents.append(doc)
                    valid_embeddings.append(emb)

            # 添加到向量存储
            if valid_documents:
                self.vector_store.add_documents(valid_documents, valid_embeddings)
                self.document_count += len(valid_documents)

                if show_progress:
                    print(f"成功添加 {len(valid_documents)} 个chunk到知识库")
            else:
                logger.warning("没有有效的文档可以添加到知识库")

        # 更新状态
        self.last_updated = datetime.now()
        self.is_initialized = True

        # 持久化
        self.vector_store.persist()

        # 返回统计信息
        stats = {
            "total_files": total_files,
            "processed_files": len(processed_files),
            "failed_files": len(failed_files),
            "total_chunks": len(all_documents),
            "valid_chunks": len(valid_documents) if 'valid_documents' in locals() else 0,
            "document_count": self.document_count,
            "processed_files_detail": processed_files,
            "failed_files_detail": failed_files
        }

        return stats

    def search(self,
               query: str,
               k: int = 4,
               filter_dict: Optional[Dict] = None) -> List[Document]:
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
            # 生成查询嵌入
            query_embedding = self.embedder.embed_query(query)

            # 搜索向量存储
            results = self.vector_store.search(
                query=query,
                k=k,
                filter_dict=filter_dict,
                embedding=query_embedding
            )

            return results

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        vector_store_stats = self.vector_store.get_collection_stats()

        stats = {
            "name": self.name,
            "description": self.description,
            "is_initialized": self.is_initialized,
            "document_count": self.document_count,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "splitter_type": self.config.get("splitter_type", "recursive"),
            "chunk_size": self.config.get("chunk_size", 500),
            "chunk_overlap": self.config.get("chunk_overlap", 50),
            "vector_store": vector_store_stats
        }

        return stats

    def clear(self):
        """清空知识库"""
        # 注意：具体实现取决于向量存储
        self.document_count = 0
        self.last_updated = None
        self.is_initialized = False

        # TODO: 实现向量存储的清空方法
        logger.warning("清空知识库功能尚未完全实现")

    def delete_documents(self, filter_dict: Dict):
        """
        删除文档

        Args:
            filter_dict: 过滤条件
        """
        # TODO: 根据过滤条件删除文档
        pass
