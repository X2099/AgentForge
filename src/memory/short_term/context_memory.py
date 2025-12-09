# -*- coding: utf-8 -*-
"""
@File    : context_memory.py
@Time    : 2025/12/9 12:24
@Desc    : 
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ...llm.utils.token_counter import TokenCounter


@dataclass
class ContextWindowConfig:
    """上下文窗口配置"""
    max_tokens: int = 4000
    max_messages: int = 20
    preserve_system_prompt: bool = True
    compression_strategy: str = "summary"  # summary, sliding, priority


class ContextMemoryManager:
    """上下文记忆管理器"""

    def __init__(self,
                 config: Optional[ContextWindowConfig] = None,
                 llm_client=None):
        self.config = config or ContextWindowConfig()
        self.llm_client = llm_client
        self.token_counter = TokenCounter()

        # 消息缓存
        self.messages: List[Dict[str, Any]] = []
        self.system_prompt: Optional[str] = None

    def add_message(self,
                    role: str,
                    content: str,
                    metadata: Optional[Dict[str, Any]] = None):
        """添加消息到上下文"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        if role == "system":
            self.system_prompt = content
            if self.config.preserve_system_prompt:
                # 系统提示词单独处理
                return

        self.messages.append(message)
        self._manage_window()

    def _manage_window(self):
        """管理上下文窗口"""
        if self._should_compress():
            self._compress_context()

    def _should_compress(self) -> bool:
        """检查是否需要压缩"""
        if len(self.messages) > self.config.max_messages:
            return True

        total_tokens = self._count_tokens()
        return total_tokens > self.config.max_tokens

    def _count_tokens(self) -> int:
        """计算总token数"""
        total = 0
        for msg in self.messages:
            total += self.token_counter.count_tokens(msg["content"], "gpt-3.5-turbo")
        return total

    def _compress_context(self):
        """压缩上下文"""
        if self.config.compression_strategy == "summary":
            self._compress_by_summary()
        elif self.config.compression_strategy == "sliding":
            self._compress_by_sliding_window()
        elif self.config.compression_strategy == "priority":
            self._compress_by_priority()

    def _compress_by_sliding_window(self):
        """滑动窗口压缩"""
        # 保留最新的消息
        while len(self.messages) > self.config.max_messages:
            self.messages.pop(0)

        # 确保token不超过限制
        while self._count_tokens() > self.config.max_tokens and len(self.messages) > 1:
            self.messages.pop(0)

    def _compress_by_summary(self):
        """摘要压缩"""
        if not self.llm_client or len(self.messages) < 3:
            # 如果没有LLM客户端或消息太少，使用滑动窗口
            self._compress_by_sliding_window()
            return

        # 选择要摘要的消息（通常是旧消息）
        to_summarize = self.messages[:len(self.messages) // 2]
        keep_messages = self.messages[len(self.messages) // 2:]

        # 生成摘要
        summary = self._generate_summary(to_summarize)

        # 替换为摘要消息
        self.messages = [
            {"role": "system", "content": f"之前的对话摘要：{summary}"},
            *keep_messages
        ]

    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成对话摘要"""
        try:
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in messages
            ])

            prompt = f"""
            请总结以下对话的主要内容，保留关键信息和决策：

            {conversation_text}

            摘要：
            """

            response = self.llm_client.chat([{"role": "user", "content": prompt}])
            return response.get_content() or "无法生成摘要"
        except:
            return "对话摘要"

    def _compress_by_priority(self):
        """优先级压缩"""
        # 为消息分配优先级
        prioritized = []
        for msg in self.messages:
            priority = self._calculate_priority(msg)
            prioritized.append((priority, msg))

        # 按优先级排序
        prioritized.sort(key=lambda x: x[0], reverse=True)

        # 保留高优先级的消息
        kept_messages = []
        total_tokens = 0

        for priority, msg in prioritized:
            msg_tokens = self.token_counter.count_tokens(msg["content"], "gpt-3.5-turbo")
            if total_tokens + msg_tokens <= self.config.max_tokens:
                kept_messages.append(msg)
                total_tokens += msg_tokens

        self.messages = kept_messages

    def _calculate_priority(self, message: Dict[str, Any]) -> float:
        """计算消息优先级"""
        priority = 1.0

        # 最近的消息优先级更高
        timestamp = datetime.fromisoformat(message["timestamp"])
        age_hours = (datetime.now() - timestamp).total_seconds() / 3600
        priority *= max(0.1, 1.0 - age_hours / 24)

        # 系统消息优先级高
        if message["role"] == "system":
            priority *= 2.0

        # 用户消息优先级较高
        if message["role"] == "user":
            priority *= 1.5

        # 工具调用结果优先级较高
        if message.get("metadata", {}).get("is_tool_call"):
            priority *= 1.3

        return priority

    def get_context(self,
                    include_system: bool = True,
                    max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取当前上下文"""
        context = []

        if include_system and self.system_prompt:
            context.append({"role": "system", "content": self.system_prompt})

        # 添加消息，确保不超过token限制
        total_tokens = 0
        max_tokens = max_tokens or self.config.max_tokens

        for msg in reversed(self.messages):
            msg_tokens = self.token_counter.count_tokens(msg["content"], "gpt-3.5-turbo")

            if total_tokens + msg_tokens <= max_tokens:
                context.insert(1 if self.system_prompt else 0, {
                    "role": msg["role"],
                    "content": msg["content"]
                })
                total_tokens += msg_tokens
            else:
                break

        return context

    def clear(self):
        """清空上下文"""
        self.messages.clear()
        self.system_prompt = None
