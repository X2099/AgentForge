# -*- coding: utf-8 -*-
"""
@File    : __init__.py.py
@Time    : 2025/12/8 15:10
@Desc    : 
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class SplitterType(Enum):
    """文本分割器类型"""
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    FIXED = "fixed"


class EmbedderType(Enum):
    """嵌入模型类型"""
    OPENAI = "openai"
    LOCAL = "local"
    BGE = "bge"


class VectorStoreType(Enum):
    """向量存储类型"""
    CHROMA = "chroma"
    FAISS = "faiss"
    MILVUS = "milvus"
    WEAVIATE = "weaviate"


@dataclass
class KnowledgeBaseConfig:
    """知识库配置"""
    name: str
    description: str = ""
    splitter_type: SplitterType = SplitterType.RECURSIVE
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedder_type: EmbedderType = EmbedderType.OPENAI
    vector_store_type: VectorStoreType = VectorStoreType.CHROMA
    persist_directory: str = "./data/knowledge_bases"
    collection_name: Optional[str] = None

    def __post_init__(self):
        if not self.collection_name:
            self.collection_name = f"kb_{self.name.lower().replace(' ', '_')}"
