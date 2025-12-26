# -*- coding: utf-8 -*-
"""
@Desc    : LangChain 原生格式的网页搜索工具
"""
import logging
from typing import Dict, Optional
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WebSearchArgs(BaseModel):
    query: str = Field(..., description="搜索查询词")
    engine: str = Field("auto", description="搜索引擎", pattern="^(google|duckduckgo|auto)$")
    max_results: int = Field(5, ge=1, le=20, description="最大结果数")


async def _search_google(query: str, max_results: int, api_key: Optional[str]) -> Dict[str, any]:
    if not api_key:
        logger.warning("未提供API密钥，使用模拟搜索")
        return _mock_search(query, max_results)

    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": "YOUR_SEARCH_ENGINE_ID", "q": query, "num": max_results}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return _format_search_results(data)
            error_text = await response.text()
            logger.error(f"Google搜索失败: {response.status} - {error_text}")
            return {"error": f"搜索失败: {response.status}"}


async def _search_duckduckgo(query: str, max_results: int) -> Dict[str, any]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"User-Agent": "MCP-Tool/1.0"}) as response:
            if response.status == 200:
                html = await response.text()
                return _parse_ddgo_html(html, max_results)
            return {"error": f"搜索失败: {response.status}"}


def _mock_search(query: str, max_results: int = 5) -> Dict[str, any]:
    results = []
    for i in range(max_results):
        results.append({
            "title": f"关于 '{query}' 的搜索结果 {i + 1}",
            "link": f"https://example.com/result{i + 1}",
            "snippet": f"这是关于 '{query}' 的第 {i + 1} 个搜索结果摘要。",
            "source": "模拟搜索"
        })
    return {"query": query, "results": results, "total_results": max_results, "source": "mock"}


def _format_search_results(data: Dict[str, any]) -> Dict[str, any]:
    results = []
    if "items" in data:
        for item in data["items"]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "google"
            })
    return {
        "query": data.get("queries", {}).get("request", [{}])[0].get("searchTerms", ""),
        "results": results,
        "total_results": data.get("searchInformation", {}).get("totalResults", len(results)),
        "source": "google"
    }


def _parse_ddgo_html(html: str, max_results: int) -> Dict[str, any]:
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    result_elements = soup.find_all('a', class_='result__url')
    for i, elem in enumerate(result_elements[:max_results]):
        title_elem = elem.find_next('h2')
        snippet_elem = elem.find_next('a', class_='result__snippet')
        if title_elem and snippet_elem:
            results.append({
                "title": title_elem.text.strip(),
                "link": elem.text.strip(),
                "snippet": snippet_elem.text.strip(),
                "source": "duckduckgo"
            })
    return {"results": results, "total_results": len(results), "source": "duckduckgo"}


async def _web_search(query: str, engine: str = "auto", max_results: int = 5, api_key: Optional[str] = None) -> str:
    logger.info(f"执行搜索: {query}, 引擎: {engine}")
    if not query:
        return "错误：查询词不能为空"

    try:
        if engine == "google":
            result = await _search_google(query, max_results, api_key)
        elif engine == "duckduckgo":
            result = await _search_duckduckgo(query, max_results)
        else:
            result = await _search_google(query, max_results, api_key) if api_key else await _search_duckduckgo(query, max_results)

        if "error" in result:
            return f"搜索失败: {result['error']}"
        return _format_results_text(result)
    except Exception as e:
        logger.error(f"搜索执行失败: {str(e)}")
        return f"搜索失败: {str(e)}"


def _format_results_text(result: Dict[str, any]) -> str:
    if "results" not in result or not result["results"]:
        return "未找到相关结果"
    lines = [f"搜索: {result.get('query', 'Unknown')}"]
    lines.append(f"来源: {result.get('source', 'Unknown')}")
    lines.append(f"找到 {len(result['results'])} 个结果:")
    lines.append("")
    for i, item in enumerate(result["results"], 1):
        lines.append(f"{i}. {item.get('title', '无标题')}")
        lines.append(f"   链接: {item.get('link', '无链接')}")
        lines.append(f"   摘要: {item.get('snippet', '无摘要')}")
        lines.append("")
    return "\n".join(lines)


# 这里使用闭包携带 api_key，符合 LangChain 的 BaseTool 接口
def create_web_search_tool(api_key: Optional[str] = None) -> StructuredTool:
    async def _wrapped(query: str, engine: str = "auto", max_results: int = 5) -> str:
        return await _web_search(query=query, engine=engine, max_results=max_results, api_key=api_key)

    return StructuredTool.from_function(
        func=_wrapped,
        name="web_search",
        description="在互联网上搜索信息（google/duckduckgo/auto）",
        args_schema=WebSearchArgs,
        coroutine=_wrapped,  # 明确异步
    )


# 默认实例（无 API key，将自动走 duckduckgo 或 mock）
web_search_tool = create_web_search_tool()

__all__ = ["web_search_tool", "create_web_search_tool", "WebSearchArgs"]
