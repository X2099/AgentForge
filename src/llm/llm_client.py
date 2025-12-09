# -*- coding: utf-8 -*-
"""
@File    : llm_client.py
@Time    : 2025/12/9 10:37
@Desc    : 
"""
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from typing import Generator as SyncGenerator
import logging
from datetime import datetime
from functools import lru_cache

from .providers.provider_factory import ProviderFactory
from .schemas.messages import ChatResponse, StreamResponse
from .utils.token_counter import TokenCounter
from .utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端主类"""

    def __init__(self,
                 provider_type: str = "openai",
                 model_name: str = "gpt-3.5-turbo",
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 rate_limit: Optional[Dict[str, int]] = None,
                 **kwargs):
        """
        初始化LLM客户端

        Args:
            provider_type: 提供商类型 (openai, anthropic, local, etc.)
            model_name: 模型名称
            api_key: API密钥
            base_url: API基础URL
            temperature: 温度参数
            max_tokens: 最大生成token数
            timeout: 超时时间
            max_retries: 最大重试次数
            rate_limit: 速率限制 {"requests_per_minute": 60, "tokens_per_minute": 60000}
            **kwargs: 其他提供商特定参数
        """
        self.provider_type = provider_type
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

        # 配置提供商
        provider_config = {
            "model_name": model_name,
            "api_key": api_key,
            "base_url": base_url,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "max_retries": max_retries,
            **kwargs
        }

        # 创建提供商实例
        self.provider = ProviderFactory.create_provider(
            provider_type, provider_config
        )

        # 初始化工具
        self.token_counter = TokenCounter()
        self.rate_limiter = None
        if rate_limit:
            self.rate_limiter = RateLimiter(**rate_limit)

        # 统计信息
        self.call_history: List[Dict[str, Any]] = []
        self.max_history_size = 100

        logger.info(f"LLM客户端初始化完成 - 提供商: {provider_type}, 模型: {model_name}")

    def chat(self,
             messages: List[Dict[str, Any]],
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             tools: Optional[List[Dict[str, Any]]] = None,
             tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
             stream: bool = False,
             **kwargs) -> Union[ChatResponse, SyncGenerator[StreamResponse, None, None]]:
        """
        聊天接口

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            tools: 工具定义列表
            tool_choice: 工具选择策略
            stream: 是否流式输出
            **kwargs: 其他参数

        Returns:
            ChatResponse 或 StreamResponse生成器
        """
        # 应用速率限制
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

        # 记录调用开始
        call_id = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        start_time = datetime.now()

        try:
            # 调用提供商
            if stream:
                return self._stream_chat(
                    call_id, messages, temperature, max_tokens,
                    tools, tool_choice, **kwargs
                )
            else:
                response = self.provider.chat(
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=max_tokens or self.max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                    **kwargs
                )

                # 记录调用结果
                self._record_call(
                    call_id, start_time, messages, response,
                    temperature, max_tokens, tools
                )

                return response

        except Exception as e:
            # 记录错误
            self._record_error(call_id, start_time, messages, str(e))
            logger.error(f"LLM调用失败 - ID: {call_id}, 错误: {str(e)}")
            raise

    async def achat(self,
                    messages: List[Dict[str, Any]],
                    temperature: Optional[float] = None,
                    max_tokens: Optional[int] = None,
                    tools: Optional[List[Dict[str, Any]]] = None,
                    tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
                    stream: bool = False,
                    **kwargs) -> Union[ChatResponse, AsyncGenerator[StreamResponse, None]]:
        """异步聊天接口"""
        # 应用速率限制
        if self.rate_limiter:
            await self.rate_limiter.await_if_needed()

        # 记录调用开始
        call_id = f"acall_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        start_time = datetime.now()

        try:
            # 调用提供商
            if stream:
                return self._astream_chat(
                    call_id, messages, temperature, max_tokens,
                    tools, tool_choice, **kwargs
                )
            else:
                response = await self.provider.achat(
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=max_tokens or self.max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                    **kwargs
                )

                # 记录调用结果
                self._record_call(
                    call_id, start_time, messages, response,
                    temperature, max_tokens, tools
                )

                return response

        except Exception as e:
            # 记录错误
            self._record_error(call_id, start_time, messages, str(e))
            logger.error(f"LLM异步调用失败 - ID: {call_id}, 错误: {str(e)}")
            raise

    def _stream_chat(self,
                     call_id: str,
                     messages: List[Dict[str, Any]],
                     temperature: Optional[float],
                     max_tokens: Optional[int],
                     tools: Optional[List[Dict[str, Any]]],
                     tool_choice: Optional[Union[str, Dict[str, Any]]],
                     **kwargs) -> SyncGenerator[StreamResponse, None, None]:
        """流式聊天"""
        try:
            full_content = ""
            stream = self.provider.stream(
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )

            for chunk in stream:
                # 收集完整内容
                if chunk.choices and chunk.choices[0]["delta"]:
                    content = chunk.choices[0]["delta"].get("content", "")
                    full_content += content

                yield chunk

            # 流结束后记录调用
            end_time = datetime.now()
            elapsed = (end_time - datetime.fromisoformat(call_id.split('_')[1])).total_seconds()

            # 创建模拟响应用于记录
            mock_response = ChatResponse(
                id=chunk.id if hasattr(chunk, 'id') else call_id,
                created=int(datetime.now().timestamp()),
                model=self.model_name,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": full_content
                    },
                    "finish_reason": "stop"
                }],
                usage={
                    "prompt_tokens": 0,  # 流式响应没有usage信息
                    "completion_tokens": len(full_content) // 4,  # 估算
                    "total_tokens": 0
                }
            )

            self._record_call(
                call_id, datetime.fromisoformat(call_id.split('_')[1]),
                messages, mock_response, temperature, max_tokens, tools
            )

        except Exception as e:
            logger.error(f"流式聊天失败 - ID: {call_id}, 错误: {str(e)}")
            raise

    async def _astream_chat(self,
                            call_id: str,
                            messages: List[Dict[str, Any]],
                            temperature: Optional[float],
                            max_tokens: Optional[int],
                            tools: Optional[List[Dict[str, Any]]],
                            tool_choice: Optional[Union[str, Dict[str, Any]]],
                            **kwargs) -> AsyncGenerator[StreamResponse, None]:
        """异步流式聊天"""
        try:
            full_content = ""
            stream = self.provider.astream(
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )

            async for chunk in stream:
                # 收集完整内容
                if chunk.choices and chunk.choices[0]["delta"]:
                    content = chunk.choices[0]["delta"].get("content", "")
                    full_content += content

                yield chunk

            # 流结束后记录调用
            end_time = datetime.now()

            # 创建模拟响应用于记录
            mock_response = ChatResponse(
                id=chunk.id if hasattr(chunk, 'id') else call_id,
                created=int(datetime.now().timestamp()),
                model=self.model_name,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": full_content
                    },
                    "finish_reason": "stop"
                }],
                usage={
                    "prompt_tokens": 0,
                    "completion_tokens": len(full_content) // 4,
                    "total_tokens": 0
                }
            )

            self._record_call(
                call_id, datetime.fromisoformat(call_id.split('_')[1]),
                messages, mock_response, temperature, max_tokens, tools
            )

        except Exception as e:
            logger.error(f"异步流式聊天失败 - ID: {call_id}, 错误: {str(e)}")
            raise

    def _record_call(self,
                     call_id: str,
                     start_time: datetime,
                     messages: List[Dict[str, Any]],
                     response: ChatResponse,
                     temperature: Optional[float],
                     max_tokens: Optional[int],
                     tools: Optional[List[Dict[str, Any]]]):
        """记录调用信息"""
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        call_info = {
            "id": call_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "elapsed_seconds": elapsed,
            "model": self.model_name,
            "provider": self.provider_type,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "has_tools": bool(tools),
            "tool_count": len(tools) if tools else 0,
            "messages_count": len(messages),
            "response_content_length": len(response.get_content() or ""),
            "usage": response.usage.copy() if response.usage else None,
            "success": True,
            "error": None
        }

        # 添加到历史记录
        self.call_history.append(call_info)

        # 保持历史记录大小
        if len(self.call_history) > self.max_history_size:
            self.call_history = self.call_history[-self.max_history_size:]

        logger.info(f"LLM调用记录 - ID: {call_id}, "
                    f"耗时: {elapsed:.2f}s, "
                    f"Tokens: {response.usage.get('total_tokens', 0) if response.usage else 0}")

    def _record_error(self,
                      call_id: str,
                      start_time: datetime,
                      messages: List[Dict[str, Any]],
                      error_msg: str):
        """记录错误信息"""
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        error_info = {
            "id": call_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "elapsed_seconds": elapsed,
            "model": self.model_name,
            "provider": self.provider_type,
            "messages_count": len(messages),
            "success": False,
            "error": error_msg
        }

        # 添加到历史记录
        self.call_history.append(error_info)

        if len(self.call_history) > self.max_history_size:
            self.call_history = self.call_history[-self.max_history_size:]

    def get_call_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取调用历史"""
        return self.call_history[-limit:]

    def clear_history(self):
        """清空历史记录"""
        self.call_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        provider_stats = self.provider.get_stats()

        # 计算总体统计
        successful_calls = [c for c in self.call_history if c.get("success")]
        failed_calls = [c for c in self.call_history if not c.get("success")]

        total_tokens = sum(c.get("usage", {}).get("total_tokens", 0)
                           for c in successful_calls)

        avg_latency = 0
        if successful_calls:
            avg_latency = sum(c.get("elapsed_seconds", 0)
                              for c in successful_calls) / len(successful_calls)

        return {
            "provider": self.provider_type,
            "model": self.model_name,
            "total_calls": len(self.call_history),
            "successful_calls": len(successful_calls),
            "failed_calls": len(failed_calls),
            "success_rate": len(successful_calls) / len(self.call_history) if self.call_history else 0,
            "total_tokens": total_tokens,
            "total_cost": provider_stats.get("total_cost", 0),
            "avg_latency_seconds": avg_latency,
            "call_history_size": len(self.call_history),
            "provider_stats": provider_stats
        }

    def count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        return self.token_counter.count_tokens(text, self.model_name)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """估算成本"""
        return self.provider.calculate_cost(prompt_tokens + completion_tokens)

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return self.provider.get_model_info()

    def get_max_context_length(self) -> int:
        """获取最大上下文长度"""
        return self.provider._get_max_context_length()

    def validate_messages_length(self, messages: List[Dict[str, Any]],
                                 max_completion_tokens: int = 1000) -> bool:
        """验证消息长度是否超过限制"""
        # 估算消息token数
        total_tokens = 0
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
            elif hasattr(msg, "content"):
                content = msg.content
            else:
                content = str(msg)

            total_tokens += self.count_tokens(content)

        max_context = self.get_max_context_length()
        return total_tokens + max_completion_tokens <= max_context

    @lru_cache(maxsize=100)
    def generate_with_prompt(self,
                             prompt_template: str,
                             variables: Dict[str, Any],
                             **kwargs) -> ChatResponse:
        """
        使用Prompt模板生成

        Args:
            prompt_template: Prompt模板字符串
            variables: 模板变量
            **kwargs: 其他参数

        Returns:
            ChatResponse对象
        """
        # 渲染Prompt
        prompt = prompt_template.format(**variables)

        # 创建消息
        messages = [{"role": "user", "content": prompt}]

        # 调用聊天接口
        return self.chat(messages, **kwargs)

    async def agenerate_with_prompt(self,
                                    prompt_template: str,
                                    variables: Dict[str, Any],
                                    **kwargs) -> ChatResponse:
        """异步使用Prompt模板生成"""
        # 渲染Prompt
        prompt = prompt_template.format(**variables)

        # 创建消息
        messages = [{"role": "user", "content": prompt}]

        # 异步调用聊天接口
        return await self.achat(messages, **kwargs)
