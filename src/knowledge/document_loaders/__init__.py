# -*- coding: utf-8 -*-
"""
@File    : __init__.py.py
@Time    : 2025/12/8 15:28
@Desc    : 
"""
from .base_loader import BaseDocumentLoader, Document
from .pdf_loader import PDFLoader
from .docx_loader import DocxLoader
from .txt_loader import TxtLoader
from .markdown_loader import MarkdownLoader
from .web_loader import WebLoader


class DocumentLoaderFactory:
    """文档加载器工厂"""

    @staticmethod
    def create_loader(file_path: str, **kwargs) -> BaseDocumentLoader:
        """根据文件扩展名创建对应的加载器"""
        from pathlib import Path

        path = Path(file_path)
        ext = path.suffix.lower()

        if file_path.startswith(('http://', 'https://')):
            return WebLoader(file_path, **kwargs)
        elif ext == '.pdf':
            return PDFLoader(file_path, **kwargs)
        elif ext in ['.docx', '.doc']:
            return DocxLoader(file_path, **kwargs)
        elif ext == '.txt':
            return TxtLoader(file_path, **kwargs)
        elif ext in ['.md', '.markdown']:
            return MarkdownLoader(file_path, **kwargs)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
