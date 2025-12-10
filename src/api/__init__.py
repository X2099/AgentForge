# -*- coding: utf-8 -*-
"""
API模块 - 提供RESTful API服务
"""

from .main import create_app, run_server
from .models import (
    ChatRequest, ChatResponse,
    KnowledgeBaseRequest, KnowledgeBaseResponse,
    DocumentUploadRequest
)
from .routes import router

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

    # 路由
    "router"
]
