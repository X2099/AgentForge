# -*- coding: utf-8 -*-
"""
@File    : llm_nodes.py
@Time    : 2025/12/9 10:17
@Desc    : 
"""
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from .base_node import Node, AsyncNode
from ..state.base_state import AgentState
from src.llm.llm_client import LLMClient
from src.config.system_config import SystemConfig


class LLMNode(Node):
    """LLM节点（完整版）"""

    def __init__(self,
                 name: str,
                 llm_config: Optional[Dict[str, Any]] = None,
                 system_prompt: str = "",
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None):
        super().__init__(name, "llm", "调用大型语言模型")

        # 创建LLM客户端
        if llm_config:
            # 从配置创建
            config_manager = SystemConfig()
            self.llm_client = config_manager.create_client(**llm_config)
        else:
            # 默认配置
            config_manager = SystemConfig()
            self.llm_client = config_manager.create_client()

        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 缓存工具定义
        self._tool_definitions_cache: Dict[str, List[Dict[str, Any]]] = {}

    def execute(self, state: AgentState) -> Dict[str, Any]:
        """执行LLM调用"""
        try:
            # 准备消息
            messages = self._prepare_messages(state)

            # 准备工具
            tools = self._prepare_tools(state)

            # 调用LLM
            start_time = datetime.now()
            response = self.llm_client.chat(
                messages=messages,
                temperature=state.get("temperature", self.temperature),
                max_tokens=state.get("max_tokens", self.max_tokens),
                tools=tools,
                tool_choice=state.get("tool_choice", "auto")
            )

            # 解析响应
            result = self._parse_response(response)

            # 更新状态
            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "llm_response": response,
                "content": result.get("content", ""),
                "tool_calls": result.get("tool_calls", []),
                "execution_time": execution_time,
                "tokens_used": response.usage.get("total_tokens", 0) if response.usage else 0,
                "next_node": "tool_executor" if result.get("tool_calls") else "response_formatter"
            }

        except Exception as e:
            logger.error(f"LLM节点执行失败: {str(e)}")
            return {
                "error": str(e),
                "content": f"抱歉，我遇到了一个错误：{str(e)}",
                "next_node": "error_handler"
            }

    def _prepare_messages(self, state: AgentState) -> List[Dict[str, Any]]:
        """准备消息列表"""
        messages = []

        # 添加系统提示
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        elif "system_prompt" in state:
            messages.append({"role": "system", "content": state["system_prompt"]})

        # 添加历史消息
        if "messages" in state:
            for msg in state["messages"]:
                if isinstance(msg, dict):
                    messages.append({
                        "role": msg.get("type", "user"),
                        "content": msg.get("content", "")
                    })

        return messages

    def _prepare_tools(self, state: AgentState) -> Optional[List[Dict[str, Any]]]:
        """准备工具定义"""
        if "available_tools" not in state or not state["available_tools"]:
            return None

        tool_names = state["available_tools"]
        cache_key = ",".join(sorted(tool_names))

        # 检查缓存
        if cache_key in self._tool_definitions_cache:
            return self._tool_definitions_cache[cache_key]

        # 从工具注册中心获取工具定义（这里需要工具系统集成）
        # 暂时返回简单定义
        tools = []
        for tool_name in tool_names:
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"调用工具: {tool_name}",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            tools.append(tool_def)

        # 缓存结果
        self._tool_definitions_cache[cache_key] = tools

        return tools

    def _parse_response(self, response) -> Dict[str, Any]:
        """解析LLM响应"""
        result = {
            "content": "",
            "tool_calls": []
        }

        # 获取内容
        result["content"] = response.get_content() or ""

        # 解析工具调用
        tool_calls = response.get_tool_calls()
        for tool_call in tool_calls:
            result["tool_calls"].append({
                "id": tool_call.id,
                "name": tool_call.function.get("name", ""),
                "arguments": json.loads(
                    tool_call.function.get("arguments", "{}")
                )
            })

        return result


class AsyncLLMNode(AsyncNode):
    """异步LLM节点"""

    def __init__(self, name: str, llm_client: LLMClient, **kwargs):
        super().__init__(name, "async_llm", "异步调用大型语言模型")
        self.llm_client = llm_client
        self.kwargs = kwargs

    async def execute_async(self, state: AgentState) -> Dict[str, Any]:
        """异步执行LLM调用"""
        try:
            # 准备消息（与同步版本相同）
            messages = []
            if "system_prompt" in state:
                messages.append({"role": "system", "content": state["system_prompt"]})

            if "messages" in state:
                for msg in state["messages"]:
                    if isinstance(msg, dict):
                        messages.append({
                            "role": msg.get("type", "user"),
                            "content": msg.get("content", "")
                        })

            # 异步调用LLM
            start_time = datetime.now()
            response = await self.llm_client.achat(messages, **self.kwargs)

            # 解析响应
            content = response.get_content() or ""
            tool_calls = response.get_tool_calls()

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "llm_response": response,
                "content": content,
                "tool_calls": [{
                    "id": tc.id,
                    "name": tc.function.get("name", ""),
                    "arguments": json.loads(tc.function.get("arguments", "{}"))
                } for tc in tool_calls],
                "execution_time": execution_time,
                "tokens_used": response.usage.get("total_tokens", 0) if response.usage else 0,
                "next_node": "tool_executor" if tool_calls else "response_formatter"
            }

        except Exception as e:
            logger.error(f"异步LLM节点执行失败: {str(e)}")
            return {
                "error": str(e),
                "content": f"抱歉，异步处理遇到了一个错误：{str(e)}",
                "next_node": "error_handler"
            }
