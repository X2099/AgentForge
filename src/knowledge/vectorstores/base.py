# -*- coding: utf-8 -*-
"""
@File    : base.py
@Time    : 2025/12/23 10:24
@Desc    : 
"""
from abc import ABC, abstractmethod
from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


class VectorStoreAdapter(ABC):

    @abstractmethod
    def add_documents(self, docs: List[Document]) -> None:
        ...

    @abstractmethod
    def as_retriever(self, **kwargs) -> BaseRetriever:
        ...

    @abstractmethod
    def similarity_search(self, query: str, k: int = 4):
        ...
