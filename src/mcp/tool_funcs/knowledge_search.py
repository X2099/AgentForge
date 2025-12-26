import logging

from langchain_core.documents import Document
from pydantic import BaseModel, Field

from src.knowledge.knowledge_manager import KnowledgeBaseManager

logger = logging.getLogger(__name__)

kb_mgr = KnowledgeBaseManager()


class KnowledgeSearchArgs(BaseModel):
    query: str = Field(..., description="搜索关键字")
    kb_name: str = Field(..., description="知识库名称，可选范围：ai_knowledge，AncientChineseLiterature")


def _format_results(results: list[tuple[Document, float]], query: str, kb_name: str) -> str:
    lines = [f"在知识库 '{kb_name}' 中搜索 '{query}' 的结果:", "=" * 50]
    for i, (doc, score) in enumerate(results, 1):
        content = doc.page_content,
        lines.append(f"\n结果 {i}:")
        lines.append(f"相似度: {float(score)}")
        lines.append(f"来源: {doc.metadata.get('source', '未知')}")
        lines.append(f"内容: {content}")
    lines.append(f"\n共找到 {len(results)} 个相关文档。")
    return "\n".join(lines)


def search(query: str, kb_name: str) -> str:
    if not query:
        return "错误：搜索查询不能为空"
    logger.info(f"知识库搜索: {query}, 知识库: {kb_name}")
    try:
        kb = kb_mgr.get_knowledge_base(kb_name)
        if not kb:
            available_kbs = kb_mgr.list_knowledge_bases()
            kb_list = ", ".join([kb['name'] for kb in available_kbs])
            return f"错误：知识库 '{kb_name}' 不存在。可用知识库: {kb_list}"
        results = kb.search(query)
        if not results:
            return f"在知识库 '{kb_name}' 中未找到相关信息。"
        return _format_results(results, query, kb_name)
    except Exception as e:
        logger.error(f"知识库搜索失败: {str(e)}")
        return f"搜索失败: {str(e)}"
