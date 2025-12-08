# -*- coding: utf-8 -*-
"""
@File    : web_loader.py
@Time    : 2025/12/8 15:55
@Desc    : 
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List
from .base_loader import BaseDocumentLoader, Document


class WebLoader(BaseDocumentLoader):
    """网页内容加载器"""

    def __init__(self, url: str):
        self.url = url
        super().__init__(url)  # 将url作为file_path传递

    def load(self) -> List[Document]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            # 获取正文
            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            # 提取标题
            title = soup.title.string if soup.title else ""

            document = Document(
                content=text,
                metadata={
                    "source": self.url,
                    "title": title,
                    "domain": urlparse(self.url).netloc,
                    "file_type": "web"
                }
            )

            return [document]

        except Exception as e:
            raise Exception(f"加载网页内容失败: {str(e)}")


if __name__ == '__main__':
    loader = WebLoader("https://docs.langchain.com/oss/python/langgraph/overview")
    docs = loader.load()
    print(docs)
