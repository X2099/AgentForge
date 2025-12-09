# -*- coding: utf-8 -*-
"""
@File    : base_graph.py
@Time    : 2025/12/9 10:12
@Desc    : 
"""
from typing import Dict, Any, List, Callable
from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, END
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO
import base64

from ..state.base_state import BaseState, AgentState


class BaseGraph(ABC):
    """图基类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.graph = StateGraph(BaseState)
        self.nodes: Dict[str, Callable] = {}
        self.edges: List[tuple] = []

    @abstractmethod
    def build(self):
        """构建图结构"""
        pass

    def compile(self) -> StateGraph:
        """编译图"""
        # 添加所有节点
        for node_name, node_func in self.nodes.items():
            self.graph.add_node(node_name, node_func)

        # 添加所有边
        for from_node, to_node in self.edges:
            self.graph.add_edge(from_node, to_node)

        return self.graph.compile()

    def add_node(self, name: str, node_func: Callable):
        """添加节点"""
        self.nodes[name] = node_func

    def add_edge(self, from_node: str, to_node: str):
        """添加边"""
        self.edges.append((from_node, to_node))

    def add_conditional_edge(self, from_node: str, condition_func: Callable,
                             path_map: Dict[str, str]):
        """添加条件边"""
        self.graph.add_conditional_edges(
            from_node,
            condition_func,
            path_map
        )

    def visualize(self) -> str:
        """可视化图结构"""
        G = nx.DiGraph()

        # 添加节点
        for node_name in self.nodes.keys():
            G.add_node(node_name)

        # 添加边
        for from_node, to_node in self.edges:
            G.add_edge(from_node, to_node)

        # 绘制图
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(G, seed=42)
        nx.draw(G, pos, with_labels=True, node_color='lightblue',
                node_size=3000, font_size=10, font_weight='bold',
                arrowsize=20)

        # 保存为Base64图片
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return f"data:image/png;base64,{img_base64}"

    def get_graph_info(self) -> Dict[str, Any]:
        """获取图信息"""
        return {
            "name": self.name,
            "description": self.description,
            "nodes": list(self.nodes.keys()),
            "edges": self.edges,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges)
        }


class AgentGraph(BaseGraph):
    """Agent图基类"""

    def __init__(self, name: str, description: str = "",
                 max_iterations: int = 10):
        super().__init__(name, description)
        self.max_iterations = max_iterations
        self.tools: Dict[str, Callable] = {}

    def add_tool(self, tool_name: str, tool_func: Callable,
                 tool_description: str = ""):
        """添加工具"""
        self.tools[tool_name] = {
            "function": tool_func,
            "description": tool_description
        }

    def build_agent_flow(self):
        """构建基础的Agent流程"""
        # 基础节点
        self.add_node("receive_input", self._receive_input_node)
        self.add_node("call_llm", self._call_llm_node)
        self.add_node("execute_tools", self._execute_tools_node)
        self.add_node("format_response", self._format_response_node)

        # 基础流程
        self.add_edge("receive_input", "call_llm")
        self.add_edge("call_llm", "execute_tools")
        self.add_edge("execute_tools", "format_response")

        # 添加循环
        self.add_conditional_edge(
            "format_response",
            self._should_continue,
            {
                "continue": "call_llm",
                "end": END
            }
        )

    def _receive_input_node(self, state: AgentState) -> AgentState:
        """接收输入节点"""
        # 初始化状态
        state["iteration_count"] = 0
        state["should_continue"] = True
        state["max_iterations"] = self.max_iterations
        state["tool_outputs"] = []
        state["current_step"] = "receive_input"

        return state

    def _call_llm_node(self, state: AgentState) -> AgentState:
        """调用LLM节点"""
        raise NotImplementedError("子类必须实现此方法")

    def _execute_tools_node(self, state: AgentState) -> AgentState:
        """执行工具节点"""
        raise NotImplementedError("子类必须实现此方法")

    def _format_response_node(self, state: AgentState) -> AgentState:
        """格式化响应节点"""
        raise NotImplementedError("子类必须实现此方法")

    def _should_continue(self, state: AgentState) -> str:
        """判断是否继续执行"""
        iteration = state.get("iteration_count", 0)
        max_iter = state.get("max_iterations", self.max_iterations)

        if iteration >= max_iter:
            return "end"

        if not state.get("should_continue", True):
            return "end"

        # 检查是否有待处理的工具调用
        if state.get("last_tool_call") and state.get("tool_outputs"):
            return "continue"

        return "end"
