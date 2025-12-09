# -*- coding: utf-8 -*-
"""
@File    : openai_provider.py
@Time    : 2025/12/9 10:32
@Desc    : 
"""
import openai
from openai import OpenAI, AsyncOpenAI
from typing import List, Dict, Any, Optional, AsyncGenerator
from typing import Generator as SyncGenerator
import logging

from .base_provider import BaseProvider
from ..schemas.messages import ChatRequest, ChatResponse, StreamResponse
from ..utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI提供商"""

    # OpenAI模型定价（美元/1000 tokens）
    PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-3.5-turbo-instruct": {"input": 0.0015, "output": 0.002},
    }

    def __init__(self,
                 model_name: str = "gpt-3.5-turbo",
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 organization: Optional[str] = None,
                 project: Optional[str] = None,
                 **kwargs):
        """
        初始化OpenAI提供商

        Args:
            model_name: 模型名称
            api_key: API密钥
            base_url: API基础URL
            organization: 组织ID
            project: 项目ID
            **kwargs: 其他参数
        """
        self.organization = organization
        self.project = project
        super().__init__(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )

    def _initialize_client(self):
        """初始化OpenAI客户端"""
        client_kwargs = {
            "api_key": self.api_key,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        if self.organization:
            client_kwargs["organization"] = self.organization

        # 同步客户端
        self.client = OpenAI(**client_kwargs)

        # 异步客户端
        self.async_client = AsyncOpenAI(**client_kwargs)

        # Token计数器
        self.token_counter = TokenCounter()

        logger.info(f"OpenAI客户端初始化完成 - 模型: {self.model_name}")

    def _call_api(self, request: ChatRequest) -> ChatResponse:
        """调用OpenAI API"""
        try:
            # 准备参数
            params = self._prepare_openai_params(request)

            # 调用API
            response = self.client.chat.completions.create(**params)

            # 转换为标准格式
            return self._convert_to_standard_format(response)

        except openai.APIConnectionError as e:
            logger.error(f"OpenAI连接错误: {str(e)}")
            raise
        except openai.RateLimitError as e:
            logger.error(f"OpenAI速率限制: {str(e)}")
            raise
        except openai.APIStatusError as e:
            logger.error(f"OpenAI API错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"OpenAI调用未知错误: {str(e)}")
            raise

    async def _acall_api(self, request: ChatRequest) -> ChatResponse:
        """异步调用OpenAI API"""
        try:
            # 准备参数
            params = self._prepare_openai_params(request)

            # 异步调用API
            response = await self.async_client.chat.completions.create(**params)

            # 转换为标准格式
            return self._convert_to_standard_format(response)

        except Exception as e:
            logger.error(f"OpenAI异步调用失败: {str(e)}")
            raise

    def _call_stream_api(self, request: ChatRequest) -> SyncGenerator[StreamResponse, None, None]:
        """调用流式API"""
        try:
            # 准备参数
            params = self._prepare_openai_params(request)

            # 流式调用
            stream = self.client.chat.completions.create(**params)

            for chunk in stream:
                # 转换为标准格式
                standard_chunk = self._convert_stream_chunk(chunk)
                yield standard_chunk

        except Exception as e:
            logger.error(f"OpenAI流式调用失败: {str(e)}")
            raise

    async def _acall_stream_api(self, request: ChatRequest) -> AsyncGenerator[StreamResponse, None]:
        """异步调用流式API"""
        try:
            # 准备参数
            params = self._prepare_openai_params(request)

            # 异步流式调用
            stream = await self.async_client.chat.completions.create(**params)

            async for chunk in stream:
                # 转换为标准格式
                standard_chunk = self._convert_stream_chunk(chunk)
                yield standard_chunk

        except Exception as e:
            logger.error(f"OpenAI异步流式调用失败: {str(e)}")
            raise

    def _prepare_openai_params(self, request: ChatRequest) -> Dict[str, Any]:
        """准备OpenAI API参数"""
        params = {
            "model": request.model,
            "messages": [msg.dict(exclude_none=True) for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stop": request.stop,
            "stream": request.stream,
            "n": request.n,
        }

        # 添加工具参数
        if request.tools:
            params["tools"] = [tool.dict(exclude_none=True) for tool in request.tools]
            if request.tool_choice:
                params["tool_choice"] = request.tool_choice

        # 移除None值
        params = {k: v for k, v in params.items() if v is not None}

        return params

    def _convert_to_standard_format(self, response) -> ChatResponse:
        """转换为标准格式"""
        # 提取工具调用
        tool_calls = []
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })

        return ChatResponse(
            id=response.id,
            created=response.created,
            model=response.model,
            choices=[{
                "index": choice.index,
                "message": {
                    "role": choice.message.role,
                    "content": choice.message.content or "",
                    "tool_calls": tool_calls
                },
                "finish_reason": choice.finish_reason
            } for choice in response.choices],
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            system_fingerprint=response.system_fingerprint
        )

    def _convert_stream_chunk(self, chunk) -> StreamResponse:
        """转换流式chunk"""
        # 提取工具调用
        tool_calls = []
        if (chunk.choices and chunk.choices[0].delta and
                chunk.choices[0].delta.tool_calls):
            for tool_call in chunk.choices[0].delta.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })

        return StreamResponse(
            id=chunk.id,
            object=chunk.object,
            created=chunk.created,
            model=chunk.model,
            choices=[{
                "index": choice.index,
                "delta": {
                    "role": choice.delta.role,
                    "content": choice.delta.content or "",
                    "tool_calls": tool_calls
                } if choice.delta else {},
                "finish_reason": choice.finish_reason
            } for choice in chunk.choices]
        )

    def calculate_cost(self, tokens: int) -> float:
        """计算成本"""
        model_pricing = self.PRICING.get(self.model_name)
        if not model_pricing:
            # 如果找不到精确匹配，尝试模糊匹配
            for model_pattern, pricing in self.PRICING.items():
                if model_pattern in self.model_name:
                    model_pricing = pricing
                    break

        if model_pricing:
            # 简化计算：假设50%输入，50%输出
            input_cost = (tokens * 0.5) * model_pricing["input"] / 1000
            output_cost = (tokens * 0.5) * model_pricing["output"] / 1000
            return input_cost + output_cost

        return 0.0

    def _get_max_context_length(self) -> int:
        """获取最大上下文长度"""
        context_lengths = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-instruct": 4096,
        }

        for model_pattern, length in context_lengths.items():
            if model_pattern in self.model_name:
                return length

        return 4096  # 默认值

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-instruct",
        ]

    def count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        return self.token_counter.count_tokens(text, self.model_name)
