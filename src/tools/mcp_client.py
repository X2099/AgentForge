# -*- coding: utf-8 -*-
"""
@File    : mcp_client.py
@Time    : 2025/12/9 11:53
@Desc    : 
"""
# src/tools/mcp_client.py
import asyncio
from typing import Dict, Any, List, Optional, Union
import logging
from contextlib import asynccontextmanager

from .schemas.protocol import Tool, ToolResult, TextContent
from .schemas.messages import (
    MCPMessageParser, MCPMessage,
    InitializeRequest, ListToolsRequest, CallToolRequest,
    SuccessResponse, ErrorResponse
)
from .transports import TransportFactory, TransportType

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP客户端"""

    def __init__(self,
                 transport_type: TransportType = TransportType.STDIO,
                 transport_config: Optional[Dict[str, Any]] = None):
        """
        初始化MCP客户端

        Args:
            transport_type: 传输类型
            transport_config: 传输配置
        """
        self.transport_type = transport_type
        self.transport_config = transport_config or {}
        self.transport = None

        # 客户端状态
        self.is_connected = False
        self.is_initialized = False

        # 工具缓存
        self.tools_cache: List[Tool] = []
        self.tools_cache_time = 0

        # 客户端能力
        self.client_capabilities = {
            "experimental": {},
            "tools": {}
        }

        logger.info(f"MCP客户端初始化 - 传输类型: {transport_type}")

    async def connect(self):
        """连接到服务器"""
        if self.is_connected:
            return

        try:
            # 创建传输
            self.transport = TransportFactory.create_client_transport(
                self.transport_type,
                self.transport_config
            )

            # 对于异步STDIO，需要特殊初始化
            if self.transport_type == TransportType.STDIO:
                await self.transport.setup()

            self.is_connected = True
            logger.info("MCP客户端连接成功")

        except Exception as e:
            logger.error(f"连接失败: {str(e)}")
            raise

    async def disconnect(self):
        """断开连接"""
        if self.transport and self.is_connected:
            await self.transport.close()
            self.is_connected = False
            logger.info("MCP客户端断开连接")

    async def initialize(self) -> bool:
        """初始化客户端"""
        if not self.is_connected:
            await self.connect()

        try:
            # 创建初始化请求
            request = InitializeRequest(
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": self.client_capabilities,
                    "clientInfo": {
                        "name": "mcp-client-python",
                        "version": "0.1.0"
                    }
                }
            )

            # 发送请求
            response = await self.transport.send_message(request)

            if isinstance(response, SuccessResponse):
                self.is_initialized = True
                logger.info("MCP客户端初始化成功")
                return True
            else:
                logger.error(f"初始化失败: {response.error if isinstance(response, ErrorResponse) else 'Unknown'}")
                return False

        except Exception as e:
            logger.error(f"初始化失败: {str(e)}")
            return False

    async def list_tools(self, force_refresh: bool = False) -> List[Tool]:
        """列出可用工具"""
        if not self.is_initialized:
            await self.initialize()

        # 检查缓存
        if not force_refresh and self.tools_cache:
            return self.tools_cache

        try:
            # 创建请求
            request = ListToolsRequest()

            # 发送请求
            response = await self.transport.send_message(request)

            if isinstance(response, SuccessResponse):
                if hasattr(response.result, 'tools'):
                    self.tools_cache = response.result.tools
                    self.tools_cache_time = asyncio.get_event_loop().time()

                    logger.info(f"获取到 {len(self.tools_cache)} 个工具")
                    return self.tools_cache
                else:
                    logger.error("响应格式错误，缺少tools字段")
                    return []
            else:
                logger.error(f"列出工具失败: {response.error if isinstance(response, ErrorResponse) else 'Unknown'}")
                return []

        except Exception as e:
            logger.error(f"列出工具失败: {str(e)}")
            return []

    async def call_tool(self,
                        tool_name: str,
                        arguments: Dict[str, Any]) -> Optional[ToolResult]:
        """调用工具"""
        if not self.is_initialized:
            await self.initialize()

        try:
            # 创建请求
            request = CallToolRequest(
                params={
                    "name": tool_name,
                    "arguments": arguments
                }
            )

            # 发送请求
            response = await self.transport.send_message(request)

            if isinstance(response, SuccessResponse):
                if hasattr(response.result, 'content'):
                    tool_result = ToolResult(
                        content=response.result.content,
                        isError=getattr(response.result, 'isError', False)
                    )

                    logger.info(f"工具调用成功: {tool_name}")
                    return tool_result
                else:
                    logger.error("响应格式错误，缺少content字段")
                    return None
            else:
                logger.error(
                    f"工具调用失败 {tool_name}: {response.error if isinstance(response, ErrorResponse) else 'Unknown'}")
                return None

        except Exception as e:
            logger.error(f"工具调用失败 {tool_name}: {str(e)}")
            return None

    async def call_tool_simple(self,
                               tool_name: str,
                               arguments: Dict[str, Any]) -> Optional[str]:
        """简化工具调用，返回文本结果"""
        result = await self.call_tool(tool_name, arguments)

        if result and result.content:
            # 提取文本内容
            texts = []
            for content in result.content:
                if hasattr(content, 'text'):
                    texts.append(content.text)

            return "\n".join(texts)

        return None

    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取特定工具信息"""
        tools = await self.list_tools()

        for tool in tools:
            if tool.name == tool_name:
                return tool

        return None

    def get_cached_tools(self) -> List[Tool]:
        """获取缓存的工具列表"""
        return self.tools_cache.copy()

    @asynccontextmanager
    async def connection(self):
        """连接上下文管理器"""
        try:
            await self.connect()
            await self.initialize()
            yield self
        finally:
            await self.disconnect()
