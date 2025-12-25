# -*- coding: utf-8 -*-
"""
@File    : base_graph.py
@Time    : 2025/12/9 10:12
@Desc    : 基于LangGraph标准的图构建基类
"""
from typing import Dict, Any, List, Callable, Optional
from abc import ABC, abstractmethod

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer

from ..state.base_state import GraphState

import logging

logger = logging.getLogger(__name__)


class BaseGraph(ABC):
    """
    图基类 - 基于LangGraph标准
    
    提供统一的图构建接口和Checkpointer集成
    """

    def __init__(
            self,
            name: str,
            description: str = "",
            state_type: Optional[Any] = None
    ):
        """
        初始化图构建器
        
        Args:
            name: 图名称
            description: 图描述
            state_type: 状态类型（TypedDict子类）
        """
        self.name = name
        self.description = description

        if state_type is None:
            state_type = GraphState

        # 创建StateGraph实例
        self.graph = StateGraph(state_type)
        self.nodes: Dict[str, Callable] = {}
        self.edges: List[tuple] = []
        self.conditional_edges: List[Dict[str, Any]] = []

        # Checkpointer支持
        self.checkpointer: Optional[BaseCheckpointSaver] = None
        # 长期记忆
        self.store: Optional[BaseStore] = None

    @abstractmethod
    def build(self):
        """
        构建图结构
        
        子类必须实现此方法来定义节点和边
        """
        pass

    def compile(
            self,
            checkpointer: Optional[Checkpointer] = None,
            store: Optional[BaseStore] = None,
            interrupt_before: Optional[List[str]] = None,
            interrupt_after: Optional[List[str]] = None
    ) -> CompiledStateGraph:
        """
        编译图
        
        Args:
            checkpointer: 检查点保存器（用于状态持久化）
            store: 长期记忆保存器
            interrupt_before: 在指定节点之前中断
            interrupt_after: 在指定节点之后中断
            
        Returns:
            编译后的图
        """
        # 先调用build方法构建图
        self.build()

        # 添加所有节点
        for node_name, node_func in self.nodes.items():
            self.graph.add_node(node_name, node_func)
            logger.debug(f"Added node: {node_name}")

        # 添加所有边
        for from_node, to_node in self.edges:
            self.graph.add_edge(from_node, to_node)
            logger.debug(f"Added edge: {from_node} -> {to_node}")

        # 添加条件边
        for edge_config in self.conditional_edges:
            self.graph.add_conditional_edges(**edge_config)
            logger.debug(f"Added conditional edge: {edge_config.get('source', 'unknown')}")

        # 记忆
        self.checkpointer = checkpointer or self.checkpointer
        self.store = store or self.store

        # 编译参数
        compile_kwargs = {}
        if self.checkpointer:
            compile_kwargs["checkpointer"] = self.checkpointer
        if self.store:
            compile_kwargs["store"] = self.store
        if interrupt_before:
            compile_kwargs["interrupt_before"] = interrupt_before
        if interrupt_after:
            compile_kwargs["interrupt_after"] = interrupt_after

        compiled_graph = self.graph.compile(**compile_kwargs)
        logger.info(f"Graph '{self.name}' compiled successfully")

        return compiled_graph

    def add_node(self, name: str, node_func: Callable):
        """
        添加节点
        
        Args:
            name: 节点名称
            node_func: 节点函数（接受state，返回state更新）
        """
        self.nodes[name] = node_func

    def add_edge(self, from_node: str, to_node: str):
        """
        添加边
        
        Args:
            from_node: 源节点
            to_node: 目标节点
        """
        self.edges.append((from_node, to_node))

    def add_conditional_edges(
            self,
            source: str,
            path: Optional[Callable] = None,
            path_map: Optional[Dict[str, str]] = None,
            condition: Optional[Callable] = None,
    ):
        """
        添加条件边（对齐最新LangGraph签名：source, path, path_map）
        
        Args:
            source: 源节点
            path: 路由函数（接受state，返回路由键或节点名）
            path_map: 路由映射 {路由键: 目标节点}，可选
            condition: 兼容旧参数名；若提供且path未提供，则使用condition作为path
        """
        route_fn = path or condition
        if route_fn is None:
            raise ValueError("add_conditional_edges 需要提供 path 或 condition 之一")

        self.conditional_edges.append({
            "source": source,
            "path": route_fn,
            "path_map": path_map
        })

    def set_finish_point(self, node: str):
        """
        设置结束节点
        
        Args:
            node: 结束节点名称（连接到END）
        """
        self.add_edge(node, END)

    def get_graph_info(self) -> Dict[str, Any]:
        """获取图信息"""
        return {
            "name": self.name,
            "description": self.description,
            "nodes": list(self.nodes.keys()),
            "edges": self.edges,
            "conditional_edges": len(self.conditional_edges),
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "has_checkpointer": self.checkpointer is not None
        }
