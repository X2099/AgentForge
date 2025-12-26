# -*- coding: utf-8 -*-
"""
@File    : loaders.py
@Time    : 2025/12/8 15:28
@Desc    : 文档加载工厂
"""
from pathlib import Path

from langchain_core.document_loaders import BaseLoader
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
    UnstructuredURLLoader
)


class DocumentLoaderFactory:
    """文档加载器工厂"""

    @staticmethod
    def create_loader(file_path: str, **kwargs) -> BaseLoader:
        """
        根据文件扩展名创建对应的加载器

        Args:
            file_path: 文件路径或URL
            **kwargs: 加载器特定参数

        Returns:
            文档加载器实例

        Raises:
            ValueError: 不支持的文件格式
        """
        # 检查URL
        if file_path.startswith(('http://', 'https://')):
            return UnstructuredURLLoader([file_path])

        # 检查文件是否存在
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检查文件大小
        file_size = path.stat().st_size
        if file_size == 0:
            raise ValueError(f"文件为空: {file_path}")
        if file_size > 100 * 1024 * 1024:  # 100MB限制
            raise ValueError(f"文件太大 ({file_size / 1024 / 1024:.1f}MB)，超过100MB限制")

        # 根据扩展名选择加载器
        ext = path.suffix.lower()

        loader_map = {
            '.pdf': PyPDFLoader,
            '.docx': UnstructuredWordDocumentLoader,
            '.txt': TextLoader,
            '.text': TextLoader,
            '.md': UnstructuredMarkdownLoader,
            '.markdown': UnstructuredMarkdownLoader,
            '.html': UnstructuredURLLoader,  # 本地HTML文件
            '.htm': UnstructuredURLLoader,
        }

        if ext in loader_map:
            loader_class = loader_map[ext]
            print(loader_class)
            # 特殊处理：.doc文件需要提醒用户
            if ext == '.doc':
                print("警告：.doc格式（Word 97-2003）支持有限，建议转换为.docx格式")
            if loader_class == TextLoader:
                kwargs.update(encoding="utf-8")
            return loader_class(file_path, **kwargs)

        # 尝试文本文件（无扩展名或未知扩展名）
        try:
            # 尝试作为文本文件读取
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
                # 简单判断是否为文本文件（大部分字节是可打印ASCII）
                text_ratio = sum(32 <= b < 127 or b in [9, 10, 13] for b in sample) / len(sample)

                if text_ratio > 0.7:  # 70%以上是可打印字符
                    print(f"警告：未知扩展名 {ext}，尝试作为文本文件处理")
                    return TextLoader(file_path, **kwargs)
        except:
            pass

        # 如果所有尝试都失败
        raise ValueError(f"不支持的文件格式: {ext}。支持格式: {', '.join(loader_map.keys())}")

    @staticmethod
    def get_supported_extensions() -> dict:
        """获取支持的文件扩展名"""
        return {
            "PDF文档": [".pdf"],
            "Word文档": [".docx", ".doc"],
            "纯文本": [".txt", ".text"],
            "Markdown": [".md", ".markdown"],
            "网页/HTML": [".html", ".htm"],
            "网页URL": ["http://", "https://"]
        }
