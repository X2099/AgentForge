# -*- coding: utf-8 -*-
"""
@File    : __init__.py.py
@Time    : 2025/12/9 11:47
@Desc    : 
"""
from typing import Optional, Dict, Any, Union
from enum import Enum
import logging

from .stdio_transport import StdioTransport, AsyncStdioTransport
from .http_transport import HTTPTransportConfig, HTTPServerTransport, HTTPClientTransport

logger = logging.getLogger(__name__)


class TransportType(str, Enum):
    """传输类型"""
    STDIO = "stdio"
    HTTP = "http"


class TransportFactory:
    """传输工厂"""

    @staticmethod
    def create_server_transport(
            transport_type: Union[str, TransportType],
            config: Optional[Dict[str, Any]] = None
    ) -> Union[StdioTransport, HTTPServerTransport]:
        """
        创建服务器传输

        Args:
            transport_type: 传输类型
            config: 传输配置

        Returns:
            传输实例
        """
        if isinstance(transport_type, str):
            transport_type = TransportType(transport_type.lower())

        if transport_type == TransportType.STDIO:
            return StdioTransport(**config or {})

        elif transport_type == TransportType.HTTP:
            http_config = HTTPTransportConfig(**(config or {}))
            return HTTPServerTransport(http_config)

        else:
            raise ValueError(f"不支持的传输类型: {transport_type}")

    @staticmethod
    def create_client_transport(
            transport_type: Union[str, TransportType],
            config: Optional[Dict[str, Any]] = None
    ) -> Union[AsyncStdioTransport, HTTPClientTransport]:
        """
        创建客户端传输

        Args:
            transport_type: 传输类型
            config: 传输配置

        Returns:
            传输实例
        """
        if isinstance(transport_type, str):
            transport_type = TransportType(transport_type.lower())

        if transport_type == TransportType.STDIO:
            transport = AsyncStdioTransport(**(config or {}))
            # 异步STDIO需要特殊初始化
            return transport

        elif transport_type == TransportType.HTTP:
            if not config or "url" not in config:
                raise ValueError("HTTP客户端传输需要'url'配置")

            url = config.pop("url")
            timeout = config.pop("timeout", 30)
            headers = config.pop("headers", None)

            return HTTPClientTransport(
                url=url,
                timeout=timeout,
                headers=headers
            )

        else:
            raise ValueError(f"不支持的传输类型: {transport_type}")

    @staticmethod
    def get_transport_info(transport_type: Union[str, TransportType]) -> Dict[str, Any]:
        """获取传输信息"""
        if isinstance(transport_type, str):
            transport_type = TransportType(transport_type.lower())

        info = {
            "type": transport_type.value,
            "description": "",
            "server_supported": True,
            "client_supported": True,
            "bidirectional": False,
            "async_supported": False
        }

        if transport_type == TransportType.STDIO:
            info.update({
                "description": "标准输入输出传输",
                "bidirectional": True,
                "async_supported": True,
                "config_example": {
                    "stdin": "sys.stdin",
                    "stdout": "sys.stdout",
                    "stderr": "sys.stderr"
                }
            })

        elif transport_type == TransportType.HTTP:
            info.update({
                "description": "HTTP传输",
                "config_example": {
                    "server": {
                        "host": "localhost",
                        "port": 8000,
                        "path": "/mcp"
                    },
                    "client": {
                        "url": "http://localhost:8000/mcp"
                    }
                }
            })

        return info
