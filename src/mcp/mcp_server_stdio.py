# -*- coding: utf-8 -*-
"""
@File    : mcp_server_stdio.py
@Time    : 2025/12/25 16:56
@Desc    : 本地MCP STDIO服务
"""
import sys
from pathlib import Path
from typing import Optional, Dict
from mcp.server.fastmcp import FastMCP
from langchain_community.tools import DuckDuckGoSearchRun

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.mcp.tool_funcs.calculator import calculate

server = FastMCP("LocalMCP")
search = DuckDuckGoSearchRun()


@server.tool(
    name="calculator",
    description="执行数学计算，支持常用三角/对数/指数等函数"
)
def calculator_tool(
        expression: str,
        variables: Optional[Dict[str, float]] = None
) -> str:
    """
    执行数学计算

    Args:
        expression: 数学表达式，如 "2 + 3 * 4", "sqrt(16)", "sin(pi/2)"
        variables: 可选自定义变量，如 {"x": 10}

    Returns:
        计算结果
    """
    return calculate(expression, variables)


@server.tool(
    name="web_search",
    description="在互联网上搜索信息"
)
def web_search(query: str) -> str:
    """
    在互联网上搜索信息

    Args:
        query: 搜索关键字

    Returns:
        搜索结果
    """
    return search.invoke(query)


if __name__ == "__main__":
    server.run(transport="stdio")
