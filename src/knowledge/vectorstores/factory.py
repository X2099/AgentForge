# -*- coding: utf-8 -*-
"""
@File    : factory.py
@Time    : 2025/12/23 10:28
@Desc    : 
"""
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_core.embeddings import Embeddings

from .base import VectorStoreAdapter
from .faiss_store import FAISSStore
from .chroma_store import ChromaStore
from ..knowledge_models import VectorStoreType


class VectorStoreFactory:
    @staticmethod
    def create_store(
            store_type: VectorStoreType,
            embeddings: Embeddings,
            persist_dir: str,
            **kwargs
    ) -> VectorStoreAdapter:

        if store_type == VectorStoreType.FAISS:
            return FAISSStore(embeddings=embeddings, persist_directory=persist_dir)

        elif store_type == VectorStoreType.CHROMA:
            return ChromaStore(
                embeddings=embeddings,
                persist_directory=persist_dir,
                collection_name=kwargs.get("collection_name")
            )

        raise ValueError(f"Unsupported vectorstore: {store_type}")
