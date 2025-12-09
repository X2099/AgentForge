# -*- coding: utf-8 -*-
"""
@File    : message_system.py
@Time    : 2025/12/9 10:11
@Desc    : 
"""
import json
from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class MessageType(Enum):
    """消息类型枚举"""
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"
    TOOL = "tool"
    FUNCTION = "function"
    CHUNK = "chunk"


@dataclass
class Message:
    """消息数据类"""
    content: str
    type: MessageType
    metadata: Dict[str, Any] = None
    timestamp: str = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "content": self.content,
            "type": self.type.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建"""
        return cls(
            content=data["content"],
            type=MessageType(data["type"]),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp")
        )


class MessageManager:
    """消息管理器"""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self.messages: List[Message] = []

    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        # 保持消息数量不超过限制
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def add_human_message(self, content: str, metadata: Dict[str, Any] = None):
        """添加人类消息"""
        message = Message(
            content=content,
            type=MessageType.HUMAN,
            metadata=metadata or {}
        )
        self.add_message(message)

    def add_ai_message(self, content: str, metadata: Dict[str, Any] = None):
        """添加AI消息"""
        message = Message(
            content=content,
            type=MessageType.AI,
            metadata=metadata or {}
        )
        self.add_message(message)

    def add_tool_message(self, tool_name: str, tool_output: Any,
                         metadata: Dict[str, Any] = None):
        """添加工具消息"""
        message = Message(
            content=json.dumps(tool_output, ensure_ascii=False),
            type=MessageType.TOOL,
            metadata={
                "tool_name": tool_name,
                **(metadata or {})
            }
        )
        self.add_message(message)

    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """获取最近的消息"""
        return self.messages[-count:]

    def get_conversation_history(self) -> str:
        """获取对话历史文本"""
        history = []
        for msg in self.messages:
            role = msg.type.value.upper()
            history.append(f"{role}: {msg.content}")
        return "\n".join(history)

    def clear_messages(self):
        """清空消息"""
        self.messages = []
