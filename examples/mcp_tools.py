# -*- coding: utf-8 -*-
"""
@File    : mcp_tools.py
@Time    : 2025/12/25 15:16
@Desc    : 
"""
import sys
from pathlib import Path
import asyncio
import os
from pprint import pprint

from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.config import mcp_servers_config

# 加载环境变量
load_dotenv()

client = MultiServerMCPClient(
    {
        # "AmapMcpServers": {
        #     "transport": "http",
        #     "url": f"https://mcp.amap.com/mcp?key={os.environ['AMAP_MCP_KEY']}",
        # },
        "LocalMcpStdio": {
            "transport": "stdio",
            "command": "python",
            "args": ["src/mcp/mcp_server_stdio.py"],
        },
        "LocalMcpHttp": {
            "transport": "http",
            "url": "http://127.0.0.1:8000/mcp",
        },
    }
)

# client = MultiServerMCPClient(mcp_servers_config)


async def main():
    tools = await client.get_tools()
    tools_map = {tool.name: tool for tool in tools}

    # for tool in tools:
    #     print(tool.name)
    #     print(tool.description)
    #     print(tool.input_schema.schema())
    #     print("--------------------\n")

    tool = tools_map['web_search']
    print(tool.name)
    print(tool.description)
    print(tool.input_schema.schema())
    print("--------------------\n")
    result = await tool.ainvoke({'query': '人工智能发展趋势', 'max_results': 3})
    print(result)


if __name__ == '__main__':
    asyncio.run(main())
