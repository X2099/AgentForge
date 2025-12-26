# -*- coding: utf-8 -*-
"""
@File    : mcp_server_http.py
@Time    : 2025/12/26 8:44
@Desc    : 本地MCP HTTP服务
"""
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.mcp.tool_funcs.knowledge_search import search, KnowledgeSearchArgs

server = FastMCP("LocalHttpMCP")


@server.tool(
    name="knowledge_search",
    description="从知识库中检索信息"
)
def knowledge_search_tool(query: str, kb_name: str):
    """
    从知识库中检索信息

    Args:
        query: 检索关键词
        kb_name: 知识库名称，可选范围：ai_knowledge，AncientChineseLiterature

    Returns:
        检索结果
    """
    return search(query=query, kb_name=kb_name)


if __name__ == "__main__":
    server.run(transport="streamable-http")
