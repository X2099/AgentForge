# -*- coding: utf-8 -*-
"""
@File    : pdf_loader.py
@Time    : 2025/12/8 15:36
@Desc    : 
"""
import PyPDF2
from typing import List
from .base_loader import BaseDocumentLoader, Document


class PDFLoader(BaseDocumentLoader):
    """PDF文档加载器"""

    def load(self) -> List[Document]:
        documents = []

        try:
            with open(self.file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()

                    document = Document(
                        content=text,
                        metadata={
                            "source": str(self.file_path),
                            "page": page_num,
                            "total_pages": len(pdf_reader.pages),
                            "file_type": "pdf"
                        }
                    )
                    documents.append(document)

        except Exception as e:
            raise Exception(f"加载PDF文件失败: {str(e)}")

        return documents


if __name__ == '__main__':
    loader = PDFLoader(r"D:\Coding\MyData\大模型技术栈-实战与应用.pdf")
    docs = loader.load()
    print(docs)
