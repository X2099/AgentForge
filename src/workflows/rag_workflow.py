# -*- coding: utf-8 -*-
"""
@File    : rag_workflow.py
@Time    : 2025/12/9 14:38
@Desc    : 基于LangGraph标准的RAG工作流
"""
from typing import TypedDict, Dict, Any, List, Optional, Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..core.graphs.base_graph import BaseGraph
from ..core.state.base_state import GraphState
from ..llm.llm_client import LLMClient


class RAGState(GraphState):
    """RAG工作流状态"""
    query: str
    documents: Annotated[List[Dict[str, Any]], lambda x, y: y or x]
    context: Optional[str] = None
    answer: Optional[str] = None
    sources: Annotated[List[Dict[str, Any]], lambda x, y: y or x]


class RAGWorkflow(BaseGraph):
    """
    RAG（检索增强生成）工作流
    
    流程：查询分析 -> 检索 -> 重排序 -> 上下文构建 -> 生成
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        knowledge_base: Any,
        system_prompt: Optional[str] = None
    ):
        """
        初始化RAG工作流
        
        Args:
            llm_client: LLM客户端
            knowledge_base: 知识库
            system_prompt: 系统提示词
        """
        super().__init__(
            name="rag_workflow",
            description="RAG检索增强生成工作流",
            state_type=RAGState
        )
        
        self.llm_client = llm_client
        self.knowledge_base = knowledge_base
        self.system_prompt = system_prompt or "你是一个基于知识库回答问题的AI助手。"
    
    def build(self):
        """构建RAG工作流"""
        # 添加节点
        self.add_node("query_analyzer", self._query_analyzer_node)
        self.add_node("retriever", self._retriever_node)
        self.add_node("reranker", self._reranker_node)
        self.add_node("context_builder", self._context_builder_node)
        self.add_node("generator", self._generator_node)
        
        # 构建流程（线性流程）
        self.set_entry_point(START)
        self.add_edge(START, "query_analyzer")
        self.add_edge("query_analyzer", "retriever")
        self.add_edge("retriever", "reranker")
        self.add_edge("reranker", "context_builder")
        self.add_edge("context_builder", "generator")
        self.add_edge("generator", END)
    
    def _query_analyzer_node(self, state: RAGState) -> Dict[str, Any]:
        """查询分析节点"""
        # 提取查询（可以从messages或query字段）
        query = state.get("query")
        if not query:
            messages = state.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, dict):
                    query = last_msg.get("content", "")
                elif isinstance(last_msg, BaseMessage):
                    query = last_msg.content
                elif isinstance(last_msg, HumanMessage):
                    query = last_msg.content
        
        if not query:
            query = ""
        
        # 简单的查询分析（可以扩展为使用LLM分析）
        return {
            "query": query
        }
    
    def _retriever_node(self, state: RAGState) -> Dict[str, Any]:
        """检索节点"""
        query = state.get("query", "")
        
        if not query:
            return {"documents": []}
        
        try:
            # 从知识库检索
            documents = self.knowledge_base.search(query, k=5)
            
            # 转换为字典格式
            doc_dicts = []
            for doc in documents:
                doc_dict = {
                    "content": doc.content if hasattr(doc, "content") else str(doc),
                    "metadata": doc.metadata if hasattr(doc, "metadata") else {},
                    "score": doc.metadata.get("similarity_score", 0.0) if hasattr(doc, "metadata") else 0.0
                }
                doc_dicts.append(doc_dict)
            
            return {"documents": doc_dicts}
            
        except Exception as e:
            return {
                "documents": [],
                "error": f"检索错误: {str(e)}"
            }
    
    def _reranker_node(self, state: RAGState) -> Dict[str, Any]:
        """重排序节点"""
        documents = state.get("documents", [])
        
        if not documents:
            return {"documents": []}
        
        # 按相似度分数排序
        sorted_docs = sorted(
            documents,
            key=lambda x: x.get("score", 0.0),
            reverse=True
        )
        
        # 取前3个
        return {"documents": sorted_docs[:3]}
    
    def _context_builder_node(self, state: RAGState) -> Dict[str, Any]:
        """上下文构建节点"""
        documents = state.get("documents", [])
        
        if not documents:
            return {"context": "没有找到相关信息。"}
        
        # 构建上下文
        context_parts = []
        sources = []
        
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")
            # 截断内容
            content_truncated = content[:300] + "..." if len(content) > 300 else content
            context_parts.append(f"[文档{i}] {content_truncated}")
            
            sources.append({
                "index": i,
                "content": content[:100] + "..." if len(content) > 100 else content,
                "source": doc.get("metadata", {}).get("source", "未知"),
                "score": doc.get("score", 0.0)
            })
        
        context = "\n\n".join(context_parts)
        
        return {
            "context": context,
            "sources": sources
        }
    
    async def _generator_node(self, state: RAGState) -> Dict[str, Any]:
        """生成节点"""
        query = state.get("query", "")
        context = state.get("context", "")
        
        # 构建提示词
        prompt = f"""基于以下上下文回答问题：

上下文：
{context}

问题：{query}

要求：
1. 基于上下文回答，不要编造信息
2. 如果上下文没有相关信息，请如实说明
3. 引用相关文档来源
"""
        
        # 准备消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # 调用LLM（异步）
            response = await self.llm_client.achat(messages)
            
            # response是AIMessage类型
            answer = response.content if hasattr(response, "content") else str(response)
            
            # 创建消息
            ai_message = AIMessage(content=answer)
            
            return {
                "messages": [ai_message],
                "answer": answer
            }
            
        except Exception as e:
            error_answer = f"生成答案时出错：{str(e)}"
            return {
                "messages": [AIMessage(content=error_answer)],
                "answer": error_answer,
                "error": str(e)
            }


def create_rag_workflow(
    llm_client: LLMClient,
    knowledge_base: Any,
    system_prompt: Optional[str] = None
) -> StateGraph:
    """
    创建RAG工作流（便捷函数）
    
    Args:
        llm_client: LLM客户端
        knowledge_base: 知识库
        system_prompt: 系统提示词
        
    Returns:
        编译后的工作流图
    """
    workflow = RAGWorkflow(
        llm_client=llm_client,
        knowledge_base=knowledge_base,
        system_prompt=system_prompt
    )
    
    return workflow.compile()
