# -*- coding: utf-8 -*-
"""
API路由模块 - 统一导出所有路由
"""
from .system_routes import router as system_router, init_system_dependencies
from .chat_routes import router as chat_router, init_chat_dependencies
from .kb_routes import router as kb_router, init_kb_dependencies
from .tool_routes import router as tool_router, init_tool_dependencies
from .auth_routes import router as auth_router, init_auth_dependencies
from .user_routes import router as user_router, init_user_dependencies

__all__ = [
    # 路由器
    "system_router",
    "chat_router",
    "kb_router",
    "tool_router",
    "auth_router",
    "user_router",

    # 初始化函数
    "init_system_dependencies",
    "init_chat_dependencies",
    "init_kb_dependencies",
    "init_tool_dependencies",
    "init_auth_dependencies",
    "init_user_dependencies"
]
