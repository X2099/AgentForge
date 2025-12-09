# -*- coding: utf-8 -*-
"""
@File    : kb_usage.py
@Time    : 2025/12/8 17:33
@Desc    : 
"""
import json
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

sys.path.append(BASE_DIR)

from src.knowledge.kb_manager import KnowledgeBaseManager


def main():
    # 创建知识库管理器
    manager = KnowledgeBaseManager("./configs/knowledge_bases")

    # 创建知识库配置
    kb_config = {
        "name": "my_knowledge_base",
        "description": "我的第一个知识库",
        "splitter_type": "recursive",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "embedder": {
            "embedder_type": "bge",
            "model_name": "BAAI/bge-base-zh-v1.5"
        },
        # "vector_store": {
        #     "store_type": "chroma",
        #     "collection_name": "my_kb",
        #     "persist_directory": "./data/vector_stores/my_kb"
        # },
        "vector_store": {
            "store_type": "faiss",
            "index_path": "./data/faiss_index",
            "dimension": 768
        }
    }

    # 创建知识库
    kb = manager.create_knowledge_base(kb_config)

    # 添加文档
    file_paths = [
        "./data/documents/大模型技术栈-实战与应用.pdf",
        "./data/documents/大模型技术栈-实战与应用.md",
        "https://docs.langchain.com/oss/python/langgraph/overview"
    ]

    stats = manager.bulk_add_documents("my_knowledge_base", file_paths)
    print(f"处理统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    # 搜索
    query = "机器学习的基本概念"
    results = manager.search("my_knowledge_base", query, k=3)

    print(f"\n搜索查询: {query}")
    print(f"找到 {len(results)} 个相关文档:\n")

    for i, doc in enumerate(results, 1):
        print(f"文档 {i}:")
        print(f"  内容: {doc.content[:200]}...")
        print(f"  来源: {doc.metadata.get('source', 'Unknown')}")
        print(f"  相似度: {doc.metadata.get('similarity_score', 0):.4f}")
        print("-" * 50)

    # 列出所有知识库
    print("\n所有知识库:")
    for kb_info in manager.list_knowledge_bases():
        print(f"  - {kb_info['name']}: {kb_info['document_count']} 个文档")


if __name__ == "__main__":
    main()
