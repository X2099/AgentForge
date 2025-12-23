# -*- coding: utf-8 -*-
"""
@File    : knowledge_demo.py
@Time    : 2025/12/23 8:22
@Desc    : 
"""
import sys
from pathlib import Path
from pprint import pprint

import faiss
from langchain_community.docstore import InMemoryDocstore

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.knowledge.langchain.loaders import DocumentLoaderFactory
from src.knowledge.langchain.embeddings import EmbedderFactory
from src.knowledge.vectorstores import VectorStoreFactory
# from src.knowledge.knowledge_base import KnowledgeBase

from src.knowledge.knowledge_manager import KnowledgeBaseManager
from src.knowledge.knowledge_models import (
    SplitterType,
    EmbedderType,
    VectorStoreType,
    KnowledgeConfig
)


def get_documents():
    loader = DocumentLoaderFactory.create_loader(r"D:\Coding\MyData\大模型技术栈-实战与应用.pdf")
    docs = loader.load()
    # print(docs)
    return docs


def get_embedder():
    # embedder_config = {"model_name": "BAAI/bge-small-zh-v1.5"}
    embedder_config = {"model_name": "BAAI/bge-base-zh-v1.5"}
    embedding = EmbedderFactory.create_embedder(embedder_type=EmbedderType.BGE, **embedder_config)
    print(embedding)
    return embedding


def get_vector_store():
    docs = get_documents()
    embeddings = get_embedder()

    store_type = VectorStoreType.FAISS
    vectorstore_config = {}

    # store_type = VectorStoreType.CHROMA
    # vectorstore_config = {
    #     "collection_name": "collection_name_test"
    # }

    vector_store = VectorStoreFactory.create_store(
        store_type=store_type,
        embeddings=embeddings,
        persist_dir=f"./data/knowledge_bases/{store_type.value}/knowledge_test",
        **vectorstore_config
    )
    vector_store.add_documents(docs)
    # print(vector_store)
    search_result = vector_store.similarity_search("大模型")
    print(len(search_result))


def get_kb_manager():
    # config = KnowledgeConfig(
    #     name="knowledge_demo",
    #     description="知识库demo",
    #     splitter_type=SplitterType.RECURSIVE,
    #     chunk_size=500,
    #     chunk_overlap=50,
    #     embedding_type=EmbedderType.BGE,
    #     embedding_model="BAAI/bge-small-zh-v1.5",
    #     vectorstore_type=VectorStoreType.FAISS,
    #     persist_directory="./data/knowledge_bases",
    #     semantic_config={},
    #     embedding_config={"model_name": "BAAI/bge-small-zh-v1.5"},
    #     vectorstore_config={}
    # )

    # config = KnowledgeConfig(
    #     name="knowledge_demo_chroma",
    #     description="知识库demo_chroma",
    #     splitter_type=SplitterType.RECURSIVE,
    #     chunk_size=500,
    #     chunk_overlap=50,
    #     embedding_type=EmbedderType.BGE,
    #     embedding_model="BAAI/bge-small-zh-v1.5",
    #     vectorstore_type=VectorStoreType.CHROMA,
    #     persist_directory="./data/knowledge_bases",
    #     semantic_config={},
    #     embedding_config={"model_name": "BAAI/bge-small-zh-v1.5"},
    #     vectorstore_config={"collection_name": "chroma_collection_name"}
    # )

    kb_manager = KnowledgeBaseManager()

    # kb = kb_manager.create_knowledge_base(config)

    # kbs = kb_manager.list_knowledge_bases()

    kb = kb_manager.get_knowledge_base("ai_kownledge")
    result = kb.search("AI")
    # print(result)
    formatted_results = []
    for doc, score in result:
        # print(doc)
        formatted_results.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", ""),
            "score": score
        })
        # print(doc.metadata)
    pprint(formatted_results)

    # print("kbs ==> ")
    # pprint(kbs)
    # docs = get_documents()
    # stats = kb_manager.bulk_add_documents(kb_name="knowledge_demo",
    #                                       file_paths=[r"D:\Coding\MyData\大模型技术栈-实战与应用.pdf"])
    # print(stats)
    # kb_manager.delete_knowledge_base("knowledge_demo_chroma", delete_data=True)


if __name__ == '__main__':
    # get_documents()
    # get_embedder()
    # get_vector_store()
    get_kb_manager()
    # print(SplitterType.RECURSIVE.value)
