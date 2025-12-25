# -*- coding: utf-8 -*-
"""
@File    : amap_mcp.py
@Time    : 2025/12/25 15:16
@Desc    : 
"""
import asyncio
import os
from pprint import pprint

from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient

# 加载环境变量
load_dotenv()

client = MultiServerMCPClient(
    {
        "AmapMcpServers": {
            "transport": "http",
            "url": f"https://mcp.amap.com/mcp?key={os.environ['AMAP_MCP_KEY']}",
        }
    }
)


async def main():
    tools = await client.get_tools()
    for tool in tools:
        print(tool.name)
        print(tool.description)
        print(tool.input_schema.schema())
        tool.ainvoke()
        break


if __name__ == '__main__':
    asyncio.run(main())
