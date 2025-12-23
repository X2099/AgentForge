# -*- coding: utf-8 -*-
"""
@File    : splitters.py
@Time    : 2025/12/22 18:44
@Desc    : 
"""
from langchain_core.documents import BaseDocumentTransformer
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter, TextSplitter
from langchain_experimental.text_splitter import SemanticChunker

from ..knowledge_models import SplitterType

CHINESE_SEPARATORS = [
    "\n\n",  # 双换行
    "\n",  # 单换行
    "。",  # 中文句号
    "！",  # 中文感叹号
    "？",  # 中文问号
    "；",  # 中文分号
    "，",  # 中文逗号
    ". ",  # 英文句号
    "! ",  # 英文感叹号
    "? ",  # 英文问号
    "; ",  # 英文分号
    ", ",  # 英文逗号
    " ",  # 空格
    ""  # 无分隔符（字符级分割）
]


class ChineseTextSplitter(CharacterTextSplitter):
    """
    适合中文文本的 CharacterTextSplitter
    """
    pass


class ChineseRecursiveTextSplitter(RecursiveCharacterTextSplitter):
    """
    适合中文文本的 RecursiveCharacterTextSplitter
    特点：
    - 按中文标点符号（。！？\n）优先断句
    - 保留 chunk_overlap
    - 避免在句子中间切断
    """

    def __init__(self, chunk_size=500, chunk_overlap=50):
        # 中文常用分隔符
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=CHINESE_SEPARATORS
        )


class ChineseSemanticSplitter(SemanticChunker):
    """
    适合中文文本的 SemanticChunker
    """
    pass


class SplitterFactory:

    @staticmethod
    def create_splitter(splitter_type: SplitterType, **kwargs) -> TextSplitter:
        if splitter_type == SplitterType.RECURSIVE:
            return ChineseRecursiveTextSplitter(**kwargs)
        elif splitter_type == SplitterType.FIXED:
            return ChineseTextSplitter(**kwargs)
        elif splitter_type == SplitterType.SEMANTIC:
            return ChineseSemanticSplitter(**kwargs)
        # 如果所有尝试都失败
        raise ValueError(f"不支持的文件分隔类型: {splitter_type}。")
