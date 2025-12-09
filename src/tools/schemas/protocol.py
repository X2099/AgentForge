# -*- coding: utf-8 -*-
"""
@File    : protocol.py
@Time    : 2025/12/9 11:46
@Desc    : 
"""
from typing import Dict, Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class MCPProtocolVersion(str, Enum):
    """MCP协议版本"""
    V1 = "2024-11-05"


class ToolType(str, Enum):
    """工具类型"""
    FUNCTION = "function"


class JSONSchemaType(str, Enum):
    """JSON Schema类型"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


class JSONSchema(BaseModel):
    """JSON Schema定义"""
    type: Optional[Union[JSONSchemaType, List[JSONSchemaType]]] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, "JSONSchema"]] = None
    required: Optional[List[str]] = None
    items: Optional["JSONSchema"] = None
    enum: Optional[List[Any]] = None
    const: Optional[Any] = None
    default: Optional[Any] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    minLength: Optional[int] = None
    maxLength: Optional[int] = None
    pattern: Optional[str] = None
    format: Optional[str] = None


JSONSchema.update_forward_refs()


class Tool(BaseModel):
    """MCP工具定义"""
    name: str
    description: str
    inputSchema: JSONSchema


class TextContent(BaseModel):
    """文本内容"""
    type: Literal["text"] = "text"
    text: str


class ImageContent(BaseModel):
    """图片内容"""
    type: Literal["image"] = "image"
    data: str
    mimeType: str


Content = Union[TextContent, ImageContent]


class ToolResult(BaseModel):
    """工具执行结果"""
    content: List[Content]
    isError: Optional[bool] = False


class Request(BaseModel):
    """MCP请求基类"""
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]] = Field(default_factory=lambda: str(uuid.uuid4()))


class Notification(Request):
    """MCP通知"""
    id: None = None


# 服务器 -> 客户端 消息
class InitializeResult(BaseModel):
    """初始化响应"""
    protocolVersion: MCPProtocolVersion
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    serverInfo: Optional[Dict[str, Any]] = None


class ListToolsResult(BaseModel):
    """列出工具响应"""
    tools: List[Tool]


class CallToolResult(BaseModel):
    """调用工具响应"""
    content: List[Content]
    isError: Optional[bool] = False


# 客户端 -> 服务器 消息
class InitializeRequest(Request):
    """初始化请求"""
    method: Literal["initialize"] = "initialize"
    params: Dict[str, Any]


class ListToolsRequest(Request):
    """列出工具请求"""
    method: Literal["tools/list"] = "tools/list"


class CallToolRequest(Request):
    """调用工具请求"""
    method: Literal["tools/call"] = "tools/call"
    params: Dict[str, Any]


class NotificationMessage(Notification):
    """通知消息"""
    method: str
    params: Optional[Dict[str, Any]] = None


# 响应消息
class Response(BaseModel):
    """MCP响应基类"""
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]] = None


class SuccessResponse(Response):
    """成功响应"""
    result: Union[InitializeResult, ListToolsResult, CallToolResult]


class ErrorResponse(Response):
    """错误响应"""
    error: Dict[str, Any]


# 消息类型别名
MCPRequest = Union[InitializeRequest, ListToolsRequest, CallToolRequest]
MCPResponse = Union[SuccessResponse, ErrorResponse]
MCPMessage = Union[MCPRequest, MCPResponse, NotificationMessage]


class MCPConfig(BaseModel):
    """MCP配置"""
    protocol_version: MCPProtocolVersion = MCPProtocolVersion.V1
    server_info: Optional[Dict[str, Any]] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    tools: List[Tool] = Field(default_factory=list)

    class Config:
        use_enum_values = True
