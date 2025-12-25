# -*- coding: utf-8 -*-
"""
@File    : base_state.py
@Time    : 2025/12/9 10:08
@Desc    : 基于LangGraph标准的状态定义
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    """
    LangGraph标准状态定义

    使用TypedDict确保类型安全，使用Annotated确保状态正确合并
    total=False表示所有字段都是可选的
    """
    # 消息历史 - 使用LangGraph标准的消息合并机制
    messages: Annotated[list[AnyMessage], add_messages]


class DisplayMessage(TypedDict, total=False):
    """
    便于在前端展示的人机会话信息
    """
    message: Optional[AnyMessage]
    sources: List[Dict[str, Any]]
