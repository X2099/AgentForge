# -*- coding: utf-8 -*-
"""
@File    : web_search.py
@Time    : 2025/12/9 11:54
@Desc    : 
"""
from typing import Dict, Any, Optional
import aiohttp
from urllib.parse import quote_plus
import logging

logger = logging.getLogger(__name__)


class WebSearchTool:
    """网页搜索工具"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化网页搜索工具

        Args:
            api_key: 搜索API密钥
        """
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def setup(self):
        """设置异步会话"""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None

    async def search_google(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """使用Google搜索"""
        # 注意：实际使用时需要Google Search API密钥
        # 这里使用简单模拟

        if not self.api_key:
            logger.warning("未提供API密钥，使用模拟搜索")
            return self._mock_search(query, max_results)

        try:
            await self.setup()

            # 构建请求URL
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": "YOUR_SEARCH_ENGINE_ID",  # 需要配置
                "q": query,
                "num": max_results
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_search_results(data)
                else:
                    error_text = await response.text()
                    logger.error(f"Google搜索失败: {response.status} - {error_text}")
                    return {"error": f"搜索失败: {response.status}"}

        except Exception as e:
            logger.error(f"Google搜索异常: {str(e)}")
            return {"error": str(e)}

    async def search_duckduckgo(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """使用DuckDuckGo搜索"""
        try:
            await self.setup()

            # DuckDuckGo HTML搜索
            url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"

            async with self.session.get(url, headers={
                "User-Agent": "MCP-Tool/1.0"
            }) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_ddgo_html(html, max_results)
                else:
                    return {"error": f"搜索失败: {response.status}"}

        except Exception as e:
            logger.error(f"DuckDuckGo搜索异常: {str(e)}")
            return {"error": str(e)}

    def _mock_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """模拟搜索"""
        import time
        time.sleep(0.5)  # 模拟延迟

        results = []
        for i in range(max_results):
            results.append({
                "title": f"关于 '{query}' 的搜索结果 {i + 1}",
                "link": f"https://example.com/result{i + 1}",
                "snippet": f"这是关于 '{query}' 的第 {i + 1} 个搜索结果摘要。",
                "source": "模拟搜索"
            })

        return {
            "query": query,
            "results": results,
            "total_results": max_results,
            "source": "mock"
        }

    def _format_search_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化搜索结果"""
        results = []

        if "items" in data:
            for item in data["items"]:
                result = {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "google"
                }
                results.append(result)

        return {
            "query": data.get("queries", {}).get("request", [{}])[0].get("searchTerms", ""),
            "results": results,
            "total_results": data.get("searchInformation", {}).get("totalResults", len(results)),
            "source": "google"
        }

    def _parse_ddgo_html(self, html: str, max_results: int) -> Dict[str, Any]:
        """解析DuckDuckGo HTML"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # 查找结果元素
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

        return {
            "results": results,
            "total_results": len(results),
            "source": "duckduckgo"
        }

    def get_tool_schema(self) -> Dict[str, Any]:
        """获取工具模式"""
        return {
            "name": "web_search",
            "description": "在互联网上搜索信息",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词"
                    },
                    "engine": {
                        "type": "string",
                        "description": "搜索引擎",
                        "enum": ["google", "duckduckgo", "auto"],
                        "default": "auto"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> str:
        """执行搜索"""
        query = arguments.get("query", "")
        engine = arguments.get("engine", "auto")
        max_results = arguments.get("max_results", 5)

        if not query:
            return "错误：查询词不能为空"

        logger.info(f"执行搜索: {query}, 引擎: {engine}")

        try:
            if engine == "google":
                result = await self.search_google(query, max_results)
            elif engine == "duckduckgo":
                result = await self.search_duckduckgo(query, max_results)
            else:
                # 自动选择
                if self.api_key:
                    result = await self.search_google(query, max_results)
                else:
                    result = await self.search_duckduckgo(query, max_results)

            # 格式化结果
            if "error" in result:
                return f"搜索失败: {result['error']}"

            formatted = self._format_results_text(result)
            return formatted

        except Exception as e:
            logger.error(f"搜索执行失败: {str(e)}")
            return f"搜索失败: {str(e)}"

    def _format_results_text(self, result: Dict[str, Any]) -> str:
        """格式化结果为文本"""
        import json

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
