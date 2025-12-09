# -*- coding: utf-8 -*-
"""
@File    : provider_factory.py
@Time    : 2025/12/9 10:36
@Desc    : 
"""
from typing import Dict, List, Any
import logging
from enum import Enum

from .base_provider import BaseProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .local_provider import LocalProvider

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """提供商类型枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    AZURE_OPENAI = "azure_openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    GLM = "glm"


class ProviderFactory:
    """提供商工厂"""

    # 提供商映射
    PROVIDER_MAP = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.LOCAL: LocalProvider,
        # 其他提供商可以在这里添加
    }

    @staticmethod
    def create_provider(provider_type: str,
                        config: Dict[str, Any]) -> BaseProvider:
        """
        创建LLM提供商

        Args:
            provider_type: 提供商类型
            config: 配置参数

        Returns:
            LLM提供商实例
        """
        # 标准化提供商类型
        provider_type = provider_type.lower().strip()

        # 映射提供商类型
        provider_enum = ProviderFactory._map_provider_type(provider_type)

        if provider_enum not in ProviderFactory.PROVIDER_MAP:
            raise ValueError(f"不支持的提供商类型: {provider_type}")

        provider_class = ProviderFactory.PROVIDER_MAP[provider_enum]

        try:
            # 创建提供商实例
            instance = provider_class(**config)
            logger.info(f"创建{provider_enum.value}提供商成功 - 模型: {instance.model_name}")
            return instance

        except Exception as e:
            logger.error(f"创建{provider_enum.value}提供商失败: {str(e)}")
            raise

    @staticmethod
    def _map_provider_type(provider_type: str) -> ProviderType:
        """映射提供商类型"""
        provider_type_lower = provider_type.lower()

        mapping = {
            # OpenAI系列
            "openai": ProviderType.OPENAI,
            "gpt": ProviderType.OPENAI,
            "azure": ProviderType.AZURE_OPENAI,
            "azure_openai": ProviderType.AZURE_OPENAI,

            # Anthropic系列
            "anthropic": ProviderType.ANTHROPIC,
            "claude": ProviderType.ANTHROPIC,

            # 本地模型
            "local": ProviderType.LOCAL,
            "huggingface": ProviderType.LOCAL,
            "transformers": ProviderType.LOCAL,

            # 国产模型
            "deepseek": ProviderType.DEEPSEEK,
            "qwen": ProviderType.QWEN,
            "glm": ProviderType.GLM,
            "chatglm": ProviderType.GLM,
        }

        for key, value in mapping.items():
            if key in provider_type_lower:
                return value

        # 默认返回OpenAI
        return ProviderType.OPENAI

    @staticmethod
    def get_available_providers() -> Dict[str, List[str]]:
        """获取可用的提供商和模型"""
        return {
            "openai": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo",
            ],
            "anthropic": [
                "claude-3-5-sonnet",
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
                "claude-2.1",
            ],
            "local": [
                "Qwen/Qwen2.5-7B-Instruct",
                "THUDM/chatglm3-6b",
                "baichuan-inc/Baichuan2-7B-Chat",
                "internlm/internlm2-chat-7b",
            ]
        }

    @staticmethod
    def get_provider_info(provider_type: str) -> Dict[str, Any]:
        """获取提供商信息"""
        provider_enum = ProviderFactory._map_provider_type(provider_type)

        info = {
            "type": provider_enum.value,
            "display_name": provider_enum.value.title(),
            "supports_streaming": True,
            "supports_tools": provider_enum in [ProviderType.OPENAI, ProviderType.ANTHROPIC],
            "is_local": provider_enum == ProviderType.LOCAL,
        }

        # 添加特定信息
        if provider_enum == ProviderType.OPENAI:
            info.update({
                "website": "https://openai.com",
                "documentation": "https://platform.openai.com/docs",
            })
        elif provider_enum == ProviderType.ANTHROPIC:
            info.update({
                "website": "https://anthropic.com",
                "documentation": "https://docs.anthropic.com",
            })
        elif provider_enum == ProviderType.LOCAL:
            info.update({
                "website": "https://huggingface.co",
                "documentation": "https://huggingface.co/docs",
                "requires_gpu": True,
            })

        return info
