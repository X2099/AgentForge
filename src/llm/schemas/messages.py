# -*- coding: utf-8 -*-
"""
@File    : messages.py
@Time    : 2025/12/9 10:29
@Desc    : 
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class ToolType(str, Enum):
    """工具类型"""
    FUNCTION = "function"
    CODE_INTERPRETER = "code_interpreter"
    RETRIEVAL = "retrieval"


class ToolCall(BaseModel):
    """工具调用"""
    id: str
    type: ToolType = ToolType.FUNCTION
    function: Dict[str, Any]


class Message(BaseModel):
    """消息模型"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None

    class Config:
        use_enum_values = True


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


class ToolDefinition(BaseModel):
    """工具定义"""
    type: ToolType = ToolType.FUNCTION
    function: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[Message]
    model: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    stop: Optional[Union[str, List[str]]] = None
    stream: bool = False
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    n: int = Field(default=1, ge=1)

    class Config:
        arbitrary_types_allowed = True


class ChatResponse(BaseModel):
    """聊天响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    system_fingerprint: Optional[str] = None

    def get_content(self) -> Optional[str]:
        """获取消息内容"""
        if self.choices:
            message = self.choices[0].get("message", {})
            return message.get("content")
        return None

    def get_tool_calls(self) -> List[ToolCall]:
        """获取工具调用"""
        tool_calls = []
        if self.choices:
            message = self.choices[0].get("message", {})
            raw_tool_calls = message.get("tool_calls", [])
            for tool_call in raw_tool_calls:
                tool_calls.append(ToolCall(**tool_call))
        return tool_calls


class StreamResponse(BaseModel):
    """流式响应"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]

    def is_finished(self) -> bool:
        """判断是否结束"""
        if self.choices:
            finish_reason = self.choices[0].get("finish_reason")
            return finish_reason is not None
        return True
