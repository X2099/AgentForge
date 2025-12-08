# -*- coding: utf-8 -*-
"""
@File    : embedder_factory.py
@Time    : 2025/12/8 17:01
@Desc    : 
"""
from .base_embedder import BaseEmbedder
from .openai_embedder import OpenAIEmbedder
from .local_embedder import LocalEmbedder


class EmbedderFactory:
    """嵌入器工厂"""

    @staticmethod
    def create_embedder(embedder_type: str, **kwargs) -> BaseEmbedder:
        """
        创建嵌入器

        Args:
            embedder_type: 嵌入器类型（"openai", "local", "bge"等）
            **kwargs: 嵌入器参数
        """
        embedder_type = embedder_type.lower()

        if embedder_type in ["openai", "openai_embedding"]:
            return OpenAIEmbedder(**kwargs)
        elif embedder_type in ["local", "sentence_transformer"]:
            return LocalEmbedder(**kwargs)
        elif embedder_type in ["bge", "bge_zh"]:
            return LocalEmbedder(
                model_name="BAAI/bge-small-zh-v1.5",
                **kwargs
            )
        else:
            raise ValueError(f"不支持的嵌入器类型: {embedder_type}")
