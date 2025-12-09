# -*- coding: utf-8 -*-
"""
@File    : llm_base.py
@Time    : 2025/12/9 10:30
@Desc    : 
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from typing import Generator as SyncGenerator
import logging
from datetime import datetime

from .schemas.messages import (
    Message, ChatRequest, ChatResponse, StreamResponse
)

logger = logging.getLogger(__name__)


class LLMBase(ABC):
    """LLM基类"""

    def __init__(self,
                 model_name: str,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3):
        """
        初始化LLM

        Args:
            model_name: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            api_key: API密钥
            base_url: API基础URL
            timeout: 超时时间
            max_retries: 最大重试次数
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        # 统计信息
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    @abstractmethod
    def generate(self,
                 messages: List[Dict[str, Any]],
                 **kwargs) -> ChatResponse:
        """
        生成文本

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            ChatResponse对象
        """
        pass

    @abstractmethod
    async def agenerate(self,
                        messages: List[Dict[str, Any]],
                        **kwargs) -> ChatResponse:
        """异步生成文本"""
        pass

    @abstractmethod
    def stream(self,
               messages: List[Dict[str, Any]],
               **kwargs) -> SyncGenerator[StreamResponse, None, None]:
        """流式生成文本"""
        pass

    @abstractmethod
    async def astream(self,
                      messages: List[Dict[str, Any]],
                      **kwargs) -> AsyncGenerator[StreamResponse, None]:
        """异步流式生成文本"""
        pass

    def chat(self,
             messages: List[Dict[str, Any]],
             tools: Optional[List[Dict[str, Any]]] = None,
             **kwargs) -> ChatResponse:
        """
        聊天接口（便捷方法）

        Args:
            messages: 消息列表
            tools: 工具定义列表
            **kwargs: 其他参数

        Returns:
            ChatResponse对象
        """
        return self.generate(messages, tools=tools, **kwargs)

    async def achat(self,
                    messages: List[Dict[str, Any]],
                    tools: Optional[List[Dict[str, Any]]] = None,
                    **kwargs) -> ChatResponse:
        """异步聊天接口"""
        return await self.agenerate(messages, tools=tools, **kwargs)

    def format_messages(self, messages: List[Dict[str, Any]]) -> List[Message]:
        """格式化消息"""
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                formatted_messages.append(Message(**msg))
            elif isinstance(msg, Message):
                formatted_messages.append(msg)
            else:
                raise ValueError(f"不支持的message类型: {type(msg)}")
        return formatted_messages

    def _prepare_request(self,
                         messages: List[Dict[str, Any]],
                         **kwargs) -> ChatRequest:
        """准备请求"""
        formatted_messages = self.format_messages(messages)

        # 合并参数
        request_kwargs = {
            "messages": formatted_messages,
            "model": self.model_name,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": kwargs.get("stream", False),
        }

        # 可选参数
        optional_params = ["top_p", "frequency_penalty", "presence_penalty",
                           "stop", "n", "tools", "tool_choice"]
        for param in optional_params:
            if param in kwargs:
                request_kwargs[param] = kwargs[param]

        return ChatRequest(**request_kwargs)

    def _update_stats(self, response: ChatResponse):
        """更新统计信息"""
        self.total_calls += 1
        if response.usage:
            self.total_tokens += response.usage.get("total_tokens", 0)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "model": self.model_name,
            "last_updated": datetime.now().isoformat()
        }

    def reset_stats(self):
        """重置统计信息"""
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    def calculate_cost(self, tokens: int) -> float:
        """计算成本"""
        # 子类应重写此方法
        return 0.0

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "provider": self.__class__.__name__.replace("Provider", ""),
            "supports_streaming": hasattr(self, 'stream'),
            "supports_tools": True,
            "max_context_length": self._get_max_context_length(),
            "available_models": self.get_available_models()
        }

    @abstractmethod
    def _get_max_context_length(self) -> int:
        """获取最大上下文长度"""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        pass
