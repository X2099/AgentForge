# -*- coding: utf-8 -*-
"""
@File    : mcp_client_example.py
@Time    : 2025/12/9 12:02
@Desc    :
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.mcp.mcp_client import MCPClient
from src.mcp.transports import TransportType


async def main():
    print("=== MCP客户端示例 ===\n")

    # 1. 创建客户端（HTTP模式）
    client = MCPClient(
        transport_type=TransportType.HTTP,
        transport_config={
            "url": "http://localhost:8000/mcp"
        }
    )

    async with client.connection():
        # 2. 列出可用工具
        print("1. 列出可用工具...")
        tools = await client.list_tools()

        if tools:
            print(f"找到 {len(tools)} 个工具:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
        else:
            print("未找到工具")
            return

        print()

        # 3. 调用计算器工具
        print("2. 调用计算器工具...")
        result = await client.call_tool_simple(
            "calculator",
            {"expression": "2 + 3 * 4"}
        )
        print(f"结果: {result}")
        print()

        # 4. 调用问候工具
        print("3. 调用问候工具...")
        result = await client.call_tool_simple(
            "greet",
            {"name": "Alice"}
        )
        print(f"结果: {result}")
        print()

        # 5. 调用网页搜索工具（模拟）
        print("4. 调用网页搜索工具...")
        result = await client.call_tool_simple(
            "web_search",
            {"query": "Python programming", "max_results": 3}
        )
        print(f"搜索结果:\n{result}")


if __name__ == "__main__":
    asyncio.run(main())
