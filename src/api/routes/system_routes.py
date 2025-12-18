# -*- coding: utf-8 -*-
"""
系统基础API路由
"""
from fastapi import APIRouter, HTTPException

# 创建路由器
router = APIRouter()

# 全局组件（将在应用启动时初始化）
knowledge_base_manager = None
system_config = None


def init_system_dependencies(kb_manager, sys_conf):
    """初始化系统路由的依赖"""
    global knowledge_base_manager, system_config
    knowledge_base_manager = kb_manager
    system_config = sys_conf


@router.get("/")
async def root():
    """根路径"""
    return {
        "service": "LangGraph-ChatChat",
        "version": "1.0.0",
        "endpoints": [
            "/chat",
            "/knowledge_base/create",
            "/knowledge_base/upload_documents",
            "/knowledge_base/search",
            "/knowledge_base/list",
            "/knowledge_base/{kb_name}/history",
            "/knowledge_base/{kb_name}/search-history",
            "/knowledge_base/{kb_name} (DELETE)",
            "/models/list",
            "/vector-stores/list",
            "/embedders/list",
            "/tools/list",
            "/database/stats",
            "/health"
        ]
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@router.get("/models/list")
async def list_models():
    """列出可用模型"""
    try:
        if not system_config:
            raise HTTPException(status_code=500, detail="系统配置未初始化")

        # 从系统配置中获取可用模型
        available_models = []

        # 获取所有提供商的模型
        providers = system_config.config.get("providers", {})
        for provider_name, provider_config in providers.items():
            model_name = provider_config.get("model_name") or provider_config.get("default_model")
            if model_name:
                available_models.append({
                    "name": model_name,
                    "provider": provider_name,
                    "display_name": f"{model_name} ({provider_name})"
                })

        return {"models": available_models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector-stores/list")
async def list_vector_stores():
    """列出可用向量存储类型"""
    try:
        if not system_config:
            raise HTTPException(status_code=500, detail="系统配置未初始化")

        vector_store_types = system_config.get_vector_stores_config()
        return {"vector_stores": vector_store_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/embedders/list")
async def list_embedders():
    """列出可用嵌入器类型"""
    try:
        if not system_config:
            raise HTTPException(status_code=500, detail="系统配置未初始化")

        embedders = system_config.get_embedders_config()

        # 为每个嵌入器添加模型列表
        for embedder in embedders:
            embedder_type = embedder["type"]
            models = system_config.get_embedder_models(embedder_type)
            embedder["models"] = models

        return {"embedders": embedders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/stats")
async def get_database_stats():
    """获取数据库统计信息"""
    try:
        if not knowledge_base_manager or not hasattr(knowledge_base_manager, 'db') or not knowledge_base_manager.db:
            raise HTTPException(status_code=500, detail="数据库功能未启用")

        stats = knowledge_base_manager.db.get_database_stats()
        return {"database_stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
