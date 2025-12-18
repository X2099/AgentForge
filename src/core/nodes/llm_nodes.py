# -*- coding: utf-8 -*-
"""
@File    : llm_nodes.py
@Time    : 2025/12/9 10:17
@Desc    : 
"""
from typing import Dict, Any, List, Optional, Union
import json
from datetime import datetime
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)

from .base_node import Node, AsyncNode
from ..state.base_state import AgentState
from src.config.system_config import SystemConfig

logger = logging.getLogger(__name__)


class LLMNode(Node):
    """LLM节点（完整版）"""

    def __init__(
        self,
        name: str,
        llm_config: Optional[Dict[str, Any]] = None,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        super().__init__(name, "llm", "调用大型语言模型")

        # 创建LLM客户端
        config_manager = SystemConfig()
        if llm_config:
            self.llm_model: BaseChatModel = config_manager.create_client(**llm_config)
        else:
            self.llm_model = config_manager.create_client()

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
            langchain_messages = self._convert_messages(messages)

            invoke_kwargs: Dict[str, Any] = {
                "temperature": state.get("temperature", self.temperature),
                "max_tokens": state.get("max_tokens", self.max_tokens),
            }
            if tools:
                invoke_kwargs["tools"] = tools
            if state.get("tool_choice"):
                invoke_kwargs["tool_choice"] = state["tool_choice"]

            if tools:
                response = self.llm_model.invoke(langchain_messages, **invoke_kwargs)
            else:
                response = self.llm_model.invoke(langchain_messages, **invoke_kwargs)

            # 解析响应
            result = self._parse_response(response)

            # 更新状态
            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "llm_response": response,
                "content": result.get("content", ""),
                "tool_calls": result.get("tool_calls", []),
                "execution_time": execution_time,
                "tokens_used": response.response_metadata.get("token_usage", {}).get("total_tokens", 0)
                if hasattr(response, "response_metadata") and response.response_metadata
                else 0,
                "next_node": "tool_executor" if result.get("tool_calls") else "response_formatter"
            }

        except Exception as e:
            logger.error(f"LLM节点执行失败: {str(e)}")
            return {
                "error": str(e),
                "content": f"抱歉，我遇到了一个错误：{str(e)}",
                "next_node": "error_handler"
            }

    def _convert_messages(self, messages: List[Union[Dict[str, Any], BaseMessage]]) -> List[BaseMessage]:
        """将通用消息转换为LangChain消息"""
        langchain_messages: List[BaseMessage] = []

        for msg in messages:
            if isinstance(msg, BaseMessage):
                langchain_messages.append(msg)
                continue

            if isinstance(msg, dict):
                role = msg.get("role", msg.get("type", "user"))
                content = msg.get("content", "")
                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                elif role in {"user", "human"}:
                    langchain_messages.append(HumanMessage(content=content))
                elif role in {"assistant", "ai"}:
                    langchain_messages.append(AIMessage(content=content))
                elif role == "tool":
                    tool_call_id = msg.get("tool_call_id", "")
                    langchain_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))
                else:
                    langchain_messages.append(HumanMessage(content=content))
                continue

            langchain_messages.append(HumanMessage(content=str(msg)))

        return langchain_messages

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
        result["content"] = getattr(response, "content", "") or ""

        # 解析工具调用
        tool_calls = getattr(response, "tool_calls", []) or []
        for tool_call in tool_calls:
            tool_name = ""
            arguments: Any = {}
            tool_id = ""

            if isinstance(tool_call, dict):
                tool_id = tool_call.get("id", "")
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("args") or tool_call.get("arguments", {})
            else:
                tool_id = getattr(tool_call, "id", "")
                tool_name = getattr(tool_call, "name", "")
                arguments = getattr(tool_call, "args", {})
                if not arguments and hasattr(tool_call, "function"):
                    fn = getattr(tool_call, "function", {})
                    arguments = json.loads(fn.get("arguments", "{}")) if isinstance(fn, dict) else {}

            try:
                parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
            except Exception:
                parsed_args = arguments

            result["tool_calls"].append({
                "id": tool_id,
                "name": tool_name,
                "arguments": parsed_args,
            })

        return result


class AsyncLLMNode(AsyncNode):
    """异步LLM节点"""

    def __init__(self, name: str, llm_client: BaseChatModel, **kwargs):
        super().__init__(name, "async_llm", "异步调用大型语言模型")
        self.llm_model = llm_client
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
            response = await self.llm_model.ainvoke(messages, **self.kwargs)

            # 解析响应
            content = getattr(response, "content", "") or ""
            tool_calls = getattr(response, "tool_calls", []) or []

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
                "tokens_used": response.response_metadata.get("token_usage", {}).get("total_tokens", 0)
                if hasattr(response, "response_metadata") and response.response_metadata
                else 0,
                "next_node": "tool_executor" if tool_calls else "response_formatter"
            }

        except Exception as e:
            logger.error(f"异步LLM节点执行失败: {str(e)}")
            return {
                "error": str(e),
                "content": f"抱歉，异步处理遇到了一个错误：{str(e)}",
                "next_node": "error_handler"
            }
