# -*- coding: utf-8 -*-
"""
API路由定义
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any

from .models import (
    ChatRequest, ChatResponse,
    KnowledgeBaseRequest, KnowledgeBaseResponse,
    DocumentUploadRequest
)
from ..workflows.rag_workflow import create_rag_workflow
from ..workflows.conversation_workflow import create_conversation_workflow
from ..knowledge.kb_manager import KnowledgeBaseManager
from ..config.system_config import SystemConfig
from ..tools.mcp_client import MCPClient

# 创建路由器
router = APIRouter()

# 全局组件（将在应用启动时初始化）
knowledge_base_manager: Optional[KnowledgeBaseManager] = None
system_config: Optional[SystemConfig] = None
mcp_client: Optional[MCPClient] = None


def init_dependencies(kb_manager: KnowledgeBaseManager,
                      sys_conf: SystemConfig,
                      mcp_cl: MCPClient):
    """初始化依赖"""
    global knowledge_base_manager, system_config, mcp_client
    knowledge_base_manager = kb_manager
    system_config = sys_conf
    mcp_client = mcp_cl


@router.on_event("startup")
async def startup_event():
    """启动事件"""
    if mcp_client:
        # 初始化组件
        await mcp_client.connect()
        await mcp_client.initialize()


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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    try:
        from langchain_core.messages import HumanMessage

        # 获取知识库
        kb = None
        if request.use_knowledge_base and knowledge_base_manager:
            kb = knowledge_base_manager.get_knowledge_base(request.knowledge_base_name)

        # 获取LLM客户端
        llm_client = system_config.create_client(model=request.model) if system_config else None

        # 获取选中的工具
        selected_tools = None
        if request.tools and knowledge_base_manager:
            from ..tools.tool_manager import get_tool_manager
            tool_manager = get_tool_manager()
            selected_tools = []
            for tool_name in request.tools:
                tool = tool_manager.get_tool(tool_name)
                if tool:
                    selected_tools.append(tool)

        # 创建工作流
        if request.use_knowledge_base and kb:
            # 使用RAG工作流（暂时不支持工具）
            workflow = create_rag_workflow(llm_client, kb)
            # 准备初始状态
            initial_state = {
                "messages": [HumanMessage(content=request.query)],
                "query": request.query,
                "thread_id": request.conversation_id or "default",
                "session_id": request.conversation_id,
                "current_step": "start",
                "next_node": None,
                "documents": [],
                "context": None,
                "answer": None,
                "sources": []
            }
        else:
            # 使用普通对话工作流
            workflow = create_conversation_workflow(llm_client, knowledge_base=kb, tools=selected_tools)

            # 准备消息
            messages = []
            if request.history:
                for msg in request.history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        from langchain_core.messages import AIMessage
                        messages.append(AIMessage(content=content))

            # 添加当前用户消息
            messages.append(HumanMessage(content=request.query))

            initial_state = {
                "messages": messages,
                "query": request.query,
                "thread_id": request.conversation_id or "default",
                "session_id": request.conversation_id,
                "current_step": "start",
                "next_node": None,
                "knowledge_base_enabled": request.use_knowledge_base,
                "retrieved_context": None,
                "response": None
            }

        # 执行工作流
        result = await workflow.ainvoke(initial_state)

        # 提取响应
        response_text = result.get("answer") or result.get("response", "")
        if not response_text:
            # 从messages中提取最后一条AI消息
            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    response_text = last_msg.content
                elif isinstance(last_msg, dict):
                    response_text = last_msg.get("content", "")

        # 格式化历史消息
        history = []
        for msg in result.get("messages", []):
            if hasattr(msg, "content"):
                history.append({
                    "role": "assistant" if hasattr(msg, "type") and msg.type == "ai" else "user",
                    "content": msg.content
                })
            elif isinstance(msg, dict):
                history.append(msg)

        # 生成响应
        response = ChatResponse(
            response=response_text or "未收到响应",
            conversation_id=request.conversation_id or "new_conversation",
            history=history,
            sources=result.get("sources")
        )

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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

        kb = knowledge_base_manager.get_knowledge_base(kb_name)
        if not kb:
            raise HTTPException(status_code=404, detail=f"知识库 {kb_name} 不存在")

        results = kb.search(query, k=k)

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


@router.get("/tools/list")
async def list_tools():
    """列出可用工具"""
    try:
        if not mcp_client:
            raise HTTPException(status_code=500, detail="MCP客户端未初始化")

        tools = await mcp_client.list_tools()
        return {"tools": [t.dict() for t in tools]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/call")
async def call_tool(tool_name: str, arguments: Dict[str, Any]):
    """调用工具"""
    try:
        if not mcp_client:
            raise HTTPException(status_code=500, detail="MCP客户端未初始化")

        result = await mcp_client.call_tool_simple(tool_name, arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
async def get_search_history(kb_name: str, limit: int = 100):
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
