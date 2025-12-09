# -*- coding: utf-8 -*-
"""
@File    : control_nodes.py
@Time    : 2025/12/9 10:18
@Desc    : 
"""
from typing import Dict, Any
from ..nodes.base_node import Node
from ..state.base_state import AgentState


class RouterNode(Node):
    """路由节点"""

    def __init__(self, name: str, routing_rules: Dict[str, str] = None):
        super().__init__(name, "router", "路由决策节点")
        self.routing_rules = routing_rules or {}

    def execute(self, state: AgentState) -> Dict[str, Any]:
        """路由决策"""
        # 基于当前状态决定下一个节点
        next_node = self._decide_next_node(state)

        return {
            "next_node": next_node,
            "routing_decision": next_node,
            "routing_reason": self._get_routing_reason(state, next_node)
        }

    def _decide_next_node(self, state: AgentState) -> str:
        """决定下一个节点"""
        # 检查错误
        if state.get("error"):
            return "error_handler"

        # 检查工具调用
        if state.get("tool_calls"):
            return "tool_executor"

        # 检查是否需要人类输入
        if state.get("needs_human_input", False):
            return "human_input"

        # 默认返回LLM节点
        return "llm"

    def _get_routing_reason(self, state: AgentState, next_node: str) -> str:
        """获取路由原因"""
        reasons = {
            "error_handler": "检测到错误，需要处理",
            "tool_executor": "有工具调用需要执行",
            "human_input": "需要人类输入或确认",
            "llm": "继续对话处理"
        }
        return reasons.get(next_node, "默认路由")


class ConditionalNode(Node):
    """条件判断节点"""

    def __init__(self, name: str, condition_func):
        super().__init__(name, "conditional", "条件判断节点")
        self.condition_func = condition_func

    def execute(self, state: AgentState) -> Dict[str, Any]:
        """执行条件判断"""
        result = self.condition_func(state)

        return {
            "condition_result": result,
            "next_node": result if isinstance(result, str) else "llm"
        }


class HumanInputNode(Node):
    """人类输入节点"""

    def __init__(self, name: str):
        super().__init__(name, "human_input", "等待人类输入")

    def execute(self, state: AgentState) -> Dict[str, Any]:
        """处理人类输入"""
        # 在实际应用中，这里会等待用户输入
        # 现在模拟用户输入
        human_input = state.get("pending_human_input", "")

        if human_input:
            # 清除待处理输入
            state.pop("pending_human_input", None)

            # 添加到消息历史
            if "messages" in state:
                state["messages"].append({
                    "type": "human",
                    "content": human_input
                })

            return {
                "human_input_received": True,
                "human_input": human_input,
                "next_node": "llm"
            }
        else:
            # 没有输入，继续等待
            return {
                "human_input_received": False,
                "next_node": "human_input"  # 保持当前节点
            }
