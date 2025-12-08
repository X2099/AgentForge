# -*- coding: utf-8 -*-
"""
@File    : markdown_loader.py
@Time    : 2025/12/8 15:51
@Desc    : 
"""
import markdown
from bs4 import BeautifulSoup
from typing import List
from .base_loader import BaseDocumentLoader, Document


class MarkdownLoader(BaseDocumentLoader):
    """Markdown文档加载器"""

    def load(self) -> List[Document]:
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as file:
                content = file.read()

            # 将Markdown转换为纯文本
            html = markdown.markdown(content)
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()

            document = Document(
                content=text,
                metadata={
                    "source": str(self.file_path),
                    "file_type": "markdown",
                    "title": self._extract_title(content)
                }
            )

            return [document]

        except Exception as e:
            raise Exception(f"加载Markdown文件失败: {str(e)}")

    def _extract_title(self, content: str) -> str:
        """从Markdown中提取标题"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return self.file_path.stem


if __name__ == '__main__':
    loader = MarkdownLoader(r"D:\Coding\MyData\大模型技术栈-实战与应用.md")
    docs = loader.load()
    print(docs)
