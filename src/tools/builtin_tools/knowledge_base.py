# -*- coding: utf-8 -*-
"""
@Desc    : LangChain 原生格式的知识库检索工具
"""
import logging
from typing import Optional, List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ...knowledge.knowledge_manager import KnowledgeBaseManager

logger = logging.getLogger(__name__)


class KnowledgeBaseArgs(BaseModel):
    query: str = Field(..., description="搜索查询")
    kb_name: str = Field("default", description="知识库名称")
    max_results: int = Field(5, ge=1, le=10, description="最大返回结果数")


def _format_results(results: List[any], query: str, kb_name: str) -> str:
    lines = [f"在知识库 '{kb_name}' 中搜索 '{query}' 的结果:"]
    lines.append("=" * 50)
    for i, doc in enumerate(results, 1):
        content = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
        lines.append(f"\n结果 {i}:")
        lines.append(f"相似度: {doc.metadata.get('similarity_score', 0):.4f}")
        lines.append(f"来源: {doc.metadata.get('source', '未知')}")
        lines.append(f"内容: {content}")
    lines.append(f"\n共找到 {len(results)} 个相关文档。")
    return "\n".join(lines)


def create_knowledge_base_tool(kb_manager: Optional[KnowledgeBaseManager] = None) -> StructuredTool:
    kb_mgr = kb_manager or KnowledgeBaseManager()

    async def _search(query: str, kb_name: str = "default", max_results: int = 5) -> str:
        if not query:
            return "错误：搜索查询不能为空"
        logger.info(f"知识库搜索: {query}, 知识库: {kb_name}")
        try:
            kb = kb_mgr.get_knowledge_base(kb_name)
            if not kb:
                available_kbs = kb_mgr.list_knowledge_bases()
                kb_list = ", ".join([kb['name'] for kb in available_kbs])
                return f"错误：知识库 '{kb_name}' 不存在。可用知识库: {kb_list}"
            results = kb.search(query, k=max_results)
            if not results:
                return f"在知识库 '{kb_name}' 中未找到相关信息。"
            return _format_results(results, query, kb_name)
        except Exception as e:
            logger.error(f"知识库搜索失败: {str(e)}")
            return f"搜索失败: {str(e)}"

    return StructuredTool.from_function(
        func=_search,
        name="knowledge_base_search",
        description="在知识库中搜索相关信息",
        args_schema=KnowledgeBaseArgs,
        coroutine=_search,
    )


# 默认实例，使用默认 KnowledgeBaseManager
knowledge_base_tool = create_knowledge_base_tool()

__all__ = ["knowledge_base_tool", "create_knowledge_base_tool", "KnowledgeBaseArgs"]
