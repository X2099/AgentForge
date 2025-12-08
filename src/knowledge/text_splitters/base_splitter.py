# -*- coding: utf-8 -*-
"""
@File    : base_splitter.py
@Time    : 2025/12/8 16:38
@Desc    : 
"""
from abc import ABC, abstractmethod
from typing import List
from ..document_loaders.base_loader import Document


class BaseTextSplitter(ABC):
    """文本分割器基类"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._validate_params()

    def _validate_params(self):
        if self.chunk_size <= 0:
            raise ValueError("chunk_size 必须大于0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能为负数")

    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """分割单个文本"""
        pass

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """分割文档列表"""
        chunks = []
        for doc in documents:
            text_chunks = self.split_text(doc.content)

            for i, chunk in enumerate(text_chunks):
                metadata = doc.metadata.copy()
                metadata.update({
                    "chunk": i,
                    "total_chunks": len(text_chunks)
                })

                chunk_doc = Document(
                    content=chunk,
                    metadata=metadata,
                    page_content=chunk
                )
                chunks.append(chunk_doc)

        return chunks
