# -*- coding: utf-8 -*-
"""
@File    : mcp_config.py
@Time    : 2025/12/26 9:27
@Desc    : 
"""
import os

mcp_servers_config = {
    "AmapMcpServers": {
        "transport": "http",
        "url": f"https://mcp.amap.com/mcp?key={os.environ['AMAP_MCP_KEY']}",
    },
    "LocalMcpServerStdio": {
        "transport": "stdio",
        "command": "python",
        "args": ["src/mcp/mcp_server_stdio.py"]
    },
    "LocalMcpHttp": {
        "transport": "http",
        "url": "http://127.0.0.1:8000/mcp",
    }
}
