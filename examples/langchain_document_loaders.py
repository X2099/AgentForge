# -*- coding: utf-8 -*-
"""
@File    : langchain_document_loaders.py
@Time    : 2025/12/22 16:34
@Desc    : 
"""
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
    UnstructuredURLLoader
)

# loader = PyPDFLoader(r"D:\Coding\MyData\大模型技术栈-实战与应用.pdf")
# docs = loader.load()
# print(docs)

# loader = UnstructuredWordDocumentLoader(r"D:\Coding\MyData\大模型技术栈-实战与应用.docx")
# docs = loader.load()
# print(docs)

# loader = TextLoader(r"D:\Coding\MyData\大模型技术栈-实战与应用.txt", encoding="utf-8")
# docs = loader.load()
# print(docs)

# loader = UnstructuredMarkdownLoader(r"D:\Coding\MyData\大模型技术栈-实战与应用.md")
# docs = loader.load()
# print(docs)

loader = UnstructuredURLLoader(["https://docs.langchain.com/oss/python/langgraph/overview"])
docs = loader.load()
print(docs)
