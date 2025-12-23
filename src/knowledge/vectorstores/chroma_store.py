# -*- coding: utf-8 -*-
"""
@File    : chroma_store.py
@Time    : 2025/12/23 10:27
@Desc    : 
"""
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from .base import VectorStoreAdapter


class ChromaStore(VectorStoreAdapter):

    def __init__(self, embeddings: Embeddings, persist_directory: str, collection_name: str):
        self._vs = Chroma(
            embedding_function=embeddings,
            persist_directory=persist_directory,
            collection_name=collection_name,
        )

    # ===== 基本操作 =====
    def add_documents(self, docs: list[Document]):
        self._vs.add_documents(docs)

    def as_retriever(self, **kwargs):
        return self._vs.as_retriever(**kwargs)

    def similarity_search(self, query, k=4):
        # return self._vs.similarity_search(query, k)
        return self._vs.similarity_search_with_score(query, k)
