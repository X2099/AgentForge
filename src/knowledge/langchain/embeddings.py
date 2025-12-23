# -*- coding: utf-8 -*-
"""
@File    : embeddings.py
@Time    : 2025/12/8 16:52
@Desc    : embeddings工厂
"""
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from ..knowledge_models import EmbedderType


class EmbedderFactory:
    """嵌入器工厂"""

    @staticmethod
    def create_embedder(embedder_type: EmbedderType, **kwargs) -> Embeddings:
        """
        创建嵌入器

        Args:
            embedder_type: 嵌入器类型（"openai", "local", "bge"等）
            **kwargs: 嵌入器参数
        """
        if embedder_type == EmbedderType.OPENAI:
            return OpenAIEmbeddings(**kwargs)
        elif embedder_type == EmbedderType.BGE:
            return HuggingFaceEmbeddings(**kwargs)
        else:
            raise ValueError(f"不支持的嵌入器类型: {embedder_type}")
