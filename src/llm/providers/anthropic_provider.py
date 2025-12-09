# -*- coding: utf-8 -*-
"""
@File    : anthropic_provider.py
@Time    : 2025/12/9 10:34
@Desc    : 
"""
import anthropic
from typing import List, Dict, Any, Optional, AsyncGenerator
from typing import Generator as SyncGenerator
import time
import logging

from .base_provider import BaseProvider
from ..schemas.messages import ChatRequest, ChatResponse, StreamResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic (Claude) 提供商"""

    # Claude模型定价（美元/1000 tokens）
    PRICING = {
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "claude-2.1": {"input": 0.008, "output": 0.024},
        "claude-2.0": {"input": 0.008, "output": 0.024},
        "claude-instant-1.2": {"input": 0.0008, "output": 0.0024},
    }

    def __init__(self,
                 model_name: str = "claude-3-sonnet",
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 **kwargs):
        """
        初始化Anthropic提供商

        Args:
            model_name: 模型名称
            api_key: API密钥
            base_url: API基础URL
            **kwargs: 其他参数
        """
        super().__init__(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )

    def _initialize_client(self):
        """初始化Anthropic客户端"""
        client_kwargs = {
            "api_key": self.api_key,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        # 同步客户端
        self.client = anthropic.Anthropic(**client_kwargs)

        # 异步客户端
        self.async_client = anthropic.AsyncAnthropic(**client_kwargs)

        logger.info(f"Anthropic客户端初始化完成 - 模型: {self.model_name}")

    def _call_api(self, request: ChatRequest) -> ChatResponse:
        """调用Anthropic API"""
        try:
            # 准备参数
            params = self._prepare_anthropic_params(request)

            # 调用API
            response = self.client.messages.create(**params)

            # 转换为标准格式
            return self._convert_to_standard_format(response)

        except anthropic.APIConnectionError as e:
            logger.error(f"Anthropic连接错误: {str(e)}")
            raise
        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic速率限制: {str(e)}")
            raise
        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic API错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Anthropic调用未知错误: {str(e)}")
            raise

    async def _acall_api(self, request: ChatRequest) -> ChatResponse:
        """异步调用Anthropic API"""
        try:
            # 准备参数
            params = self._prepare_anthropic_params(request)

            # 异步调用API
            response = await self.async_client.messages.create(**params)

            # 转换为标准格式
            return self._convert_to_standard_format(response)

        except Exception as e:
            logger.error(f"Anthropic异步调用失败: {str(e)}")
            raise

    def _call_stream_api(self, request: ChatRequest) -> SyncGenerator[StreamResponse, None, None]:
        """调用流式API"""
        try:
            # 准备参数
            params = self._prepare_anthropic_params(request)
            params["stream"] = True

            # 流式调用
            with self.client.messages.stream(**params) as stream:
                for chunk in stream:
                    # 转换为标准格式
                    standard_chunk = self._convert_stream_chunk(chunk)
                    if standard_chunk:
                        yield standard_chunk

        except Exception as e:
            logger.error(f"Anthropic流式调用失败: {str(e)}")
            raise

    async def _acall_stream_api(self, request: ChatRequest) -> AsyncGenerator[StreamResponse, None]:
        """异步调用流式API"""
        try:
            # 准备参数
            params = self._prepare_anthropic_params(request)
            params["stream"] = True

            # 异步流式调用
            async with self.async_client.messages.stream(**params) as stream:
                async for chunk in stream:
                    # 转换为标准格式
                    standard_chunk = self._convert_stream_chunk(chunk)
                    if standard_chunk:
                        yield standard_chunk

        except Exception as e:
            logger.error(f"Anthropic异步流式调用失败: {str(e)}")
            raise

    def _prepare_anthropic_params(self, request: ChatRequest) -> Dict[str, Any]:
        """准备Anthropic API参数"""
        # 转换消息格式
        messages = []
        system_messages = []

        for msg in request.messages:
            if msg.role == "system":
                system_messages.append(msg.content)
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        params = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 4096,
            "top_p": request.top_p,
            "stop_sequences": request.stop if isinstance(request.stop, list) else [
                request.stop] if request.stop else None,
            "stream": False,  # 流式单独处理
        }

        # 添加系统消息
        if system_messages:
            params["system"] = "\n".join(system_messages)

        # 移除None值
        params = {k: v for k, v in params.items() if v is not None}

        return params

    def _convert_to_standard_format(self, response) -> ChatResponse:
        """转换为标准格式"""
        # Anthropic响应格式转换
        content_text = ""
        if response.content:
            # 提取文本内容
            text_parts = []
            for content in response.content:
                if content.type == "text":
                    text_parts.append(content.text)
            content_text = "".join(text_parts)

        return ChatResponse(
            id=response.id,
            created=int(time.time()),  # Anthropic没有返回created时间
            model=response.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content_text
                },
                "finish_reason": response.stop_reason
            }],
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            system_fingerprint=None
        )

    def _convert_stream_chunk(self, chunk) -> Optional[StreamResponse]:
        """转换流式chunk"""
        # 处理不同类型的chunk
        if hasattr(chunk, 'type'):
            if chunk.type == "message_start":
                return None
            elif chunk.type == "content_block_start":
                return None
            elif chunk.type == "content_block_delta":
                return StreamResponse(
                    id="",  # 流式响应没有ID
                    object="chat.completion.chunk",
                    created=int(time.time()),
                    model=self.model_name,
                    choices=[{
                        "index": 0,
                        "delta": {
                            "content": chunk.delta.text
                        },
                        "finish_reason": None
                    }]
                )
            elif chunk.type == "content_block_stop":
                return None
            elif chunk.type == "message_delta":
                return None
            elif chunk.type == "message_stop":
                return StreamResponse(
                    id="",
                    object="chat.completion.chunk",
                    created=int(time.time()),
                    model=self.model_name,
                    choices=[{
                        "index": 0,
                        "delta": {},
                        "finish_reason": chunk.delta.stop_reason
                    }]
                )

        return None

    def calculate_cost(self, tokens: int) -> float:
        """计算成本"""
        model_pricing = self.PRICING.get(self.model_name)
        if not model_pricing:
            # 模糊匹配
            for model_pattern, pricing in self.PRICING.items():
                if model_pattern in self.model_name:
                    model_pricing = pricing
                    break

        if model_pricing:
            # Anthropic区分输入输出token
            # 这里简化计算：假设50%输入，50%输出
            input_cost = (tokens * 0.5) * model_pricing["input"] / 1000
            output_cost = (tokens * 0.5) * model_pricing["output"] / 1000
            return input_cost + output_cost

        return 0.0

    def _get_max_context_length(self) -> int:
        """获取最大上下文长度"""
        context_lengths = {
            "claude-3-5-sonnet": 200000,
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-haiku": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000,
        }

        for model_pattern, length in context_lengths.items():
            if model_pattern in self.model_name:
                return length

        return 100000  # 默认值

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "claude-3-5-sonnet",
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2",
        ]
