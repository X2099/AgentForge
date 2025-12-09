# -*- coding: utf-8 -*-
"""
@File    : messages.py
@Time    : 2025/12/9 11:46
@Desc    : 
"""
from typing import Any, Optional, Union
import json

from .protocol import (
    MCPRequest, MCPResponse, MCPMessage, NotificationMessage,
    InitializeRequest, ListToolsRequest, CallToolRequest,
    SuccessResponse, ErrorResponse
)


class MCPMessageParser:
    """MCP消息解析器"""

    @staticmethod
    def parse_message(data: Union[str, bytes, dict]) -> MCPMessage:
        """解析MCP消息"""
        if isinstance(data, bytes):
            data = data.decode('utf-8')

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {str(e)}")

        if not isinstance(data, dict):
            raise ValueError("Message must be a dictionary")

        # 检查JSON-RPC版本
        if data.get("jsonrpc") != "2.0":
            raise ValueError("Invalid JSON-RPC version")

        # 检查消息类型
        if "method" in data:
            # 请求或通知
            if data.get("id") is None:
                return NotificationMessage(**data)
            else:
                return MCPMessageParser._parse_request(data)
        elif "result" in data or "error" in data:
            # 响应
            return MCPMessageParser._parse_response(data)
        else:
            raise ValueError("Invalid message format")

    @staticmethod
    def _parse_request(data: dict) -> MCPRequest:
        """解析请求"""
        method = data.get("method")

        if method == "initialize":
            return InitializeRequest(**data)
        elif method == "tools/list":
            return ListToolsRequest(**data)
        elif method == "tools/call":
            return CallToolRequest(**data)
        else:
            raise ValueError(f"Unknown method: {method}")

    @staticmethod
    def _parse_response(data: dict) -> MCPResponse:
        """解析响应"""
        if "error" in data:
            return ErrorResponse(**data)
        else:
            return SuccessResponse(**data)

    @staticmethod
    def serialize_message(message: MCPMessage) -> str:
        """序列化MCP消息"""
        return json.dumps(message.dict(exclude_none=True), ensure_ascii=False)

    @staticmethod
    def create_error_response(request_id: Optional[Union[str, int]],
                              code: int,
                              message: str,
                              data: Optional[Any] = None) -> ErrorResponse:
        """创建错误响应"""
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data

        return ErrorResponse(
            jsonrpc="2.0",
            id=request_id,
            error=error
        )

    @staticmethod
    def create_success_response(request_id: Optional[Union[str, int]],
                                result: Any) -> SuccessResponse:
        """创建成功响应"""
        return SuccessResponse(
            jsonrpc="2.0",
            id=request_id,
            result=result
        )


class MCPErrorCodes:
    """MCP错误码"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32000
    SERVER_ERROR_END = -32099

    # 自定义错误码
    TOOL_NOT_FOUND = -33001
    TOOL_EXECUTION_ERROR = -33002
    PERMISSION_DENIED = -33003
    RATE_LIMITED = -33004
