# -*- coding: utf-8 -*-
"""
@File    : http_transport.py
@Time    : 2025/12/9 11:49
@Desc    : HTTP传输
"""
import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import aiohttp
from aiohttp import web
import logging
from contextlib import asynccontextmanager

from ..schemas.messages import MCPMessageParser, MCPMessage, MCPErrorCodes
from ..schemas.protocol import MCPProtocolVersion

logger = logging.getLogger(__name__)


@dataclass
class HTTPTransportConfig:
    """HTTP传输配置"""
    host: str = "localhost"
    port: int = 8000
    path: str = "/mcp"
    timeout: int = 30
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    cors_enabled: bool = True
    cors_origins: List[str] = None


class HTTPServerTransport:
    """HTTP服务器传输"""

    def __init__(self, config: Optional[HTTPTransportConfig] = None):
        """
        初始化HTTP服务器传输

        Args:
            config: HTTP配置
        """
        self.config = config or HTTPTransportConfig()
        self.app = web.Application(
            client_max_size=self.config.max_request_size
        )
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

        # 消息处理回调
        self.message_handler: Optional[Callable[[MCPMessage], Any]] = None

        # 设置路由
        self._setup_routes()

        # 设置CORS（如果启用）
        if self.config.cors_enabled:
            self._setup_cors()

        logger.info(f"HTTP服务器传输初始化 - {self.config.host}:{self.config.port}")

    def _setup_routes(self):
        """设置路由"""
        # MCP端点
        self.app.router.add_post(self.config.path, self._handle_mcp_request)

        # 健康检查端点
        self.app.router.add_get("/health", self._handle_health_check)

        # 工具列表端点
        self.app.router.add_get("/tools", self._handle_list_tools)

    def _setup_cors(self):
        """设置CORS"""

        async def cors_middleware(app, handler):
            async def middleware_handler(request):
                # 处理预检请求
                if request.method == "OPTIONS":
                    response = web.Response()
                else:
                    response = await handler(request)

                # 添加CORS头
                origins = self.config.cors_origins or ["*"]
                response.headers['Access-Control-Allow-Origin'] = ', '.join(origins)
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                response.headers['Access-Control-Allow-Credentials'] = 'true'

                return response

            return middleware_handler

        self.app.middlewares.append(cors_middleware)

    async def _handle_mcp_request(self, request: web.Request) -> web.Response:
        """处理MCP请求"""
        try:
            # 读取请求体
            data = await request.json()

            # 解析消息
            message = MCPMessageParser.parse_message(data)

            # 处理消息
            if self.message_handler:
                response = await self.message_handler(message)

                if isinstance(response, MCPMessage):
                    # 返回MCP响应
                    return web.json_response(
                        response.dict(exclude_none=True),
                        status=200
                    )
                else:
                    # 返回直接结果
                    return web.json_response(response, status=200)
            else:
                # 没有消息处理器，返回错误
                error_response = MCPMessageParser.create_error_response(
                    request_id=message.id if hasattr(message, 'id') else None,
                    code=MCPErrorCodes.INTERNAL_ERROR,
                    message="No message handler configured"
                )
                return web.json_response(
                    error_response.dict(exclude_none=True),
                    status=500
                )

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {str(e)}")
            error_response = MCPMessageParser.create_error_response(
                request_id=None,
                code=MCPErrorCodes.PARSE_ERROR,
                message=f"Invalid JSON: {str(e)}"
            )
            return web.json_response(
                error_response.dict(exclude_none=True),
                status=400
            )
        except Exception as e:
            logger.error(f"处理请求失败: {str(e)}")
            error_response = MCPMessageParser.create_error_response(
                request_id=None,
                code=MCPErrorCodes.INTERNAL_ERROR,
                message=str(e)
            )
            return web.json_response(
                error_response.dict(exclude_none=True),
                status=500
            )

    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """处理健康检查"""
        return web.json_response({
            "status": "healthy",
            "service": "mcp-server",
            "protocol_version": MCPProtocolVersion.V1.value
        })

    async def _handle_list_tools(self, request: web.Request) -> web.Response:
        """处理工具列表请求"""
        # 这个端点主要用于调试和发现
        return web.json_response({
            "endpoint": f"{self.config.path}",
            "method": "POST",
            "protocol": "MCP JSON-RPC 2.0"
        })

    async def start(self):
        """启动HTTP服务器"""
        try:
            # 创建应用运行器
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            # 创建TCP站点
            self.site = web.TCPSite(
                self.runner,
                self.config.host,
                self.config.port
            )

            await self.site.start()

            logger.info(f"HTTP服务器启动 - http://{self.config.host}:{self.config.port}")
            logger.info(f"MCP端点: http://{self.config.host}:{self.config.port}{self.config.path}")

        except Exception as e:
            logger.error(f"启动HTTP服务器失败: {str(e)}")
            raise

    async def stop(self):
        """停止HTTP服务器"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()

            logger.info("HTTP服务器已停止")

        except Exception as e:
            logger.error(f"停止HTTP服务器失败: {str(e)}")

    def set_message_handler(self, handler: Callable[[MCPMessage], Any]):
        """设置消息处理器"""
        self.message_handler = handler

    @asynccontextmanager
    async def serve(self, message_handler: Optional[Callable[[MCPMessage], Any]] = None):
        """上下文管理器"""
        if message_handler:
            self.set_message_handler(message_handler)

        try:
            await self.start()
            yield self
        finally:
            await self.stop()


class HTTPClientTransport:
    """HTTP客户端传输"""

    def __init__(self,
                 url: str,
                 timeout: int = 30,
                 headers: Optional[Dict[str, str]] = None):
        """
        初始化HTTP客户端传输

        Args:
            url: 服务器URL
            timeout: 超时时间（秒）
            headers: 自定义请求头
        """
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"HTTP客户端传输初始化 - 目标: {self.url}")

    async def connect(self):
        """连接服务器"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.headers
            )

            # 测试连接
            try:
                async with self.session.get(f"{self.url}/health") as response:
                    if response.status == 200:
                        logger.info("HTTP服务器连接成功")
                    else:
                        logger.warning(f"HTTP服务器健康检查失败: {response.status}")
            except Exception as e:
                logger.warning(f"HTTP服务器健康检查失败: {str(e)}")

    async def send_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """发送消息"""
        if self.session is None:
            await self.connect()

        try:
            # 序列化消息
            serialized = MCPMessageParser.serialize_message(message)

            # 发送请求
            async with self.session.post(self.url, data=serialized) as response:
                if response.status == 200:
                    # 解析响应
                    data = await response.json()
                    response_message = MCPMessageParser.parse_message(data)
                    logger.debug(f"收到响应: {response_message}")
                    return response_message
                else:
                    error_text = await response.text()
                    logger.error(f"HTTP请求失败: {response.status} - {error_text}")
                    return None

        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return None

    async def call_tool(self,
                        tool_name: str,
                        arguments: Dict[str, Any],
                        request_id: Optional[str] = None) -> Optional[MCPMessage]:
        """调用工具"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        if request_id:
            request["id"] = request_id

        message = MCPMessageParser.parse_message(request)
        return await self.send_message(message)

    async def list_tools(self, request_id: Optional[str] = None) -> Optional[MCPMessage]:
        """列出工具"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": request_id or "list_tools"
        }

        message = MCPMessageParser.parse_message(request)
        return await self.send_message(message)

    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None

        logger.info("HTTP客户端传输关闭")

    @asynccontextmanager
    async def connection(self):
        """上下文管理器"""
        try:
            await self.connect()
            yield self
        finally:
            await self.close()
