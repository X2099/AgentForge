# -*- coding: utf-8 -*-
"""
@File    : rag_workflow.py
@Time    : 2025/12/9 14:38
@Desc    : 知识库问答工作流
"""
from langgraph.graph import StateGraph, END
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class RAGState:
    """RAG工作流状态"""
    query: str
    documents: List[Dict[str, Any]] = None
    context: str = ""
    answer: str = ""
    sources: List[Dict[str, Any]] = None


def create_rag_workflow(knowledge_base):
    """创建RAG工作流（对标Langchain-Chatchat的KB Service）"""

    workflow = StateGraph(RAGState)

    # 1. 查询解析节点
    def query_analyzer(state: RAGState):
        """分析查询意图"""
        # 提取关键词、判断查询类型等
        return {"analyzed_query": state.query}

    # 2. 检索节点（使用知识库）
    def retriever(state: RAGState):
        """检索相关文档"""
        documents = knowledge_base.search(state.query, k=5)
        return {"documents": documents}

    # 3. 重排序节点
    def reranker(state: RAGState):
        """重排序检索结果"""
        if not state.documents:
            return {"documents": []}

        # 简单按相似度排序
        sorted_docs = sorted(
            state.documents,
            key=lambda x: x.metadata.get('similarity_score', 0),
            reverse=True
        )
        return {"documents": sorted_docs[:3]}

    # 4. 上下文构建节点
    def context_builder(state: RAGState):
        """构建LLM上下文"""
        if not state.documents:
            return {"context": "没有找到相关信息。"}

        context_parts = []
        for i, doc in enumerate(state.documents, 1):
            content = doc.content[:300] + "..." if len(doc.content) > 300 else doc.content
            context_parts.append(f"[文档{i}] {content}")
            context_parts.append(f"来源: {doc.metadata.get('source', '未知')}")

        return {"context": "\n\n".join(context_parts)}

    # 5. LLM生成节点
    def llm_generator(state: RAGState):
        """生成答案"""
        prompt = f"""
        基于以下上下文回答问题：

        上下文：
        {state.context}

        问题：{state.query}

        要求：
        1. 基于上下文回答，不要编造信息
        2. 如果上下文没有相关信息，请如实说明
        3. 引用相关文档来源
        """

        # 调用LLM（这里简化为模拟）
        answer = f"基于检索到的信息回答：{state.query}"
        sources = [
            {"source": doc.metadata.get('source'), "content": doc.content[:100]}
            for doc in (state.documents or [])
        ]

        return {"answer": answer, "sources": sources}

    # 添加节点
    workflow.add_node("query_analyzer", query_analyzer)
    workflow.add_node("retriever", retriever)
    workflow.add_node("reranker", reranker)
    workflow.add_node("context_builder", context_builder)
    workflow.add_node("llm_generator", llm_generator)

    # 构建流程
    workflow.set_entry_point("query_analyzer")
    workflow.add_edge("query_analyzer", "retriever")
    workflow.add_edge("retriever", "reranker")
    workflow.add_edge("reranker", "context_builder")
    workflow.add_edge("context_builder", "llm_generator")
    workflow.add_edge("llm_generator", END)

    return workflow.compile()
