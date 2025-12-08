# -*- coding: utf-8 -*-
"""
@File    : chroma_store.py
@Time    : 2025/12/8 17:09
@Desc    : 
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
from ..document_loaders.base_loader import Document
from .base_store import BaseVectorStore


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB向量存储"""

    def __init__(self,
                 collection_name: str = "default",
                 persist_directory: str = "./data/chroma_db",
                 embedding_function=None):
        """
        初始化Chroma向量存储

        Args:
            collection_name: 集合名称
            persist_directory: 持久化目录
            embedding_function: 嵌入函数（ChromaDB格式）
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function

        # 初始化Chroma客户端
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

    def add_documents(self, documents: List[Document], embeddings: List[List[float]] = None):
        """添加文档到向量存储"""
        if not documents:
            return

        # 准备数据
        ids = []
        texts = []
        metadatas = []
        embeds = []

        for i, doc in enumerate(documents):
            # 生成唯一ID
            doc_id = f"doc_{uuid.uuid4().hex[:8]}_{i}"
            ids.append(doc_id)
            texts.append(doc.content)
            metadatas.append(doc.metadata)

            # 如果有预计算的嵌入
            if embeddings and i < len(embeddings):
                embeds.append(embeddings[i])

        # 添加到集合
        if embeds:
            # 如果有嵌入，直接添加
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeds
            )
        else:
            # 使用嵌入函数
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )

    def search(self,
               query: str,
               k: int = 4,
               filter_dict: Optional[Dict] = None,
               embedding: Optional[List[float]] = None) -> List[Document]:
        """搜索相似文档"""
        try:
            if embedding:
                # 使用提供的嵌入
                results = self.collection.query(
                    query_embeddings=[embedding],
                    n_results=k,
                    where=filter_dict,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                # 使用文本查询
                results = self.collection.query(
                    query_texts=[query],
                    n_results=k,
                    where=filter_dict,
                    include=["documents", "metadatas", "distances"]
                )

            # 转换结果为Document对象
            documents = []
            if results and results['documents']:
                for i in range(len(results['documents'][0])):
                    doc = Document(
                        content=results['documents'][0][i],
                        metadata=results['metadatas'][0][i] if results['metadatas'] else {},
                        page_content=results['documents'][0][i]
                    )
                    # 添加相似度分数
                    if results.get('distances'):
                        doc.metadata['similarity_score'] = 1 - results['distances'][0][i]

                    documents.append(doc)

            return documents

        except Exception as e:
            raise Exception(f"Chroma搜索失败: {str(e)}")

    def delete(self, ids: List[str]):
        """删除文档"""
        self.collection.delete(ids=ids)

    def delete_by_filter(self, filter_dict: Dict):
        """根据过滤器删除文档"""
        self.collection.delete(where=filter_dict)

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            count = self.collection.count()

            # 获取一些样本数据来估计文档长度
            sample_results = self.collection.query(
                query_texts=["test"],
                n_results=min(10, count)
            )

            avg_length = 0
            if sample_results['documents']:
                doc_lengths = [len(doc) for doc in sample_results['documents'][0]]
                avg_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0

            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "average_document_length": avg_length,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            return {
                "error": str(e),
                "collection_name": self.collection_name
            }

    def persist(self):
        """持久化向量存储（ChromaDB自动持久化）"""
        pass  # ChromaDB自动持久化，无需额外操作
