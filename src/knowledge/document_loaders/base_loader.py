# -*- coding: utf-8 -*-
"""
@File    : base_loader.py
@Time    : 2025/12/8 15:29
@Desc    : 
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Document:
    """文档数据类"""
    content: str
    metadata: Dict[str, Any]
    page_content: str = None

    def __post_init__(self):
        if self.page_content is None:
            self.page_content = self.content


class BaseDocumentLoader(ABC):
    """文档加载器基类"""

    def __init__(self, file_path: str, encoding: str = "utf-8"):
        self.file_path = Path(file_path)
        self.encoding = encoding

    @abstractmethod
    def load(self) -> List[Document]:
        """加载文档"""
        pass

    def load_and_split(self, splitter=None) -> List[Document]:
        """加载并分割文档"""
        documents = self.load()
        if splitter:
            return splitter.split_documents(documents)
        return documents
