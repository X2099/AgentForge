# -*- coding: utf-8 -*-
"""
@File    : llm_config.py
@Time    : 2025/12/9 10:47
@Desc    : LLM配置类
"""
import os
import json
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import logging
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class SystemConfig:
    """LLM配置管理"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or "./configs/system_config.yaml"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config_path = Path(self.config_path)

        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}, 使用默认配置")
            return self._get_default_config()

        try:
            if config_path.suffix == ".yaml" or config_path.suffix == ".yml":
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            elif config_path.suffix == ".json":
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                logger.error(f"不支持的配置文件格式: {config_path.suffix}")
                return self._get_default_config()

            # 解析环境变量
            config = self._parse_env_vars(config)

            logger.info(f"加载配置文件成功: {config_path}")
            return config

        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return self._get_default_config()

    def _parse_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解析环境变量"""

        def replace_env_vars(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.getenv(env_var, value)
            return value

        def traverse_dict(d):
            if isinstance(d, dict):
                return {k: traverse_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [traverse_dict(v) for v in d]
            else:
                return replace_env_vars(d)

        return traverse_dict(config)

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "default_provider": "openai",
            "default_model": "gpt-3.5-turbo",
            "providers": {
                "deepseek": {
                    "api_key": "${DEEPSEEK_API_KEY}",
                    "base_url": None,
                    "model": "deepseek-chat",
                    "timeout": 30,
                    "max_retries": 3
                },
                "openai": {
                    "api_key": "${OPENAI_API_KEY}",
                    "base_url": None,
                    "model": "gpt-5",
                    "timeout": 30,
                    "max_retries": 3
                },
                "local": {
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "device": "auto",
                    "load_in_8bit": False,
                    "load_in_4bit": False
                }
            },
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 60,
                "tokens_per_minute": 60000
            },
            "caching": {
                "enabled": True,
                "ttl_seconds": 300,
                "max_size": 100
            },
            "logging": {
                "level": "INFO",
                "log_file": "./logs/llm.log",
                "max_file_size_mb": 10,
                "backup_count": 5
            }
        }

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """获取提供商配置"""
        providers = self.config.get("providers", {})
        return providers.get(provider, {})

    def get_default_provider(self) -> str:
        """获取默认提供商"""
        return self.config.get("default_provider", "openai")

    def get_default_model(self, provider: Optional[str] = None) -> str:
        """获取默认模型"""
        if provider:
            provider_config = self.get_provider_config(provider)
            return provider_config.get("default_model", "gpt-3.5-turbo")
        return self.config.get("default_model", "gpt-3.5-turbo")

    def get_rate_limiting_config(self) -> Dict[str, Any]:
        """获取速率限制配置"""
        rate_limiting = self.config.get("rate_limiting", {})
        if rate_limiting.get("enabled", True):
            return {
                "requests_per_minute": rate_limiting.get("requests_per_minute", 60),
                "tokens_per_minute": rate_limiting.get("tokens_per_minute", 60000)
            }
        return {}

    def _find_provider_by_model(self, model_name: str) -> Optional[str]:
        """根据模型名称找到对应的提供商"""
        providers = self.config.get("providers", {})
        for provider_name, provider_config in providers.items():
            # 检查model_name和default_model两个字段
            configured_model = provider_config.get("model_name") or provider_config.get("default_model")
            if configured_model == model_name:
                return provider_name
        return None

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
            **kwargs,
    ) -> BaseChatModel:
        """直接创建LangChain ChatModel实例"""
        common_params = {
            "model": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "max_retries": max_retries,
            **kwargs,
        }

        if provider_type.lower() == "openai":
            if api_key:
                common_params["api_key"] = api_key
            if base_url:
                common_params["base_url"] = base_url
            return ChatOpenAI(**common_params)
        if provider_type.lower() == "deepseek":
            if api_key:
                common_params["api_key"] = api_key
            return ChatDeepSeek(**common_params)
        if provider_type.lower() == "anthropic":
            if api_key:
                common_params["api_key"] = api_key
            return ChatAnthropic(**common_params)

        raise ValueError(f"不支持的提供商类型: {provider_type}")

    def create_client(self,
                      provider: Optional[str] = None,
                      model: Optional[str] = None,
                      **kwargs) -> BaseChatModel:
        """
        创建LLM模型实例（直接使用LangChain ChatModel）

        Args:
            provider: 提供商类型 (openai, anthropic)
            model: 模型名称
            **kwargs: 其他参数

        Returns:
            BaseChatModel实例
        """

        # 如果提供了model但没有provider，尝试根据model找到对应的provider
        if model and not provider:
            provider = self._find_provider_by_model(model)

        # 使用配置或参数
        provider = provider or self.get_default_provider()
        model = model or self.get_default_model(provider)

        # 获取提供商配置
        provider_config = self.get_provider_config(provider)

        # 合并配置
        client_config = {
            "provider_type": provider,
            "model_name": model,
            **provider_config,
            **kwargs
        }

        # 从环境变量读取API密钥
        if "api_key" in client_config and client_config["api_key"]:
            if isinstance(client_config["api_key"], str) and client_config["api_key"].startswith("${") and \
                    client_config["api_key"].endswith("}"):
                env_var = client_config["api_key"][2:-1]
                client_config["api_key"] = os.getenv(env_var, client_config["api_key"])

        return self._create_chat_model(**client_config)

    def save_config(self, config: Optional[Dict[str, Any]] = None):
        """保存配置"""
        config_to_save = config or self.config
        config_path = Path(self.config_path)

        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if config_path.suffix == ".yaml" or config_path.suffix == ".yml":
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_to_save, f, default_flow_style=False, allow_unicode=True)
            elif config_path.suffix == ".json":
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_to_save, f, ensure_ascii=False, indent=2)
            else:
                logger.error(f"不支持的配置文件格式: {config_path.suffix}")
                return False

            logger.info(f"配置文件保存成功: {config_path}")
            return True

        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False

    def get_vector_stores_config(self) -> List[Dict[str, Any]]:
        """获取向量数据库配置"""
        vector_stores = self.config.get("vector_stores", [])
        # 只返回启用的向量数据库
        return [store for store in vector_stores if store.get("enabled", True)]

    def get_embedders_config(self) -> List[Dict[str, Any]]:
        """获取嵌入器配置"""
        embedders = self.config.get("embedders", [])
        # 只返回启用的嵌入器
        return [embedder for embedder in embedders if embedder.get("enabled", True)]

    def get_embedder_models(self, embedder_type: str) -> List[Dict[str, Any]]:
        """获取特定嵌入器类型的模型列表"""
        embedders = self.get_embedders_config()
        for embedder in embedders:
            if embedder.get("type") == embedder_type:
                return embedder.get("models", [])
        return []
