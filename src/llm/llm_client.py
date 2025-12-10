# -*- coding: utf-8 -*-
"""
@File    : llm_client.py
@Time    : 2025/12/9 10:37
@Desc    : 基于LangChain的LLM客户端
"""
from typing import List, Dict, Any, Optional, Union
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM客户端 - 基于LangChain实现
    
    直接使用LangChain的ChatModels，提供统一的接口
    """

    def __init__(
            self,
            provider_type: str = "openai",
            model_name: str = "gpt-3.5-turbo",
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            timeout: int = 30,
            max_retries: int = 3,
            **kwargs
    ):
        """
        初始化LLM客户端
        
        Args:
            provider_type: 提供商类型 (openai, anthropic)
            model_name: 模型名称
            api_key: API密钥
            base_url: API基础URL
            temperature: 温度参数
            max_tokens: 最大生成token数
            timeout: 超时时间
            max_retries: 最大重试次数
            **kwargs: 其他参数
        """
        self.provider_type = provider_type
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

        # 创建LangChain ChatModel
        self.chat_model = self._create_chat_model(
            provider_type=provider_type,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs
        )

        # 统计信息
        self.call_count = 0
        self.total_tokens = 0

        logger.info(f"LLM客户端初始化完成 - 提供商: {provider_type}, 模型: {model_name}")

    def _create_chat_model(
            self,
            provider_type: str,
            model_name: str,
            api_key: Optional[str],
            base_url: Optional[str],
            temperature: float,
            max_tokens: Optional[int],
            timeout: int,
            max_retries: int,
            **kwargs
    ) -> BaseChatModel:
        """创建LangChain ChatModel"""
        common_params = {
            "model": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "max_retries": max_retries,
            **kwargs
        }

        if provider_type.lower() == "openai":
            if api_key:
                common_params["api_key"] = api_key
            if base_url:
                common_params["base_url"] = base_url
            return ChatOpenAI(**common_params)

        elif provider_type.lower() == "deepseek":
            if api_key:
                common_params["api_key"] = api_key
            return ChatDeepSeek(**common_params)

        elif provider_type.lower() == "anthropic":
            if api_key:
                common_params["api_key"] = api_key
            return ChatAnthropic(**common_params)

        else:
            raise ValueError(f"不支持的提供商类型: {provider_type}")

    def _convert_messages(self, messages: List[Union[Dict[str, Any], BaseMessage]]) -> List[BaseMessage]:
        """
        将消息转换为LangChain消息格式
        
        Args:
            messages: 消息列表（可以是字典或BaseMessage）
            
        Returns:
            LangChain消息列表
        """
        langchain_messages = []

        for msg in messages:
            if isinstance(msg, BaseMessage):
                langchain_messages.append(msg)
            elif isinstance(msg, dict):
                role = msg.get("role", msg.get("type", "user"))
                content = msg.get("content", "")

                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                elif role == "user" or role == "human":
                    langchain_messages.append(HumanMessage(content=content))
                elif role == "assistant" or role == "ai":
                    langchain_messages.append(AIMessage(content=content))
                elif role == "tool":
                    tool_call_id = msg.get("tool_call_id", "")
                    langchain_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))
                else:
                    # 默认作为用户消息
                    langchain_messages.append(HumanMessage(content=content))
            else:
                # 其他类型，转换为字符串
                langchain_messages.append(HumanMessage(content=str(msg)))

        return langchain_messages

    def chat(
            self,
            messages: List[Union[Dict[str, Any], BaseMessage]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            tools: Optional[List[BaseTool]] = None,
            tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
            **kwargs
    ) -> AIMessage:
        """
        聊天接口（同步）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            tools: 工具列表（LangChain Tools）
            tool_choice: 工具选择策略
            **kwargs: 其他参数
            
        Returns:
            AIMessage（LangChain消息类型）
        """
        # 转换消息
        langchain_messages = self._convert_messages(messages)

        # 准备调用参数
        invoke_kwargs = {}
        if temperature is not None:
            invoke_kwargs["temperature"] = temperature
        if max_tokens is not None:
            invoke_kwargs["max_tokens"] = max_tokens
        if tools:
            invoke_kwargs["tools"] = tools
        if tool_choice:
            invoke_kwargs["tool_choice"] = tool_choice
        invoke_kwargs.update(kwargs)

        try:
            # 调用LangChain ChatModel
            if tools:
                # 绑定工具
                model_with_tools = self.chat_model.bind_tools(tools)
                response = model_with_tools.invoke(langchain_messages, **invoke_kwargs)
            else:
                response = self.chat_model.invoke(langchain_messages, **invoke_kwargs)

            # 更新统计
            self.call_count += 1
            if hasattr(response, "response_metadata") and response.response_metadata:
                token_usage = response.response_metadata.get("token_usage", {})
                self.total_tokens += token_usage.get("total_tokens", 0)

            return response

        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}", exc_info=True)
            raise

    async def achat(
            self,
            messages: List[Union[Dict[str, Any], BaseMessage]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            tools: Optional[List[BaseTool]] = None,
            tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
            **kwargs
    ) -> AIMessage:
        """
        异步聊天接口
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            tools: 工具列表（LangChain Tools）
            tool_choice: 工具选择策略
            **kwargs: 其他参数
            
        Returns:
            AIMessage（LangChain消息类型）
        """
        # 转换消息
        langchain_messages = self._convert_messages(messages)

        # 准备调用参数
        invoke_kwargs = {}
        if temperature is not None:
            invoke_kwargs["temperature"] = temperature
        if max_tokens is not None:
            invoke_kwargs["max_tokens"] = max_tokens
        if tools:
            invoke_kwargs["tools"] = tools
        if tool_choice:
            invoke_kwargs["tool_choice"] = tool_choice
        invoke_kwargs.update(kwargs)

        try:
            # 异步调用LangChain ChatModel
            if tools:
                model_with_tools = self.chat_model.bind_tools(tools)
                response = await model_with_tools.ainvoke(langchain_messages, **invoke_kwargs)
            else:
                response = await self.chat_model.ainvoke(langchain_messages, **invoke_kwargs)

            # 更新统计
            self.call_count += 1
            if hasattr(response, "response_metadata") and response.response_metadata:
                token_usage = response.response_metadata.get("token_usage", {})
                self.total_tokens += token_usage.get("total_tokens", 0)

            return response

        except Exception as e:
            logger.error(f"LLM异步调用失败: {str(e)}", exc_info=True)
            raise

    def stream(
            self,
            messages: List[Union[Dict[str, Any], BaseMessage]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            tools: Optional[List[BaseTool]] = None,
            **kwargs
    ):
        """
        流式生成（同步）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            tools: 工具列表
            **kwargs: 其他参数
            
        Yields:
            AIMessage chunks
        """
        langchain_messages = self._convert_messages(messages)

        invoke_kwargs = {}
        if temperature is not None:
            invoke_kwargs["temperature"] = temperature
        if max_tokens is not None:
            invoke_kwargs["max_tokens"] = max_tokens
        invoke_kwargs.update(kwargs)

        if tools:
            model_with_tools = self.chat_model.bind_tools(tools)
            stream = model_with_tools.stream(langchain_messages, **invoke_kwargs)
        else:
            stream = self.chat_model.stream(langchain_messages, **invoke_kwargs)

        for chunk in stream:
            yield chunk

    async def astream(
            self,
            messages: List[Union[Dict[str, Any], BaseMessage]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            tools: Optional[List[BaseTool]] = None,
            **kwargs
    ):
        """
        异步流式生成
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            tools: 工具列表
            **kwargs: 其他参数
            
        Yields:
            AIMessage chunks
        """
        langchain_messages = self._convert_messages(messages)

        invoke_kwargs = {}
        if temperature is not None:
            invoke_kwargs["temperature"] = temperature
        if max_tokens is not None:
            invoke_kwargs["max_tokens"] = max_tokens
        invoke_kwargs.update(kwargs)

        if tools:
            model_with_tools = self.chat_model.bind_tools(tools)
            stream = model_with_tools.astream(langchain_messages, **invoke_kwargs)
        else:
            stream = self.chat_model.astream(langchain_messages, **invoke_kwargs)

        async for chunk in stream:
            yield chunk

    def get_content(self) -> str:
        """兼容性方法：获取最后一条消息的内容（不推荐使用）"""
        return ""

    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """兼容性方法：获取工具调用（不推荐使用）"""
        return []

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "provider": self.provider_type,
            "model": self.model_name,
            "call_count": self.call_count,
            "total_tokens": self.total_tokens
        }

    @property
    def model(self) -> BaseChatModel:
        """获取底层的LangChain ChatModel"""
        return self.chat_model
