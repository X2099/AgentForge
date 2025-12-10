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
    history: Optional[List[Dict[str, Any]]] = None
    stream: bool = False
    knowledge_base_name: Optional[str] = "default"
    use_knowledge_base: bool = True
    tools: Optional[List[str]] = None  # 选中的工具名称列表
    model: Optional[str] = None  # 选中的模型名称


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    conversation_id: str
    history: List[Dict[str, Any]]
    sources: Optional[List[Dict[str, Any]]] = None


class KnowledgeBaseRequest(BaseModel):
    """知识库请求"""
    file_paths: Optional[List[str]] = None  # 可选，用于创建时添加文档
    kb_name: str = "default"
    chunk_size: int = 500
    chunk_overlap: int = 50


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    kb_name: str
    document_count: int
    status: str


class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    kb_name: str
    file_paths: List[str]
