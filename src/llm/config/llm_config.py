# -*- coding: utf-8 -*-
"""
@File    : llm_config.py
@Time    : 2025/12/9 10:47
@Desc    : 
"""
import os
import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class LLMConfig:
    """LLM配置管理"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or "./configs/llm_config.yaml"
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
                "openai": {
                    "api_key": "${OPENAI_API_KEY}",
                    "base_url": None,
                    "default_model": "gpt-3.5-turbo",
                    "timeout": 30,
                    "max_retries": 3
                },
                "anthropic": {
                    "api_key": "${ANTHROPIC_API_KEY}",
                    "base_url": None,
                    "default_model": "claude-3-sonnet",
                    "timeout": 30,
                    "max_retries": 3
                },
                "local": {
                    "default_model": "Qwen/Qwen2.5-7B-Instruct",
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

    def create_client(self,
                      provider: Optional[str] = None,
                      model: Optional[str] = None,
                      **kwargs) -> "LLMClient":
        """
        创建LLM客户端

        Args:
            provider: 提供商类型
            model: 模型名称
            **kwargs: 其他参数

        Returns:
            LLMClient实例
        """
        from ..llm_client import LLMClient

        # 使用配置或参数
        provider = provider or self.get_default_provider()
        model = model or self.get_default_model(provider)

        # 获取提供商配置
        provider_config = self.get_provider_config(provider)

        # 合并配置
        client_config = {**provider_config, **kwargs, "provider_type": provider, "model_name": model}

        # 添加提供商类型和模型名称

        # 添加速率限制
        rate_limit_config = self.get_rate_limiting_config()
        if rate_limit_config:
            client_config["rate_limit"] = rate_limit_config

        # 从环境变量读取API密钥
        if "api_key" in client_config and client_config["api_key"]:
            if client_config["api_key"].startswith("${") and client_config["api_key"].endswith("}"):
                env_var = client_config["api_key"][2:-1]
                client_config["api_key"] = os.getenv(env_var)

        # 创建客户端
        return LLMClient(**client_config)

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
