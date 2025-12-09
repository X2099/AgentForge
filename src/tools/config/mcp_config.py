# -*- coding: utf-8 -*-
"""
@File    : mcp_config.py
@Time    : 2025/12/9 11:58
@Desc    : 
"""
import os
import yaml
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

from ..schemas.protocol import MCPConfig, MCPProtocolVersion
from ..transports import HTTPTransportConfig

# 加载环境变量
load_dotenv()


class MCPToolConfig:
    """MCP工具配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or "./configs/mcp_tools.yaml"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config_path = Path(self.config_path)

        if not config_path.exists():
            return self._get_default_config()

        try:
            if config_path.suffix in ['.yaml', '.yml']:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            elif config_path.suffix == '.json':
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")

            # 解析环境变量
            config = self._parse_env_vars(config)

            return config

        except Exception as e:
            print(f"加载配置文件失败: {str(e)}，使用默认配置")
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
            "mcp": {
                "protocol_version": "2024-11-05",
                "server_info": {
                    "name": "mcp-tools-python",
                    "version": "0.1.0"
                }
            },
            "server": {
                "transport": "stdio",
                "stdio": {},
                "http": {
                    "host": "localhost",
                    "port": 8000,
                    "path": "/mcp",
                    "cors_enabled": True
                }
            },
            "tools": {
                "enabled": ["calculator", "web_search", "knowledge_base_search"],
                "calculator": {},
                "web_search": {
                    "api_key": "${GOOGLE_SEARCH_API_KEY}",
                    "fallback_to_mock": True
                },
                "knowledge_base_search": {
                    "kb_config_dir": "./configs/knowledge_bases"
                }
            },
            "logging": {
                "level": "INFO",
                "file": "./logs/mcp_tools.log"
            }
        }

    def get_mcp_config(self) -> MCPConfig:
        """获取MCP配置"""
        mcp_config = self.config.get("mcp", {})

        return MCPConfig(
            protocol_version=MCPProtocolVersion(mcp_config.get("protocol_version", "2024-11-05")),
            server_info=mcp_config.get("server_info"),
            capabilities=mcp_config.get("capabilities", {})
        )

    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        server_config = self.config.get("server", {})
        transport = server_config.get("transport", "stdio")

        config = {
            "transport_type": transport,
            "transport_config": {}
        }

        if transport == "http":
            http_config = server_config.get("http", {})
            config["transport_config"] = HTTPTransportConfig(**http_config).__dict__

        return config

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """获取工具配置"""
        tools_config = self.config.get("tools", {})
        return tools_config.get(tool_name, {})

    def get_enabled_tools(self) -> List[str]:
        """获取启用的工具列表"""
        tools_config = self.config.get("tools", {})
        return tools_config.get("enabled", [])

    def save_config(self, config: Optional[Dict[str, Any]] = None):
        """保存配置"""
        config_to_save = config or self.config
        config_path = Path(self.config_path)

        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if config_path.suffix in ['.yaml', '.yml']:
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_to_save, f, default_flow_style=False, allow_unicode=True)
            elif config_path.suffix == '.json':
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_to_save, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
            return False
