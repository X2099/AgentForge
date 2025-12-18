# -*- coding: utf-8 -*-
"""
@File    : base_state.py
@Time    : 2025/12/9 10:08
@Desc    : 基于LangGraph标准的状态定义
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph.message import AnyMessage, add_messages


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


class AgentState(GraphState, total=False):
    """
    Agent专用状态

    扩展基础状态，添加Agent特定字段
    """
    # Agent配置
    system_prompt: Optional[str]

    # 工具相关
    available_tools: Annotated[List[str], lambda x, y: y or x]
    tool_calls: Annotated[List[Dict[str, Any]], lambda x, y: (x or []) + (y or [])]
    tool_results: Annotated[List[Dict[str, Any]], lambda x, y: (x or []) + (y or [])]

    # 记忆相关
    retrieved_documents: Annotated[List[Dict[str, Any]], lambda x, y: (x or []) + (y or [])]
    memory_context: Optional[str]
    summary: Optional[str]

    # 控制流
    should_continue: bool
    max_iterations: int
    iteration_count: int

    # 错误处理
    error: Optional[str]
    retry_count: int


class WorkflowState(AgentState, total=False):
    """
    工作流状态

    用于复杂多步骤工作流
    """
    workflow_name: str
    workflow_steps: Annotated[List[str], lambda x, y: y or x]
    current_step_index: int
    workflow_result: Optional[Dict[str, Any]]
