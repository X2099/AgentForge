# -*- coding: utf-8 -*-
"""
@File    : tool_nodes.py
@Time    : 2025/12/9 10:18
@Desc    : 基于LangGraph标准的工具节点
"""
from typing import Dict, Any, List, Optional
import json
import asyncio
from langchain_core.messages import ToolMessage, AIMessage
from langchain_core.tools import BaseTool

from ..state.base_state import GraphState

import logging

logger = logging.getLogger(__name__)


def create_tool_executor_node(tools: List[BaseTool]):
    """
    创建工具执行节点（LangGraph标准）
    
    Args:
        tools: LangChain Tools列表
        name: 节点名称
        
    Returns:
        节点函数
    """
    # 创建工具字典
    tool_map = {tool.name: tool for tool in tools}
    
    async def tool_executor_node(state: GraphState) -> Dict[str, Any]:
        """
        工具执行节点
        
        从消息中提取工具调用，执行工具，返回工具消息
        """
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        
        # 检查最后一条消息是否是AI消息并包含工具调用
        if not isinstance(last_message, AIMessage):
            return {}
        
        tool_calls = last_message.tool_calls if hasattr(last_message, "tool_calls") else []
        if not tool_calls:
            return {}
        
        # 执行工具调用
        tool_messages = []
        tool_results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
            tool_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
            tool_args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
            
            if tool_name not in tool_map:
                error_msg = f"工具 '{tool_name}' 未找到"
                logger.warning(error_msg)
                tool_message = ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_id
                )
                tool_messages.append(tool_message)
                tool_results.append({
                    "tool_name": tool_name,
                    "success": False,
                    "error": error_msg
                })
                continue
            
            tool = tool_map[tool_name]
            
            try:
                # 执行工具（支持同步和异步）
                if asyncio.iscoroutinefunction(tool.invoke):
                    result = await tool.ainvoke(tool_args)
                else:
                    result = tool.invoke(tool_args)
                
                # 转换为字符串
                if isinstance(result, dict):
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)
                else:
                    result_str = str(result)
                
                # 创建工具消息
                tool_message = ToolMessage(
                    content=result_str,
                    tool_call_id=tool_id
                )
                tool_messages.append(tool_message)
                
                tool_results.append({
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "result": result,
                    "success": True
                })
                
                logger.info(f"工具 '{tool_name}' 执行成功")
                
            except Exception as e:
                error_msg = f"工具执行失败: {str(e)}"
                logger.error(f"工具 '{tool_name}' 执行失败: {e}", exc_info=True)
                
                tool_message = ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_id
                )
                tool_messages.append(tool_message)
                
                tool_results.append({
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "error": str(e),
                    "success": False
                })
        
        return {
            "messages": tool_messages,
            "tool_results": tool_results
        }
    
    return tool_executor_node


def create_tool_router_node(
    tools: List[BaseTool],
    name: str = "tool_router",
    llm_client: Optional[Any] = None
):
    """
    创建工具路由节点（使用LLM选择工具）
    
    Args:
        tools: LangChain Tools列表
        name: 节点名称
        llm_client: LLM客户端（用于智能路由）
        
    Returns:
        节点函数
    """
    tool_map = {tool.name: tool for tool in tools}
    
    async def tool_router_node(state: AgentState) -> Dict[str, Any]:
        """
        工具路由节点
        
        根据任务选择合适的工具
        """
        # 获取当前任务/查询
        messages = state.get("messages", [])
        last_user_msg = None
        
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                last_user_msg = msg
                break
            elif isinstance(msg, dict) and msg.get("type") == "human":
                last_user_msg = msg
                break
        
        if not last_user_msg:
            return {"selected_tools": []}
        
        query = last_user_msg.content if hasattr(last_user_msg, "content") else last_user_msg.get("content", "")
        
        # 简单的关键词匹配（可以扩展为使用LLM进行智能选择）
        selected_tools = []
        
        # 提取工具名称用于匹配
        for tool in tools:
            tool_name_lower = tool.name.lower()
            query_lower = query.lower()
            
            # 检查工具名称或描述是否匹配查询
            if tool_name_lower in query_lower:
                selected_tools.append(tool.name)
                continue
            
            if hasattr(tool, "description"):
                if any(keyword in query_lower for keyword in tool.description.lower().split()[:5]):
                    selected_tools.append(tool.name)
        
        return {
            "selected_tools": selected_tools,
            "available_tools": [tool.name for tool in tools]
        }
    
    return tool_router_node
