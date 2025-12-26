# -*- coding: utf-8 -*-
"""
@File    : mcp_tool_node.py
@Time    : 2025/12/9 12:02
@Desc    : 
"""
from typing import Dict, Any
import asyncio
import json

from .base_node import AsyncNode
from ..state.base_state import AgentState
from src.mcp.mcp_client import MCPClient
from src.mcp.transports import TransportType


class MCPToolNode(AsyncNode):
    """MCP工具节点"""

    def __init__(self,
                 name: str,
                 mcp_client: MCPClient,
                 tool_name: str,
                 description: str = "MCP工具调用节点"):
        """
        初始化MCP工具节点

        Args:
            name: 节点名称
            mcp_client: MCP客户端
            tool_name: 工具名称
            description: 节点描述
        """
        super().__init__(name, "mcp_tool", description)
        self.mcp_client = mcp_client
        self.tool_name = tool_name
        self.tool_info = None

    async def execute_async(self, state: AgentState) -> Dict[str, Any]:
        """执行工具调用"""
        try:
            # 从状态中提取参数
            if "tool_arguments" in state:
                arguments = state.get("tool_arguments", {})
            else:
                # 尝试从消息中提取
                arguments = self._extract_arguments_from_state(state)

            # 调用工具
            result = await self.mcp_client.call_tool_simple(
                self.tool_name, arguments
            )

            # 更新状态
            return {
                "tool_result": result,
                "tool_name": self.tool_name,
                "tool_arguments": arguments,
                "next_node": "llm"  # 通常调用工具后返回LLM处理
            }

        except Exception as e:
            return {
                "error": str(e),
                "tool_result": f"工具调用失败: {str(e)}",
                "next_node": "error_handler"
            }

    def _extract_arguments_from_state(self, state: AgentState) -> Dict[str, Any]:
        """从状态中提取参数"""
        # 简单的参数提取逻辑
        arguments = {}

        # 检查是否有特定的工具调用
        if "tool_calls" in state:
            for tool_call in state["tool_calls"]:
                if tool_call.get("name") == self.tool_name:
                    arguments = tool_call.get("arguments", {})
                    break

        return arguments


class MCPToolExecutorNode(AsyncNode):
    """MCP工具执行器节点（通用）"""

    def __init__(self,
                 name: str,
                 mcp_client: MCPClient,
                 description: str = "通用MCP工具执行器"):
        """
        初始化MCP工具执行器

        Args:
            name: 节点名称
            mcp_client: MCP客户端
            description: 节点描述
        """
        super().__init__(name, "mcp_tool_executor", description)
        self.mcp_client = mcp_client

    async def execute_async(self, state: AgentState) -> Dict[str, Any]:
        """执行工具调用"""
        try:
            # 获取待执行的工具调用
            tool_calls = state.get("tool_calls", [])
            results = []

            for tool_call in tool_calls:
                tool_name = tool_call.get("name")
                arguments = tool_call.get("arguments", {})

                # 调用工具
                result = await self.mcp_client.call_tool_simple(
                    tool_name, arguments
                )

                results.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result
                })

            # 更新状态
            return {
                "tool_results": results,
                "has_tool_results": len(results) > 0,
                "next_node": "llm" if results else "response_formatter"
            }

        except Exception as e:
            return {
                "error": str(e),
                "tool_results": [],
                "has_tool_results": False,
                "next_node": "error_handler"
            }
