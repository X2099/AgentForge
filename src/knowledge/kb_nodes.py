# -*- coding: utf-8 -*-
"""
@File    : kb_nodes.py
@Time    : 2025/12/9
@Desc    : 基于LangGraph标准的知识库检索节点
"""
from typing import Dict, Any, List, Optional
import logging

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.messages import HumanMessage, BaseMessage

from ..core.state.base_state import AgentState

logger = logging.getLogger(__name__)


def create_knowledge_retrieval_node(
    retriever: BaseRetriever,
    k: int = 4,
    node_name: str = "knowledge_retrieval"
):
    """
    创建知识检索节点（LangGraph标准节点）
    
    使用LangChain的Retriever接口进行检索
    
    Args:
        retriever: LangChain Retriever实例
        k: 检索文档数量
        node_name: 节点名称
        
    Returns:
        节点函数
    """
    async def knowledge_retrieval_node(state: AgentState) -> Dict[str, Any]:
        """
        知识检索节点
        
        从知识库中检索相关文档
        """
        try:
            # 提取查询
            query = _extract_query_from_state(state)
            
            if not query:
                logger.warning("无法提取查询，返回空文档")
                return {
                    "retrieved_documents": [],
                    "retrieved_context": ""
                }
            
            # 使用Retriever检索
            documents = await retriever.aget_relevant_documents(query)
            
            # 限制返回数量
            documents = documents[:k] if len(documents) > k else documents
            
            # 构建上下文
            context = _format_documents_as_context(documents)
            
            # 构建文档列表（用于状态更新）
            doc_list = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "unknown")
                }
                for doc in documents
            ]
            
            logger.debug(f"检索到 {len(documents)} 个相关文档")
            
            return {
                "retrieved_documents": doc_list,
                "retrieved_context": context
            }
            
        except Exception as e:
            logger.error(f"知识检索失败: {str(e)}")
            return {
                "retrieved_documents": [],
                "retrieved_context": f"检索错误: {str(e)}",
                "error": str(e)
            }
    
    knowledge_retrieval_node.__name__ = node_name
    return knowledge_retrieval_node


def create_knowledge_retrieval_node_from_kb(
    knowledge_base: Any,
    k: int = 4,
    search_type: str = "similarity",
    search_kwargs: Optional[Dict[str, Any]] = None
):
    """
    从知识库实例创建检索节点
    
    Args:
        knowledge_base: 知识库实例（LangChainKnowledgeBase或支持as_retriever的知识库）
        k: 检索文档数量
        search_type: 搜索类型
        search_kwargs: 搜索参数
        
    Returns:
        节点函数
    """
    # 获取Retriever
    if hasattr(knowledge_base, "as_retriever"):
        search_kwargs = search_kwargs or {"k": k}
        retriever = knowledge_base.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )
    elif isinstance(knowledge_base, BaseRetriever):
        retriever = knowledge_base
    else:
        raise ValueError("知识库必须支持as_retriever方法或本身就是Retriever")
    
    return create_knowledge_retrieval_node(retriever, k=k)


def _extract_query_from_state(state: AgentState) -> str:
    """
    从状态中提取查询
    
    Args:
        state: Agent状态
        
    Returns:
        查询字符串
    """
    # 优先从query字段获取
    query = state.get("query")
    if query:
        return query
    
    # 从messages中提取最后一条用户消息
    messages = state.get("messages", [])
    if messages:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
            elif isinstance(msg, BaseMessage) and hasattr(msg, "type"):
                if msg.type == "human":
                    return msg.content if hasattr(msg, "content") else str(msg)
            elif isinstance(msg, dict):
                role = msg.get("role", "")
                if role == "user":
                    return msg.get("content", "")
    
    return ""


def _format_documents_as_context(documents: List[Document]) -> str:
    """
    将文档列表格式化为上下文字符串
    
    Args:
        documents: 文档列表
        
    Returns:
        格式化的上下文字符串
    """
    if not documents:
        return "没有找到相关信息。"
    
    context_parts = []
    for i, doc in enumerate(documents, 1):
        content = doc.page_content
        # 截断过长的内容
        if len(content) > 500:
            content = content[:500] + "..."
        
        source = doc.metadata.get("source", "未知来源")
        score = doc.metadata.get("similarity_score", 0.0)
        
        context_parts.append(
            f"[文档{i}] (来源: {source}, 相似度: {score:.3f})\n{content}"
        )
    
    return "\n\n".join(context_parts)




