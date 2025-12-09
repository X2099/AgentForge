# -*- coding: utf-8 -*-
"""
@File    : knowledge_base.py
@Time    : 2025/12/9 11:56
@Desc    : 
"""
from typing import Dict, Any, List, Optional
import logging
from ...knowledge.kb_manager import KnowledgeBaseManager

logger = logging.getLogger(__name__)


class KnowledgeBaseTool:
    """知识库工具"""

    def __init__(self, kb_manager: Optional[KnowledgeBaseManager] = None):
        """
        初始化知识库工具

        Args:
            kb_manager: 知识库管理器
        """
        self.kb_manager = kb_manager or KnowledgeBaseManager()

    def get_tool_schema(self) -> Dict[str, Any]:
        """获取工具模式"""
        return {
            "name": "knowledge_base_search",
            "description": "在知识库中搜索相关信息",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    },
                    "kb_name": {
                        "type": "string",
                        "description": "知识库名称",
                        "default": "default"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> str:
        """执行知识库搜索"""
        query = arguments.get("query", "")
        kb_name = arguments.get("kb_name", "default")
        max_results = arguments.get("max_results", 5)

        if not query:
            return "错误：搜索查询不能为空"

        logger.info(f"知识库搜索: {query}, 知识库: {kb_name}")

        try:
            # 获取知识库
            kb = self.kb_manager.get_knowledge_base(kb_name)
            if not kb:
                available_kbs = self.kb_manager.list_knowledge_bases()
                kb_list = ", ".join([kb["name"] for kb in available_kbs])
                return f"错误：知识库 '{kb_name}' 不存在。可用知识库: {kb_list}"

            # 执行搜索
            results = kb.search(query, k=max_results)

            # 格式化结果
            if not results:
                return f"在知识库 '{kb_name}' 中未找到相关信息。"

            formatted = self._format_results(results, query, kb_name)
            return formatted

        except Exception as e:
            logger.error(f"知识库搜索失败: {str(e)}")
            return f"搜索失败: {str(e)}"

    def _format_results(self,
                        results: List[Any],
                        query: str,
                        kb_name: str) -> str:
        """格式化搜索结果"""
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
