# -*- coding: utf-8 -*-
"""
@File    : tool_manager.py
@Time    : 2025/12/9
@Desc    : 极简工具管理器 - 基于LangChain Tools
"""
from typing import Dict, Any, List, Optional, Callable
from langchain_core.tools import BaseTool, StructuredTool
import logging

logger = logging.getLogger(__name__)


class ToolManager:
    """极简工具管理器：只做注册、列举和获取。"""

    def __init__(self):
        """初始化工具管理器"""
        self.tools: Dict[str, BaseTool] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        logger.info("工具管理器初始化")

        # 自动注册内置/已定义工具，避免忘记手动调用
        try:
            register_default_tools(self)
        except Exception as e:
            logger.warning(f"自动注册默认工具失败: {e}")

    def register_tool(self, tool: BaseTool, metadata: Optional[Dict[str, Any]] = None):
        """
        注册LangChain工具（直接使用 BaseTool/StructuredTool）
        """
        tool_name = tool.name
        self.tools[tool_name] = tool
        self.tool_metadata[tool_name] = metadata or {}
        logger.info(f"注册工具: {tool_name}")

    def register_custom_tool(
            self,
            name: str,
            description: str,
            func: Callable,
            args_schema: Optional[Any] = None,
            metadata: Optional[Dict[str, Any]] = None
    ):
        """将函数包装为 LangChain StructuredTool 并注册。"""
        tool = StructuredTool.from_function(
            func=func,
            name=name,
            description=description,
            args_schema=args_schema
        )
        self.register_tool(tool, metadata)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self.tools.get(name)

    def list_tools(self, with_metadata: bool = False) -> List[Any]:
        """
        列出所有已注册工具。
        Args:
            with_metadata: True 时返回 (tool, metadata) 元组列表，方便区分内置/自定义；默认仅返回工具对象。
        """
        if not with_metadata:
            return list(self.tools.values())
        return [
            (tool, self.tool_metadata.get(name, {}))
            for name, tool in self.tools.items()
        ]

    def get_tool_names(self) -> List[str]:
        """获取工具名称列表"""
        return list(self.tools.keys())

    def unregister_tool(self, name: str):
        """取消注册工具"""
        if name in self.tools:
            del self.tools[name]
            if name in self.tool_metadata:
                del self.tool_metadata[name]
            logger.info(f"取消注册工具: {name}")

    def get_tools_for_llm(self) -> List[BaseTool]:
        """
        获取用于LLM的工具列表
        
        Returns:
            LangChain Tools列表，可直接传递给LLM
        """
        return list(self.tools.values())

    def get_tool_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具元数据"""
        return self.tool_metadata.get(name)


# 全局工具管理器实例
_global_tool_manager: Optional[ToolManager] = None


def get_tool_manager() -> ToolManager:
    """获取全局工具管理器实例"""
    global _global_tool_manager
    if _global_tool_manager is None:
        _global_tool_manager = ToolManager()
    return _global_tool_manager


def register_default_tools(tool_manager: Optional[ToolManager] = None):
    """
    注册默认工具
    
    Args:
        tool_manager: 工具管理器实例，如果为None则使用全局实例
    """
    if tool_manager is None:
        tool_manager = get_tool_manager()

    # 注册内置工具（已是 LangChain BaseTool/StructuredTool）
    try:
        from .builtin_tools.calculator import calculator_tool
        tool_manager.register_tool(calculator_tool, {"category": "builtin", "type": "calculator"})
    except Exception as e:
        logger.warning(f"注册计算器工具失败: {e}")

    try:
        from .builtin_tools.web_search import web_search_tool
        tool_manager.register_tool(web_search_tool, {"category": "builtin", "type": "web_search"})
    except Exception as e:
        logger.warning(f"注册网页搜索工具失败: {e}")

    try:
        from .builtin_tools.knowledge_base import knowledge_base_tool
        tool_manager.register_tool(knowledge_base_tool, {"category": "builtin", "type": "knowledge_base"})
    except Exception as e:
        logger.warning(f"注册知识库工具失败: {e}")

    logger.info(f"已注册 {len(tool_manager.list_tools())} 个默认工具")
