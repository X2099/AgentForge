# -*- coding: utf-8 -*-
"""
知识库管理相关API路由
"""
from typing import Optional
from fastapi import APIRouter, HTTPException

from src.knowledge.kb_manager import KnowledgeBaseManager
from ..models import (
    KnowledgeBaseRequest, KnowledgeBaseResponse,
    DocumentUploadRequest
)

# 创建路由器
router = APIRouter()

# 全局组件（将在应用启动时初始化）
knowledge_base_manager: Optional[KnowledgeBaseManager] = None


def init_kb_dependencies(kb_manager):
    """初始化知识库路由的依赖"""
    global knowledge_base_manager
    knowledge_base_manager = kb_manager


@router.post("/knowledge_base/create", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(request: KnowledgeBaseRequest):
    """创建知识库（对标Langchain-Chatchat的知识库管理）"""
    try:
        if not knowledge_base_manager:
            raise HTTPException(status_code=500, detail="知识库管理器未初始化")

        # 创建或获取知识库配置
        kb_config = {
            "name": request.kb_name,
            "chunk_size": request.chunk_size,
            "chunk_overlap": request.chunk_overlap,
            "embedder": {
                "embedder_type": "bge",
                "model_name": "BAAI/bge-small-zh-v1.5"
            },
            "vector_store": {
                "store_type": "chroma",
                "collection_name": request.kb_name
            }
        }

        # 创建知识库
        kb = knowledge_base_manager.create_knowledge_base(kb_config)

        # 如果提供了文件路径，则添加文档
        document_count = 0
        if request.file_paths:
            stats = knowledge_base_manager.bulk_add_documents(
                kb_name=request.kb_name,
                file_paths=request.file_paths
            )
            document_count = stats.get("valid_chunks", 0)

        return KnowledgeBaseResponse(
            kb_name=request.kb_name,
            document_count=document_count,
            status="created"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge_base/upload_documents")
async def upload_documents_to_knowledge_base(request: DocumentUploadRequest):
    """上传文档到现有知识库"""
    try:
        if not knowledge_base_manager:
            raise HTTPException(status_code=500, detail="知识库管理器未初始化")

        # 检查知识库是否存在
        kb = knowledge_base_manager.get_knowledge_base(request.kb_name)
        if not kb:
            raise HTTPException(status_code=404, detail=f"知识库 '{request.kb_name}' 不存在")

        # 添加文档
        stats = knowledge_base_manager.bulk_add_documents(
            kb_name=request.kb_name,
            file_paths=request.file_paths
        )

        return {
            "kb_name": request.kb_name,
            "processed_files": stats.get("processed_files", 0),
            "failed_files": stats.get("failed_files", 0),
            "total_chunks": stats.get("total_chunks", 0),
            "valid_chunks": stats.get("valid_chunks", 0),
            "status": "uploaded"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge_base/list")
async def list_knowledge_bases():
    """列出知识库"""
    try:
        if not knowledge_base_manager:
            raise HTTPException(status_code=500, detail="知识库管理器未初始化")

        kbs = []
        kb_list = knowledge_base_manager.list_knowledge_bases()

        for kb in kb_list:
            kb_data = {
                "name": kb["name"],
                "description": kb.get("description", ""),
                "document_count": kb.get("document_count", 0),
                "last_updated": kb.get("last_updated")
            }

            # 如果使用数据库，获取更详细的统计信息
            if hasattr(knowledge_base_manager, 'db') and knowledge_base_manager.db:
                stats = knowledge_base_manager.db.get_statistics(kb["name"])
                if stats:
                    kb_data.update({
                        "document_count": stats.get("document_count", 0),
                        "total_chunks": stats.get("total_chunks", 0),
                        "vector_count": stats.get("vector_count", 0),
                        "last_updated": stats.get("last_updated")
                    })

            kbs.append(kb_data)

        return {"knowledge_bases": kbs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge_base/search")
async def search_knowledge_base(kb_name: str, query: str, k: int = 5):
    """搜索知识库"""
    try:
        if not knowledge_base_manager:
            raise HTTPException(status_code=500, detail="知识库管理器未初始化")

        # 使用manager的search方法，这样会记录搜索历史
        results = knowledge_base_manager.search(kb_name, query, k=k)

        # 格式化结果
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc.content,
                "source": doc.metadata.get("source", ""),
                "score": doc.metadata.get("similarity_score", 0)
            })

        return {
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge_base/{kb_name}")
async def delete_knowledge_base(kb_name: str, delete_data: bool = False):
    """删除知识库"""
    try:
        if not knowledge_base_manager:
            raise HTTPException(status_code=500, detail="知识库管理器未初始化")

        # 检查知识库是否存在
        if kb_name not in knowledge_base_manager.knowledge_bases:
            raise HTTPException(status_code=404, detail=f"知识库 '{kb_name}' 不存在")

        # 执行删除
        knowledge_base_manager.delete_knowledge_base(kb_name, delete_data)

        return {
            "message": f"知识库 '{kb_name}' 已成功删除",
            "delete_data": delete_data
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge_base/{kb_name}/history")
async def get_knowledge_base_history(kb_name: str, limit: int = 50):
    """获取知识库操作历史"""
    try:
        if not knowledge_base_manager or not hasattr(knowledge_base_manager, 'db') or not knowledge_base_manager.db:
            raise HTTPException(status_code=500, detail="数据库功能未启用")

        # 检查知识库是否存在
        if kb_name not in knowledge_base_manager.knowledge_bases:
            raise HTTPException(status_code=404, detail=f"知识库 '{kb_name}' 不存在")

        operations = knowledge_base_manager.db.get_operation_history(kb_name, limit)
        return {"operations": operations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge_base/{kb_name}/search-history")
async def get_knowledge_base_search_history(kb_name: str, limit: int = 50):
    """获取知识库搜索历史"""
    try:
        if not knowledge_base_manager or not hasattr(knowledge_base_manager, 'db') or not knowledge_base_manager.db:
            raise HTTPException(status_code=500, detail="数据库功能未启用")

        # 检查知识库是否存在
        if kb_name not in knowledge_base_manager.knowledge_bases:
            raise HTTPException(status_code=404, detail=f"知识库 '{kb_name}' 不存在")

        searches = knowledge_base_manager.db.get_search_history(kb_name, limit)
        return {"searches": searches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
