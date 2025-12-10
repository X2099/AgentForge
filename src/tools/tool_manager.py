# -*- coding: utf-8 -*-
"""
@File    : tool_manager.py
@Time    : 2025/12/9
@Desc    : 统一的工具管理器 - 基于LangChain Tools标准
"""
from typing import Dict, Any, List, Optional, Callable, Union
from langchain_core.tools import BaseTool, StructuredTool, tool
from pydantic import BaseModel, Field
import logging
import inspect

logger = logging.getLogger(__name__)


class ToolManager:
    """
    工具管理器
    
    统一管理工具，支持：
    - LangChain Tools
    - 自定义工具（通过适配器转换为LangChain Tools）
    - MCP工具（可选）
    """
    
    def __init__(self):
        """初始化工具管理器"""
        self.tools: Dict[str, BaseTool] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        logger.info("工具管理器初始化")
    
    def register_tool(self, tool: BaseTool, metadata: Optional[Dict[str, Any]] = None):
        """
        注册LangChain工具
        
        Args:
            tool: LangChain BaseTool实例
            metadata: 工具元数据（可选）
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
        args_schema: Optional[BaseModel] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        注册自定义工具（自动转换为LangChain Tool）
        
        Args:
            name: 工具名称
            description: 工具描述
            func: 工具函数
            args_schema: 参数模式（Pydantic模型）
            metadata: 工具元数据
        """
        # 创建LangChain工具
        langchain_tool = StructuredTool.from_function(
            func=func,
            name=name,
            description=description,
            args_schema=args_schema
        )
        
        self.register_tool(langchain_tool, metadata)
    
    def register_dict_tool(
        self,
        name: str,
        description: str,
        handler: Callable[[Dict[str, Any]], Any],
        input_schema: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        从字典模式注册工具（兼容旧格式）
        
        Args:
            name: 工具名称
            description: 工具描述
            handler: 工具处理函数（接受Dict参数）
            input_schema: JSON Schema格式的输入模式
            metadata: 工具元数据
        """
        # 创建Pydantic模型
        args_model = self._create_pydantic_model_from_schema(name, input_schema)
        
        # 创建包装函数
        def wrapped_func(**kwargs):
            return handler(kwargs)
        
        # 注册工具
        langchain_tool = StructuredTool.from_function(
            func=wrapped_func,
            name=name,
            description=description,
            args_schema=args_model
        )
        
        self.register_tool(langchain_tool, metadata)
    
    def register_builtin_tool(self, tool_instance: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        注册内置工具实例（自动适配）
        
        支持工具实例具有：
        - get_tool_schema() 方法返回JSON Schema
        - execute() 或 __call__() 方法执行工具
        
        Args:
            tool_instance: 工具实例
            metadata: 工具元数据
        """
        if not hasattr(tool_instance, 'get_tool_schema'):
            raise ValueError(f"工具实例 {tool_instance} 没有 get_tool_schema 方法")
        
        schema = tool_instance.get_tool_schema()
        name = schema.get("name")
        description = schema.get("description", "")
        input_schema = schema.get("inputSchema", {})
        
        # 获取执行函数
        if hasattr(tool_instance, 'execute'):
            handler = tool_instance.execute
        elif hasattr(tool_instance, '__call__'):
            handler = tool_instance
        else:
            raise ValueError(f"工具 {tool_instance} 没有执行方法")
        
        # 检查是否是异步函数
        is_async = inspect.iscoroutinefunction(handler)
        
        if is_async:
            # 对于异步函数，需要包装
            async def async_handler(arguments: Dict[str, Any]) -> Any:
                return await handler(arguments)
            
            self.register_dict_tool(
                name=name,
                description=description,
                handler=async_handler,
                input_schema=input_schema,
                metadata=metadata
            )
        else:
            self.register_dict_tool(
                name=name,
                description=description,
                handler=handler,
                input_schema=input_schema,
                metadata=metadata
            )
    
    def _create_pydantic_model_from_schema(self, model_name: str, schema: Dict[str, Any]) -> type[BaseModel]:
        """
        从JSON Schema创建Pydantic模型
        
        Args:
            model_name: 模型名称
            schema: JSON Schema
            
        Returns:
            Pydantic模型类
        """
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # 创建字段定义
        field_definitions = {}
        annotations = {}
        
        for prop_name, prop_schema in properties.items():
            prop_type = self._get_python_type(prop_schema.get("type", "string"))
            description = prop_schema.get("description", "")
            
            # 创建Field
            if prop_name in required:
                field_definitions[prop_name] = Field(description=description)
            else:
                field_definitions[prop_name] = Field(default=None, description=description)
            
            annotations[prop_name] = Optional[prop_type] if prop_name not in required else prop_type
        
        # 创建模型类
        model = type(
            f"{model_name}Args",
            (BaseModel,),
            {
                "__annotations__": annotations,
                **field_definitions
            }
        )
        
        return model
    
    def _get_python_type(self, json_type: str) -> type:
        """将JSON Schema类型转换为Python类型"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,
            "array": list
        }
        return type_mapping.get(json_type, str)
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        """列出所有工具"""
        return list(self.tools.values())
    
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
    
    # 注册内置工具
    try:
        from .builtin_tools.calculator import CalculatorTool
        calculator = CalculatorTool()
        tool_manager.register_builtin_tool(calculator, {"category": "builtin", "type": "calculator"})
    except Exception as e:
        logger.warning(f"注册计算器工具失败: {e}")
    
    try:
        from .builtin_tools.web_search import WebSearchTool
        web_search = WebSearchTool()
        tool_manager.register_builtin_tool(web_search, {"category": "builtin", "type": "web_search"})
    except Exception as e:
        logger.warning(f"注册网页搜索工具失败: {e}")
    
    try:
        from .builtin_tools.knowledge_base import KnowledgeBaseTool
        # KnowledgeBaseTool需要知识库参数，这里不自动注册
        # kb_tool = KnowledgeBaseTool(knowledge_base)
        pass
    except Exception as e:
        logger.warning(f"跳过知识库工具自动注册: {e}")
    
    logger.info(f"已注册 {len(tool_manager.list_tools())} 个默认工具")

