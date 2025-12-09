# -*- coding: utf-8 -*-
"""
@File    : base_provider.py
@Time    : 2025/12/9 10:31
@Desc    : 
"""
from abc import abstractmethod
from typing import List, Dict, Any, AsyncGenerator
from typing import Generator as SyncGenerator
import time
from functools import wraps
import logging
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)

from ..llm_base import LLMBase
from ..schemas.messages import ChatRequest, ChatResponse, StreamResponse

logger = logging.getLogger(__name__)


def retry_decorator(max_retries: int = 3):
    """重试装饰器"""

    def decorator(func):
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((Exception,)),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


class BaseProvider(LLMBase):
    """提供商基类"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = None
        self._initialize_client()

    @abstractmethod
    def _initialize_client(self):
        """初始化客户端"""
        pass

    @retry_decorator(max_retries=3)
    def generate(self,
                 messages: List[Dict[str, Any]],
                 **kwargs) -> ChatResponse:
        """生成文本（带重试）"""
        try:
            start_time = time.time()

            # 准备请求
            request = self._prepare_request(messages, **kwargs)

            # 调用API
            response = self._call_api(request)

            # 更新统计
            self._update_stats(response)

            # 计算成本
            if response.usage:
                tokens = response.usage.get("total_tokens", 0)
                self.total_cost += self.calculate_cost(tokens)

            # 记录日志
            elapsed = time.time() - start_time
            logger.info(f"LLM调用完成 - 模型: {self.model_name}, "
                        f"耗时: {elapsed:.2f}s, "
                        f"Tokens: {response.usage.get('total_tokens', 0) if response.usage else 0}")

            return response

        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}", exc_info=True)
            raise

    @retry_decorator(max_retries=3)
    async def agenerate(self,
                        messages: List[Dict[str, Any]],
                        **kwargs) -> ChatResponse:
        """异步生成文本（带重试）"""
        try:
            start_time = time.time()

            # 准备请求
            request = self._prepare_request(messages, **kwargs)

            # 调用API
            response = await self._acall_api(request)

            # 更新统计
            self._update_stats(response)

            # 计算成本
            if response.usage:
                tokens = response.usage.get("total_tokens", 0)
                self.total_cost += self.calculate_cost(tokens)

            # 记录日志
            elapsed = time.time() - start_time
            logger.info(f"LLM异步调用完成 - 模型: {self.model_name}, "
                        f"耗时: {elapsed:.2f}s, "
                        f"Tokens: {response.usage.get('total_tokens', 0) if response.usage else 0}")

            return response

        except Exception as e:
            logger.error(f"LLM异步调用失败: {str(e)}", exc_info=True)
            raise

    @abstractmethod
    def _call_api(self, request: ChatRequest) -> ChatResponse:
        """调用API"""
        pass

    @abstractmethod
    async def _acall_api(self, request: ChatRequest) -> ChatResponse:
        """异步调用API"""
        pass

    @abstractmethod
    def _call_stream_api(self, request: ChatRequest) -> SyncGenerator[StreamResponse, None, None]:
        """调用流式API"""
        pass

    @abstractmethod
    async def _acall_stream_api(self, request: ChatRequest) -> AsyncGenerator[StreamResponse, None]:
        """异步调用流式API"""
        pass

    def stream(self,
               messages: List[Dict[str, Any]],
               **kwargs) -> SyncGenerator[StreamResponse, None, None]:
        """流式生成"""
        request = self._prepare_request(messages, **kwargs)
        request.stream = True

        try:
            for chunk in self._call_stream_api(request):
                yield chunk
        except Exception as e:
            logger.error(f"流式生成失败: {str(e)}")
            raise

    async def astream(self,
                      messages: List[Dict[str, Any]],
                      **kwargs) -> AsyncGenerator[StreamResponse, None]:
        """异步流式生成"""
        request = self._prepare_request(messages, **kwargs)
        request.stream = True

        try:
            async for chunk in self._acall_stream_api(request):
                yield chunk
        except Exception as e:
            logger.error(f"异步流式生成失败: {str(e)}")
            raise

    def _create_error_response(self, error_msg: str) -> ChatResponse:
        """创建错误响应"""
        return ChatResponse(
            id=f"error_{int(time.time())}",
            created=int(time.time()),
            model=self.model_name,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"调用失败: {error_msg}"
                },
                "finish_reason": "error"
            }],
            usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        )
