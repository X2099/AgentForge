# -*- coding: utf-8 -*-
"""
@File    : mcp_server.py
@Time    : 2025/12/9 11:51
@Desc    : MCP服务器
"""
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
import logging
from contextlib import asynccontextmanager

from .schemas.protocol import (
    Tool, ToolResult, Content, TextContent,
    InitializeResult, ListToolsResult, CallToolResult,
    MCPProtocolVersion, MCPConfig
)
from .schemas.messages import (
    MCPMessageParser, MCPMessage, MCPRequest,
    InitializeRequest, ListToolsRequest, CallToolRequest,
    SuccessResponse, ErrorResponse, MCPErrorCodes
)
from .transports import TransportFactory, TransportType

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """工具定义（内部）"""
    name: str
    description: str
    handler: Callable[[Dict[str, Any]], Any]
    input_schema: Dict[str, Any]

    def to_mcp_tool(self) -> Tool:
        """转换为MCP工具"""
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )


class MCPServer:
    """MCP服务器"""

    def __init__(self,
                 config: Optional[MCPConfig] = None,
                 transport_type: TransportType = TransportType.STDIO):
        """
        初始化MCP服务器

        Args:
            config: MCP配置
            transport_type: 传输类型
        """
        self.config = config or MCPConfig()
        self.transport_type = transport_type
        self.transport = None

        # 工具注册表
        self.tools: Dict[str, ToolDefinition] = {}

        # 服务器状态
        self.is_initialized = False
        self.client_capabilities: Dict[str, Any] = {}

        # 请求处理器映射
        self.request_handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool
        }

        logger.info(f"MCP服务器初始化 - 协议版本: {self.config.protocol_version}")

    def register_tool(self,
                      name: str,
                      description: str,
                      handler: Callable[[Dict[str, Any]], Any],
                      input_schema: Dict[str, Any]):
        """
        注册工具

        Args:
            name: 工具名称
            description: 工具描述
            handler: 工具处理函数
            input_schema: 输入模式
        """
        if name in self.tools:
            logger.warning(f"工具 '{name}' 已存在，将被覆盖")

        tool = ToolDefinition(
            name=name,
            description=description,
            handler=handler,
            input_schema=input_schema
        )

        self.tools[name] = tool
        logger.info(f"注册工具: {name}")

    def register_tool_decorator(self,
                                name: str,
                                description: str,
                                input_schema: Dict[str, Any]):
        """
        工具注册装饰器

        Args:
            name: 工具名称
            description: 工具描述
            input_schema: 输入模式

        Returns:
            装饰器函数
        """

        def decorator(func):
            self.register_tool(name, description, func, input_schema)
            return func

        return decorator

    async def _handle_initialize(self, request: InitializeRequest) -> SuccessResponse:
        """处理初始化请求"""
        try:
            # 存储客户端能力
            self.client_capabilities = request.params.get("capabilities", {})
            self.is_initialized = True

            # 准备响应
            result = InitializeResult(
                protocolVersion=self.config.protocol_version,
                capabilities={},  # 服务器能力
                serverInfo=self.config.server_info
            )

            response = MCPMessageParser.create_success_response(
                request_id=request.id,
                result=result
            )

            logger.info("客户端初始化成功")
            return response

        except Exception as e:
            logger.error(f"初始化处理失败: {str(e)}")
            return MCPMessageParser.create_error_response(
                request_id=request.id,
                code=MCPErrorCodes.INTERNAL_ERROR,
                message=str(e)
            )

    async def _handle_list_tools(self, request: ListToolsRequest) -> SuccessResponse:
        """处理列出工具请求"""
        try:
            # 检查是否已初始化
            if not self.is_initialized:
                return MCPMessageParser.create_error_response(
                    request_id=request.id,
                    code=MCPErrorCodes.INVALID_REQUEST,
                    message="Server not initialized"
                )

            # 获取工具列表
            mcp_tools = [tool.to_mcp_tool() for tool in self.tools.values()]

            result = ListToolsResult(tools=mcp_tools)
            response = MCPMessageParser.create_success_response(
                request_id=request.id,
                result=result
            )

            logger.debug(f"列出工具: {len(mcp_tools)} 个")
            return response

        except Exception as e:
            logger.error(f"列出工具失败: {str(e)}")
            return MCPMessageParser.create_error_response(
                request_id=request.id,
                code=MCPErrorCodes.INTERNAL_ERROR,
                message=str(e)
            )

    async def _handle_call_tool(self, request: CallToolRequest) -> SuccessResponse:
        """处理调用工具请求"""
        try:
            # 检查是否已初始化
            if not self.is_initialized:
                return MCPMessageParser.create_error_response(
                    request_id=request.id,
                    code=MCPErrorCodes.INVALID_REQUEST,
                    message="Server not initialized"
                )

            # 提取参数
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})

            if not tool_name:
                return MCPMessageParser.create_error_response(
                    request_id=request.id,
                    code=MCPErrorCodes.INVALID_PARAMS,
                    message="Missing tool name"
                )

            # 查找工具
            if tool_name not in self.tools:
                return MCPMessageParser.create_error_response(
                    request_id=request.id,
                    code=MCPErrorCodes.TOOL_NOT_FOUND,
                    message=f"Tool not found: {tool_name}"
                )

            tool = self.tools[tool_name]

            # 执行工具
            logger.info(f"执行工具: {tool_name}")
            try:
                result = tool.handler(arguments)

                # 标准化结果格式
                if isinstance(result, ToolResult):
                    tool_result = result
                elif isinstance(result, str):
                    tool_result = ToolResult(
                        content=[TextContent(text=result)]
                    )
                elif isinstance(result, dict):
                    # 尝试从字典创建
                    if "content" in result:
                        tool_result = ToolResult(**result)
                    else:
                        # 转换为文本
                        import json
                        tool_result = ToolResult(
                            content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
                        )
                else:
                    # 转换为字符串
                    tool_result = ToolResult(
                        content=[TextContent(text=str(result))]
                    )

            except Exception as e:
                logger.error(f"工具执行失败 {tool_name}: {str(e)}")
                return MCPMessageParser.create_error_response(
                    request_id=request.id,
                    code=MCPErrorCodes.TOOL_EXECUTION_ERROR,
                    message=str(e)
                )

            # 创建响应
            result_obj = CallToolResult(
                content=tool_result.content,
                isError=tool_result.isError
            )

            response = MCPMessageParser.create_success_response(
                request_id=request.id,
                result=result_obj
            )

            logger.debug(f"工具执行完成: {tool_name}")
            return response

        except Exception as e:
            logger.error(f"调用工具失败: {str(e)}")
            return MCPMessageParser.create_error_response(
                request_id=request.id,
                code=MCPErrorCodes.INTERNAL_ERROR,
                message=str(e)
            )

    async def handle_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理消息"""
        try:
            # 处理请求
            if isinstance(message, MCPRequest):
                handler = self.request_handlers.get(message.method)
                if handler:
                    return await handler(message)
                else:
                    return MCPMessageParser.create_error_response(
                        request_id=message.id,
                        code=MCPErrorCodes.METHOD_NOT_FOUND,
                        message=f"Method not found: {message.method}"
                    )

            # 忽略其他类型消息
            return None

        except Exception as e:
            logger.error(f"消息处理失败: {str(e)}")
            return MCPMessageParser.create_error_response(
                request_id=message.id if hasattr(message, 'id') else None,
                code=MCPErrorCodes.INTERNAL_ERROR,
                message=str(e)
            )

    async def start(self, transport_config: Optional[Dict[str, Any]] = None):
        """启动服务器"""
        # 创建传输
        self.transport = TransportFactory.create_server_transport(
            self.transport_type,
            transport_config or {}
        )

        # 设置消息处理器
        if hasattr(self.transport, 'set_message_handler'):
            self.transport.set_message_handler(self.handle_message)

        # 启动传输
        if self.transport_type == TransportType.STDIO:
            # STDIO传输是阻塞的
            await self.transport.listen(self.handle_message)
        elif self.transport_type == TransportType.HTTP:
            # HTTP传输需要显式启动
            await self.transport.start()

            # 保持运行
            try:
                await asyncio.Future()  # 永久运行
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止服务器")

    async def stop(self):
        """停止服务器"""
        if self.transport:
            await self.transport.stop()

        logger.info("MCP服务器已停止")

    @asynccontextmanager
    async def run(self, transport_config: Optional[Dict[str, Any]] = None):
        """运行服务器（上下文管理器）"""
        try:
            # 启动服务器
            server_task = asyncio.create_task(self.start(transport_config))

            # 等待一段时间确保服务器启动
            await asyncio.sleep(0.1)

            yield self
        finally:
            # 停止服务器
            await self.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    def get_tool_count(self) -> int:
        """获取工具数量"""
        return len(self.tools)

    def get_tool_names(self) -> List[str]:
        """获取工具名称列表"""
        return list(self.tools.keys())
