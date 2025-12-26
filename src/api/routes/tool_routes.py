# -*- coding: utf-8 -*-
"""
工具管理相关API路由
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any

from langchain_mcp_adapters.client import MultiServerMCPClient

# 创建路由器
router = APIRouter()

# 全局组件（将在应用启动时初始化）
mcp_client: Optional[MultiServerMCPClient] = None


def init_tool_dependencies(mcp_cl):
    """初始化工具路由的依赖"""
    global mcp_client
    mcp_client = mcp_cl


@router.get("/tools/list")
async def list_tools():
    """列出可用工具（包含本地LangChain工具与MCP服务工具）"""
    try:
        tools = []
        if mcp_client:
            mcp_tools = await mcp_client.get_tools()
            tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "args_schema": tool.input_schema.schema(),
                    "source": "mcp"
                }
                for tool in mcp_tools
            ]

        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/call")
async def call_tool(tool_name: str, arguments: Dict[str, Any]):
    """调用工具"""
    try:
        if not mcp_client:
            raise HTTPException(status_code=500, detail="MCP客户端未初始化")
        tools = await mcp_client.get_tools()
        tools_map = {tool.name: tool for tool in tools}
        tool = tools_map.get(tool_name)
        if not tool:
            raise HTTPException(status_code=400, detail=f"没找到工具 {tool_name}")
        result = await tool.ainvoke(arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
