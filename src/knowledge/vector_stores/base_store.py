# -*- coding: utf-8 -*-
"""
@File    : base_store.py
@Time    : 2025/12/8 17:09
@Desc    : 
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
from ..document_loaders.base_loader import Document


class BaseVectorStore(ABC):
    """向量存储基类"""

    @abstractmethod
    def add_documents(self, documents: List[Document], embeddings: List[List[float]] = None):
        """添加文档到向量存储"""
        pass

    @abstractmethod
    def search(self,
               query: str,
               k: int = 4,
               filter_dict: Optional[Dict] = None) -> List[Document]:
        """搜索相似文档"""
        pass

    @abstractmethod
    def delete(self, ids: List[str]):
        """删除文档"""
        pass

    @abstractmethod
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        pass

    @abstractmethod
    def persist(self):
        """持久化向量存储"""
        pass
