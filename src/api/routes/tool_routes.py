# -*- coding: utf-8 -*-
"""
工具管理相关API路由
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, List

# 创建路由器
router = APIRouter()

# 全局组件（将在应用启动时初始化）
mcp_client = None


def init_tool_dependencies(mcp_cl):
    """初始化工具路由的依赖"""
    global mcp_client
    mcp_client = mcp_cl


@router.get("/tools/list")
async def list_tools():
    """列出可用工具（包含本地LangChain工具与MCP服务工具）"""
    try:
        from src.tools.tool_manager import get_tool_manager

        tool_manager = get_tool_manager()
        local_tools_info = tool_manager.list_tools(with_metadata=True)
        local_tools = []
        for tool, metadata in local_tools_info:
            local_tools.append({
                "name": tool.name,
                "description": getattr(tool, "description", ""),
                "args_schema": getattr(tool, "args_schema", None).schema() if getattr(tool, "args_schema",
                                                                                      None) else None,
                "source": "local",
                "metadata": metadata or {}
            })

        remote_tools = []
        # if mcp_client:
        #     remote = await mcp_client.list_tools()
        #     remote_tools = [
        #         {
        #             "name": tool.name,
        #             "description": tool.description,
        #             "args_schema": getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None),
        #             "source": "mcp"
        #         }
        #         for tool in remote
        #     ]

        return {"tools": local_tools + remote_tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/call")
async def call_tool(tool_name: str, arguments: Dict[str, Any]):
    """调用工具"""
    try:
        if not mcp_client:
            raise HTTPException(status_code=500, detail="MCP客户端未初始化")

        result = await mcp_client.call_tool_simple(tool_name, arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
