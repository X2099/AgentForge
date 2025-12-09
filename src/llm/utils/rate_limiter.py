# -*- coding: utf-8 -*-
"""
@File    : rate_limiter.py
@Time    : 2025/12/9 10:46
@Desc    : 
"""
import asyncio
import time
from collections import deque
import threading
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器"""

    def __init__(self,
                 requests_per_minute: int = 60,
                 tokens_per_minute: int = 60000):
        """
        初始化速率限制器

        Args:
            requests_per_minute: 每分钟请求数限制
            tokens_per_minute: 每分钟token数限制
        """
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute

        # 请求时间记录
        self.request_times = deque()
        self.request_lock = threading.Lock()

        # Token使用记录
        self.token_usage = deque()
        self.token_lock = threading.Lock()

        # 时间窗口（秒）
        self.window_seconds = 60

        logger.info(f"速率限制器初始化 - 请求限制: {requests_per_minute}/分钟, "
                    f"Token限制: {tokens_per_minute}/分钟")

    def wait_if_needed(self, estimated_tokens: int = 0):
        """
        如果需要等待，则阻塞当前线程

        Args:
            estimated_tokens: 预估的token使用量
        """
        while True:
            # 检查请求限制
            with self.request_lock:
                self._clean_old_entries(self.request_times)

                if len(self.request_times) >= self.requests_per_minute:
                    # 计算需要等待的时间
                    oldest_time = self.request_times[0]
                    wait_time = self.window_seconds - (time.time() - oldest_time)

                    if wait_time > 0:
                        time.sleep(wait_time + 0.1)  # 加一点缓冲
                        continue

            # 检查token限制
            with self.token_lock:
                self._clean_old_entries(self.token_usage, is_token=True)

                current_tokens = sum(amount for _, amount in self.token_usage)
                if current_tokens + estimated_tokens > self.tokens_per_minute:
                    # 计算需要等待的时间
                    if self.token_usage:
                        oldest_time, _ = self.token_usage[0]
                        wait_time = self.window_seconds - (time.time() - oldest_time)

                        if wait_time > 0:
                            time.sleep(wait_time + 0.1)
                            continue

            # 通过检查
            break

        # 记录本次请求
        current_time = time.time()
        with self.request_lock:
            self.request_times.append(current_time)

        if estimated_tokens > 0:
            with self.token_lock:
                self.token_usage.append((current_time, estimated_tokens))

    async def await_if_needed(self, estimated_tokens: int = 0):
        """
        异步等待（如果需要）

        Args:
            estimated_tokens: 预估的token使用量
        """
        while True:
            # 检查请求限制
            with self.request_lock:
                self._clean_old_entries(self.request_times)

                if len(self.request_times) >= self.requests_per_minute:
                    oldest_time = self.request_times[0]
                    wait_time = self.window_seconds - (time.time() - oldest_time)

                    if wait_time > 0:
                        await asyncio.sleep(wait_time + 0.1)
                        continue

            # 检查token限制
            with self.token_lock:
                self._clean_old_entries(self.token_usage, is_token=True)

                current_tokens = sum(amount for _, amount in self.token_usage)
                if current_tokens + estimated_tokens > self.tokens_per_minute:
                    if self.token_usage:
                        oldest_time, _ = self.token_usage[0]
                        wait_time = self.window_seconds - (time.time() - oldest_time)

                        if wait_time > 0:
                            await asyncio.sleep(wait_time + 0.1)
                            continue

            # 通过检查
            break

        # 记录本次请求
        current_time = time.time()
        with self.request_lock:
            self.request_times.append(current_time)

        if estimated_tokens > 0:
            with self.token_lock:
                self.token_usage.append((current_time, estimated_tokens))

    def _clean_old_entries(self, entries: deque, is_token: bool = False):
        """清理过期条目"""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        if is_token:
            # 清理token记录
            while entries and entries[0][0] < cutoff_time:
                entries.popleft()
        else:
            # 清理时间记录
            while entries and entries[0] < cutoff_time:
                entries.popleft()

    def get_current_usage(self) -> dict:
        """获取当前使用情况"""
        current_time = time.time()

        with self.request_lock:
            self._clean_old_entries(self.request_times)
            request_count = len(self.request_times)

        with self.token_lock:
            self._clean_old_entries(self.token_usage, is_token=True)
            token_usage = sum(amount for _, amount in self.token_usage)

        return {
            "requests_per_minute": {
                "current": request_count,
                "limit": self.requests_per_minute,
                "remaining": max(0, self.requests_per_minute - request_count)
            },
            "tokens_per_minute": {
                "current": token_usage,
                "limit": self.tokens_per_minute,
                "remaining": max(0, self.tokens_per_minute - token_usage)
            },
            "window_seconds": self.window_seconds,
            "timestamp": current_time
        }
