# -*- coding: utf-8 -*-
"""
@File    : base_state.py
@Time    : 2025/12/9 10:08
@Desc    : 
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph.message import add_messages


class BaseState(TypedDict):
    """基础状态类"""
    # 消息历史
    messages: Annotated[List[Dict[str, Any]], add_messages]

    # 当前状态
    current_step: str
    last_tool_call: Optional[Dict[str, Any]]
    tool_outputs: List[Dict[str, Any]]

    # 控制流
    next_node: Optional[str]
    should_continue: bool
    max_iterations: int
    iteration_count: int

    # 会话信息
    session_id: str
    user_id: Optional[str]
    timestamp: str


class AgentState(BaseState):
    """Agent专用状态"""
    # Agent特定字段
    agent_type: str
    agent_role: str
    available_tools: List[str]

    # 记忆相关
    retrieved_documents: List[Dict[str, Any]]
    memory_context: str
    summary: str

    # 工具调用历史
    tool_call_history: List[Dict[str, Any]]

    # 错误处理
    error: Optional[str]
    retry_count: int


class WorkflowState(AgentState):
    """工作流状态"""
    workflow_name: str
    workflow_steps: List[str]
    current_step_index: int
    workflow_result: Optional[Dict[str, Any]]

    # 分支控制
    branch_decision: Optional[str]
    condition_results: Dict[str, bool]
