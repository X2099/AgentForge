# -*- coding: utf-8 -*-
"""
@File    : token_counter.py
@Time    : 2025/12/9 10:45
@Desc    : 
"""
import tiktoken
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class TokenCounter:
    """Token计数器"""

    # 模型到编码器的映射
    MODEL_ENCODINGS = {
        # OpenAI模型
        "gpt-4o": "cl100k_base",
        "gpt-4o-mini": "cl100k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-4": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",

        # Anthropic模型
        "claude-3": "claude",  # Anthropic有自己的tokenizer
        "claude-2": "claude",

        # 通用映射
        "text-davinci": "p50k_base",
        "code-davinci": "p50k_base",
        "text-curie": "r50k_base",
        "text-babbage": "r50k_base",
        "text-ada": "r50k_base",
    }

    def __init__(self):
        self.encoders: Dict[str, tiktoken.Encoding] = {}

    def count_tokens(self, text: str, model_name: str) -> int:
        """
        计算文本的token数量

        Args:
            text: 文本内容
            model_name: 模型名称

        Returns:
            token数量
        """
        try:
            # 获取编码器
            encoding = self._get_encoding(model_name)

            # 计算tokens
            tokens = encoding.encode(text)
            return len(tokens)

        except Exception as e:
            logger.warning(f"计算token失败，使用字符数估算: {str(e)}")
            # 失败时使用字符数估算（1 token ≈ 4字符）
            return len(text) // 4

    def _get_encoding(self, model_name: str) -> tiktoken.Encoding:
        """获取编码器"""
        # 查找匹配的编码
        encoding_name = None
        for model_pattern, encoding in self.MODEL_ENCODINGS.items():
            if model_pattern in model_name:
                encoding_name = encoding
                break

        # 默认使用cl100k_base（GPT-4/GPT-3.5-turbo的编码）
        if encoding_name is None:
            encoding_name = "cl100k_base"

        # 获取或创建编码器
        if encoding_name not in self.encoders:
            try:
                if encoding_name == "claude":
                    # Anthropic模型的近似处理
                    encoding_name = "cl100k_base"

                self.encoders[encoding_name] = tiktoken.get_encoding(encoding_name)
            except Exception as e:
                logger.error(f"获取编码器失败: {encoding_name}, 错误: {str(e)}")
                # 回退到cl100k_base
                self.encoders[encoding_name] = tiktoken.get_encoding("cl100k_base")

        return self.encoders[encoding_name]

    def truncate_by_tokens(self, text: str, model_name: str, max_tokens: int) -> str:
        """
        根据token数量截断文本

        Args:
            text: 文本内容
            model_name: 模型名称
            max_tokens: 最大token数

        Returns:
            截断后的文本
        """
        encoding = self._get_encoding(model_name)
        tokens = encoding.encode(text)

        if len(tokens) <= max_tokens:
            return text

        # 截断tokens并解码
        truncated_tokens = tokens[:max_tokens]
        truncated_text = encoding.decode(truncated_tokens)

        return truncated_text

    def estimate_tokens_for_messages(self,
                                     messages: list,
                                     model_name: str) -> int:
        """
        估算消息列表的token数量

        Args:
            messages: 消息列表
            model_name: 模型名称

        Returns:
            估算的token数量
        """
        total_tokens = 0

        for message in messages:
            if isinstance(message, dict):
                # 每条消息的格式开销（近似）
                total_tokens += 4

                # 内容token
                content = message.get("content", "")
                total_tokens += self.count_tokens(content, model_name)

                # 工具调用token（如果存在）
                if "tool_calls" in message:
                    tool_calls = message["tool_calls"]
                    for tool_call in tool_calls:
                        tool_json = str(tool_call)
                        total_tokens += self.count_tokens(tool_json, model_name)
            else:
                # 简单字符串消息
                total_tokens += self.count_tokens(str(message), model_name)

        return total_tokens
