# -*- coding: utf-8 -*-
"""
API数据模型定义
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class ChatRequest(BaseModel):
    """聊天请求"""
    query: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None  # 用户ID，用于记录会话和消息
    history: Optional[List[Dict[str, Any]]] = None
    stream: bool = False
    knowledge_base_name: Optional[str] = "default"
    use_knowledge_base: bool = True
    tools: Optional[List[str]] = None  # 选中的工具名称列表
    model: Optional[str] = None  # 选中的模型名称
    mode: Optional[str] = None  # 图类型（agent或rag）


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    conversation_id: str
    sources: Optional[List[Dict[str, Any]]] = None


class KnowledgeBaseRequest(BaseModel):
    """知识库请求"""
    kb_name: str
    kb_desc: str
    splitter_type: str
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedder: dict
    vector_store: dict
    semantic_config: Optional[dict] = None


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    kb_name: str
    document_count: int = 0
    status: str


class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    kb_name: str
    file_paths: List[str]


# ===== 用户和会话相关模型 =====

class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    username: str
    email: Optional[str] = None
    display_name: str
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str
    is_active: bool
    last_login_at: Optional[str] = None


class UserSessionCreateRequest(BaseModel):
    """创建用户会话请求"""
    user_id: str
    title: Optional[str] = None
    model_name: Optional[str] = None
    kb_name: Optional[str] = None
    tools_config: Optional[List[str]] = None
    mode: Optional[str] = None


class UserSessionResponse(BaseModel):
    """用户会话响应"""
    session_id: str
    user_id: str
    title: str
    model_name: Optional[str] = None
    kb_name: Optional[str] = None
    tools_config: List[str] = []
    total_messages: int
    created_at: str
    updated_at: str
    is_active: bool
    metadata: Optional[Dict[str, Any]] = None


class UserStatsResponse(BaseModel):
    """用户统计响应"""
    total_sessions: int
    total_messages: int


# ===== 用户认证相关模型 =====

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str  # 注意：实际应用中密码应该通过安全的方式处理


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    user: Optional[UserResponse] = None
    token: Optional[str] = None
    message: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str  # 注意：实际应用中密码应该通过安全的方式处理
    email: Optional[str] = None
    display_name: Optional[str] = None


class RegisterResponse(BaseModel):
    """注册响应"""
    success: bool
    user: Optional[UserResponse] = None
    message: str
