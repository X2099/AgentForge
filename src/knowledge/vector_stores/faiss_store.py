# -*- coding: utf-8 -*-
"""
@File    : faiss_store.py
@Time    : 2025/12/8 17:11
@Desc    : 
"""
import faiss
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
import os
from ..document_loaders.base_loader import Document
from .base_store import BaseVectorStore


class FAISSVectorStore(BaseVectorStore):
    """FAISS向量存储"""

    def __init__(self,
                 index_path: str = "./data/faiss_index",
                 dimension: int = 384):
        """
        初始化FAISS向量存储

        Args:
            index_path: 索引文件路径
            dimension: 向量维度
        """
        self.index_path = index_path
        self.dimension = dimension
        self.documents = []  # 存储文档内容
        self.metadatas = []  # 存储元数据

        # 加载或创建索引
        self._load_or_create_index()

    def _load_or_create_index(self):
        """加载或创建FAISS索引"""
        index_file = f"{self.index_path}.index"
        meta_file = f"{self.index_path}.pkl"

        if os.path.exists(index_file) and os.path.exists(meta_file):
            # 加载现有索引
            self.index = faiss.read_index(index_file)

            with open(meta_file, 'rb') as f:
                data = pickle.load(f)
                self.documents = data.get('documents', [])
                self.metadatas = data.get('metadatas', [])
        else:
            # 创建新索引（使用内积，后续会归一化）
            self.index = faiss.IndexFlatIP(self.dimension)

            # 确保目录存在
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

    def add_documents(self, documents: List[Document], embeddings: List[List[float]] = None):
        """添加文档到向量存储"""
        if not documents:
            return

        if embeddings is None:
            raise ValueError("FAISS存储需要预计算的嵌入")

        # 转换为numpy数组
        embeds_array = np.array(embeddings).astype('float32')

        # 归一化向量（用于余弦相似度）
        faiss.normalize_L2(embeds_array)

        # 添加到索引
        self.index.add(embeds_array)

        # 存储文档和元数据
        for doc in documents:
            self.documents.append(doc.content)
            self.metadatas.append(doc.metadata)

        # 保存索引和元数据
        self._save()

    def search(self,
               query: str,
               k: int = 4,
               filter_dict: Optional[Dict] = None,
               embedding: Optional[List[float]] = None) -> List[Document]:
        """搜索相似文档"""
        if embedding is None:
            raise ValueError("FAISS搜索需要查询嵌入")

        # 准备查询向量
        query_embedding = np.array([embedding]).astype('float32')
        faiss.normalize_L2(query_embedding)

        # 搜索
        distances, indices = self.index.search(query_embedding, k)

        # 获取结果
        documents = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                # 过滤（简单的元数据过滤）
                metadata = self.metadatas[idx]
                if filter_dict and not self._filter_match(metadata, filter_dict):
                    continue

                doc = Document(
                    content=self.documents[idx],
                    metadata=metadata.copy(),
                    page_content=self.documents[idx]
                )
                doc.metadata['similarity_score'] = float(distances[0][i])
                documents.append(doc)

        return documents

    def _filter_match(self, metadata: Dict, filter_dict: Dict) -> bool:
        """检查元数据是否匹配过滤器"""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True

    def delete(self, ids: List[str]):
        """删除文档（FAISS不支持直接删除，需要重建）"""
        # FAISS不支持直接删除，这里实现标记删除
        for doc_id in ids:
            # 在实际应用中，需要维护一个删除标记
            # 这里简化处理
            pass

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        return {
            "index_type": "FAISS Flat Index",
            "dimension": self.dimension,
            "total_vectors": self.index.ntotal,
            "documents_count": len(self.documents),
            "index_path": self.index_path
        }

    def persist(self):
        """持久化向量存储"""
        self._save()

    def _save(self):
        """保存索引和元数据"""
        # 保存FAISS索引
        faiss.write_index(self.index, f"{self.index_path}.index")

        # 保存元数据
        with open(f"{self.index_path}.pkl", 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'metadatas': self.metadatas
            }, f)
