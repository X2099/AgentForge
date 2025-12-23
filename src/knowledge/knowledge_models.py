# -*- coding: utf-8 -*-
"""
@File    : knowledge_models.py
@Time    : 2025/12/22 18:25
@Desc    : 知识库数据模型定义
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
class KnowledgeConfig:
    """知识库配置"""
    name: str
    description: str
    splitter_type: SplitterType
    chunk_size: int
    chunk_overlap: int
    embedding_type: EmbedderType
    embedding_model: str
    vectorstore_type: VectorStoreType
    persist_directory: str
    semantic_config: dict
    embedding_config: dict
    vectorstore_config: dict


@dataclass
class KnowledgeState:
    initialized: bool = False
    index_path: Optional[str] = None
    doc_count: int = 0
    last_updated_at: Optional[str] = None
