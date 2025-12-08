# -*- coding: utf-8 -*-
"""
@File    : base_embedder.py
@Time    : 2025/12/8 16:53
@Desc    : 
"""
from abc import ABC, abstractmethod
from typing import List


class BaseEmbedder(ABC):
    """嵌入模型基类"""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        pass

    def get_embedding_dimension(self) -> int:
        """获取嵌入维度"""
        # 测试一个样本来获取维度
        test_text = "test"
        embedding = self.embed_query(test_text)
        return len(embedding)
