# -*- coding: utf-8 -*-
"""
@File    : store_factory.py
@Time    : 2025/12/8 17:16
@Desc    : 
"""
from typing import Optional, Dict

from chromadb import EmbeddingFunction
from .base_store import BaseVectorStore
from .chroma_store import ChromaVectorStore
from .faiss_store import FAISSVectorStore
from ..embeddings import EmbedderFactory


class VectorStoreFactory:
    """向量存储工厂"""

    @staticmethod
    def create_store(store_type: str,
                     embedder_config: Optional[Dict] = None,
                     **kwargs) -> BaseVectorStore:
        """
        创建向量存储

        Args:
            store_type: 存储类型（"chroma", "faiss", "milvus"）
            embedder_config: 嵌入器配置
            **kwargs: 向量存储参数
        """
        store_type = store_type.lower()

        # 处理嵌入函数
        embedding_function = None
        if embedder_config and store_type == "chroma":
            # 为Chroma创建嵌入函数
            embedder = EmbedderFactory.create_embedder(**embedder_config)

            class MyEmbeddingFunction(EmbeddingFunction):
                def __call__(self, texts):
                    return embedder.embed_documents(texts)

                def name(self):
                    return embedder_config["model_name"]

            embedding_function = MyEmbeddingFunction()

        if store_type == "chroma":
            if embedding_function:
                kwargs['embedding_function'] = embedding_function
            return ChromaVectorStore(**kwargs)
        elif store_type == "faiss":
            return FAISSVectorStore(**kwargs)
        elif store_type == "milvus":
            # TODO: 实现Milvus存储
            raise NotImplementedError("Milvus存储尚未实现")
        else:
            raise ValueError(f"不支持的向量存储类型: {store_type}")
