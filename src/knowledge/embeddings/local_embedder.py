# -*- coding: utf-8 -*-
"""
@File    : local_embedder.py
@Time    : 2025/12/8 16:57
@Desc    : 
"""
from typing import List
from sentence_transformers import SentenceTransformer
from .base_embedder import BaseEmbedder


class LocalEmbedder(BaseEmbedder):
    """本地嵌入模型（使用Sentence Transformers）"""

    def __init__(self,
                 model_name: str = "BAAI/bge-small-zh-v1.5",
                 device: str = None,
                 normalize_embeddings: bool = True):
        """
        初始化本地嵌入器

        Args:
            model_name: 模型名称或路径
            device: 运行设备（cpu/cuda）
            normalize_embeddings: 是否归一化嵌入向量
        """
        self.model_name = model_name
        self.normalize_embeddings = normalize_embeddings

        # 自动选择设备
        if device is None:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device

        # 加载模型
        self.model = SentenceTransformer(model_name, device=device)

        # 测试嵌入维度
        test_embedding = self.model.encode(["test"])[0]
        self._embedding_dim = len(test_embedding)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        if not texts:
            return []

        # Sentence Transformers自动处理批量
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False
        )

        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        embedding = self.model.encode(
            [text],
            normalize_embeddings=self.normalize_embeddings
        )[0]

        return embedding.tolist()

    def get_embedding_dimension(self) -> int:
        """获取嵌入维度"""
        return self._embedding_dim
