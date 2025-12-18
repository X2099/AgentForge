# -*- coding: utf-8 -*-
"""
API模块 - 提供RESTful API服务
"""

from .main import create_app, run_server
from .models import (
    ChatRequest, ChatResponse,
    KnowledgeBaseRequest, KnowledgeBaseResponse,
    DocumentUploadRequest,
    LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
    UserResponse,
    UserSessionCreateRequest, UserSessionResponse,
    UserStatsResponse
)
from .routes import (
    system_router,
    chat_router,
    kb_router,
    tool_router,
    auth_router,
    user_router
)

__all__ = [
    # 应用创建和运行
    "create_app",
    "run_server",

    # 数据模型
    "ChatRequest",
    "ChatResponse",
    "KnowledgeBaseRequest",
    "KnowledgeBaseResponse",
    "DocumentUploadRequest",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "UserResponse",
    "UserSessionCreateRequest",
    "UserSessionResponse",
    "UserStatsResponse",

    # 路由
    "system_router",
    "chat_router",
    "kb_router",
    "tool_router",
    "auth_router",
    "user_router"
]
