# -*- coding: utf-8 -*-
"""
@File    : faiss_store.py
@Time    : 2025/12/23 10:25
@Desc    : 
"""
import os
import faiss
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.docstore import InMemoryDocstore
from langchain_community.vectorstores import FAISS

from .base import VectorStoreAdapter


class FAISSStore(VectorStoreAdapter):

    def __init__(
            self,
            embeddings: Embeddings,
            persist_directory: str,
            dim: int = None,
            index: str = None,
            normalize_embeddings: bool = True
    ):
        self.persist_directory = persist_directory
        if os.path.exists(os.path.join(self.persist_directory, "index.faiss")):
            print(f"FAISS 向量库 {self.persist_directory} 已经存在，直接加载...")
            self._vs = FAISS.load_local(
                self.persist_directory,
                embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            print(f"创建 FAISS 向量库 {self.persist_directory} ...")
            dim = dim if dim else len(embeddings.embed_query("dimension_probe"))
            index = faiss.IndexFlatIP(dim)
            self._vs = FAISS(
                embedding_function=embeddings,
                index=index,
                docstore=InMemoryDocstore({}),
                index_to_docstore_id={},
                normalize_L2=normalize_embeddings,
            )
            self.persist()

    # ===== 基本操作 =====
    def add_documents(self, docs: list[Document]):
        self._vs.add_documents(docs)
        self.persist()

    def as_retriever(self, **kwargs):
        return self._vs.as_retriever(**kwargs)

    def similarity_search(self, query, k=4):
        # return self._vs.similarity_search(query, k)
        return self._vs.similarity_search_with_score(query, k)

    def persist(self):
        self._vs.save_local(self.persist_directory)
