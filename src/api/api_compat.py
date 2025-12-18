# -*- coding: utf-8 -*-
"""
兼容性层 - 重导出新API结构以保持向后兼容
"""
# 重导出应用
from .main import create_app

# 创建应用实例以保持兼容性
app = create_app()

# 重导出数据模型
from .models import ChatRequest, KnowledgeBaseRequest


# 重导出路由函数（通过app调用）
async def chat(request: ChatRequest):
    """聊天接口"""
    from .routes.chat_routes import chat as chat_route
    return await chat_route(request)


async def create_knowledge_base(request: KnowledgeBaseRequest):
    """创建知识库"""
    from .routes.knowledge_base_routes import create_knowledge_base as create_kb_route
    return await create_kb_route(request)


async def list_knowledge_bases():
    """列出知识库"""
    from .routes.knowledge_base_routes import list_knowledge_bases as list_kb_route
    return await list_kb_route()


async def search_knowledge_base(kb_name: str, query: str, k: int = 5):
    """搜索知识库"""
    from .routes.knowledge_base_routes import search_knowledge_base as search_kb_route
    return await search_kb_route(kb_name, query, k)


async def list_tools():
    """列出工具"""
    from .routes.tool_routes import list_tools as list_tools_route
    return await list_tools_route()


async def call_tool(tool_name: str, arguments: dict):
    """调用工具"""
    from .routes.tool_routes import call_tool as call_tool_route
    return await call_tool_route(tool_name, arguments)
