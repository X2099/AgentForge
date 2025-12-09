# -*- coding: utf-8 -*-
"""
@File    : base_node.py
@Time    : 2025/12/9 10:16
@Desc    : 
"""
from typing import Dict, Any, Callable
from abc import ABC, abstractmethod

import logging

from ..state.base_state import AgentState

logger = logging.getLogger(__name__)


class Node(ABC):
    """节点基类"""

    def __init__(self, name: str, node_type: str, description: str = ""):
        self.name = name
        self.node_type = node_type
        self.description = description
        self.config: Dict[str, Any] = {}

    def __call__(self, state: AgentState) -> AgentState:
        """执行节点"""
        try:
            logger.info(f"Executing node: {self.name}")
            state["current_step"] = self.name

            result = self.execute(state)

            # 更新状态
            if "next_node" in result:
                state["next_node"] = result["next_node"]

            # 合并结果
            for key, value in result.items():
                if key != "next_node":
                    state[key] = value

            logger.info(f"Node {self.name} executed successfully")
            return state

        except Exception as e:
            logger.error(f"Error executing node {self.name}: {str(e)}")
            state["error"] = str(e)
            state["next_node"] = "error_handler"
            return state

    @abstractmethod
    def execute(self, state: AgentState) -> Dict[str, Any]:
        """执行节点逻辑"""
        pass

    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)

    def get_info(self) -> Dict[str, Any]:
        """获取节点信息"""
        return {
            "name": self.name,
            "type": self.node_type,
            "description": self.description,
            "config": self.config
        }


class AsyncNode(Node):
    """异步节点"""

    async def __call__(self, state: AgentState) -> AgentState:
        """异步执行节点"""
        try:
            logger.info(f"Executing async node: {self.name}")
            state["current_step"] = self.name

            result = await self.execute_async(state)

            # 更新状态
            if "next_node" in result:
                state["next_node"] = result["next_node"]

            # 合并结果
            for key, value in result.items():
                if key != "next_node":
                    state[key] = value

            logger.info(f"Async node {self.name} executed successfully")
            return state

        except Exception as e:
            logger.error(f"Error executing async node {self.name}: {str(e)}")
            state["error"] = str(e)
            state["next_node"] = "error_handler"
            return state

    @abstractmethod
    async def execute_async(self, state: AgentState) -> Dict[str, Any]:
        """异步执行节点逻辑"""
        pass


# 装饰器：将同步函数转换为节点
def create_node(name: str, node_type: str = "custom"):
    """创建节点装饰器"""

    def decorator(func: Callable):
        class FunctionNode(Node):
            def __init__(self):
                super().__init__(name, node_type, func.__doc__ or "")

            def execute(self, state: AgentState) -> Dict[str, Any]:
                return func(state)

        return FunctionNode()

    return decorator


# 装饰器：将异步函数转换为节点
def create_async_node(name: str, node_type: str = "custom"):
    """创建异步节点装饰器"""

    def decorator(func: Callable):
        class AsyncFunctionNode(AsyncNode):
            def __init__(self):
                super().__init__(name, node_type, func.__doc__ or "")

            async def execute_async(self, state: AgentState) -> Dict[str, Any]:
                return await func(state)

        return AsyncFunctionNode()

    return decorator
