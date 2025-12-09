# -*- coding: utf-8 -*-
"""
@File    : mcp_registry.py
@Time    : 2025/12/9 11:57
@Desc    : 
"""
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import logging

from .mcp_server import MCPServer
from .schemas.protocol import MCPConfig
from .transports import TransportType

logger = logging.getLogger(__name__)


@dataclass
class RegisteredTool:
    """已注册的工具"""
    name: str
    description: str
    handler: Callable[[Dict[str, Any]], Any]
    input_schema: Dict[str, Any]
    category: str = "general"
    enabled: bool = True


class MCPToolRegistry:
    """MCP工具注册中心"""

    def __init__(self, config: Optional[MCPConfig] = None):
        """
        初始化工具注册中心

        Args:
            config: MCP配置
        """
        self.config = config or MCPConfig()
        self.server: Optional[MCPServer] = None

        # 工具存储
        self.tools: Dict[str, RegisteredTool] = {}

        # 内置工具实例
        self.builtin_tools: Dict[str, Any] = {}

        logger.info("MCP工具注册中心初始化")

    def register_tool(self,
                      name: str,
                      description: str,
                      handler: Callable[[Dict[str, Any]], Any],
                      input_schema: Dict[str, Any],
                      category: str = "general"):
        """
        注册工具

        Args:
            name: 工具名称
            description: 工具描述
            handler: 工具处理函数
            input_schema: 输入模式
            category: 工具类别
        """
        tool = RegisteredTool(
            name=name,
            description=description,
            handler=handler,
            input_schema=input_schema,
            category=category
        )

        self.tools[name] = tool
        logger.info(f"注册工具: {name} ({category})")

    def register_builtin_tool(self, tool_instance: Any):
        """注册内置工具实例"""
        if hasattr(tool_instance, 'get_tool_schema'):
            schema = tool_instance.get_tool_schema()

            if hasattr(tool_instance, 'execute'):
                handler = tool_instance.execute
            elif hasattr(tool_instance, '__call__'):
                handler = tool_instance
            else:
                raise ValueError(f"工具 {tool_instance} 没有执行方法")

            self.register_tool(
                name=schema["name"],
                description=schema["description"],
                handler=handler,
                input_schema=schema["inputSchema"],
                category="builtin"
            )

            self.builtin_tools[schema["name"]] = tool_instance
            logger.info(f"注册内置工具: {schema['name']}")
        else:
            logger.warning(f"工具 {tool_instance} 没有get_tool_schema方法")

    def unregister_tool(self, name: str):
        """取消注册工具"""
        if name in self.tools:
            del self.tools[name]

            if name in self.builtin_tools:
                del self.builtin_tools[name]

            logger.info(f"取消注册工具: {name}")
        else:
            logger.warning(f"尝试取消注册不存在的工具: {name}")

    def get_tool(self, name: str) -> Optional[RegisteredTool]:
        """获取工具"""
        return self.tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[RegisteredTool]:
        """列出工具"""
        if category:
            return [tool for tool in self.tools.values() if tool.category == category]
        return list(self.tools.values())

    def get_tool_names(self) -> List[str]:
        """获取工具名称列表"""
        return list(self.tools.keys())

    async def start_server(self,
                           transport_type: TransportType = TransportType.STDIO,
                           transport_config: Optional[Dict[str, Any]] = None):
        """启动MCP服务器"""
        if self.server:
            logger.warning("服务器已在运行")
            return

        # 创建服务器
        self.server = MCPServer(
            config=self.config,
            transport_type=transport_type
        )

        # 注册所有工具
        for tool in self.tools.values():
            if tool.enabled:
                self.server.register_tool(
                    name=tool.name,
                    description=tool.description,
                    handler=tool.handler,
                    input_schema=tool.input_schema
                )

        logger.info(f"启动MCP服务器，共注册 {len(self.tools)} 个工具")

        # 启动服务器
        await self.server.start(transport_config)

    async def stop_server(self):
        """停止MCP服务器"""
        if self.server:
            await self.server.stop()
            self.server = None
            logger.info("MCP服务器已停止")

    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        if not self.server:
            return {"status": "stopped"}

        return {
            "status": "running",
            "tool_count": self.server.get_tool_count(),
            "tool_names": self.server.get_tool_names(),
            "transport_type": self.server.transport_type.value
        }

    @asynccontextmanager
    async def run_server(self,
                         transport_type: TransportType = TransportType.STDIO,
                         transport_config: Optional[Dict[str, Any]] = None):
        """运行服务器（上下文管理器）"""
        try:
            await self.start_server(transport_type, transport_config)
            yield self
        finally:
            await self.stop_server()
