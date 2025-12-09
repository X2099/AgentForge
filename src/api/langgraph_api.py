# -*- coding: utf-8 -*-
"""
@File    : langgraph_api.py
@Time    : 2025/12/9 14:41
@Desc    : 
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

from ..workflows.rag_workflow import create_rag_workflow
from ..workflows.conversation_workflow import create_conversation_workflow
from ..knowledge.kb_manager import KnowledgeBaseManager
from ..llm.config.llm_config import LLMConfig
from ..tools.transports import TransportType
from ..tools.mcp_client import MCPClient

app = FastAPI(title="LangGraph-ChatChat API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局组件
knowledge_base_manager = KnowledgeBaseManager()
llm_config = LLMConfig()
mcp_client = MCPClient(
    transport_type=TransportType.HTTP,
    transport_config={"url": "http://localhost:8000/mcp"}
)


class ChatRequest(BaseModel):
    """聊天请求（对标Langchain-Chatchat）"""
    query: str
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    stream: bool = False
    knowledge_base_name: Optional[str] = "default"
    use_knowledge_base: bool = True


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    conversation_id: str
    history: List[Dict[str, Any]]
    sources: Optional[List[Dict[str, Any]]] = None


class KnowledgeBaseRequest(BaseModel):
    """知识库请求"""
    file_paths: List[str]
    kb_name: str = "default"
    chunk_size: int = 500
    chunk_overlap: int = 50


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    kb_name: str
    document_count: int
    status: str


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    # 初始化组件
    await mcp_client.connect()
    await mcp_client.initialize()


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "LangGraph-ChatChat",
        "version": "1.0.0",
        "endpoints": [
            "/chat",
            "/knowledge_base/create",
            "/knowledge_base/search",
            "/health"
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口（对标Langchain-Chatchat的对话接口）"""
    try:
        # 获取知识库
        kb = None
        if request.use_knowledge_base:
            kb = knowledge_base_manager.get_knowledge_base(request.knowledge_base_name)

        # 获取LLM
        llm = llm_config.create_client()

        # 创建工作流
        if request.use_knowledge_base and kb:
            # 使用RAG工作流
            workflow = create_rag_workflow(kb)
            initial_state = {"query": request.query}
        else:
            # 使用普通对话工作流
            workflow = create_conversation_workflow(llm, knowledge_base=kb)

            # 准备消息
            messages = []
            if request.history:
                messages.extend(request.history)
            messages.append({"role": "user", "content": request.query})

            initial_state = {
                "messages": messages,
                "query": request.query,
                "knowledge_base_enabled": request.use_knowledge_base
            }

        # 执行工作流
        result = await workflow.ainvoke(initial_state)

        # 生成响应
        response = ChatResponse(
            response=result.get("answer") or result.get("response", ""),
            conversation_id=request.conversation_id or "new_conversation",
            history=result.get("messages", []),
            sources=result.get("sources")
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge_base/create", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(request: KnowledgeBaseRequest):
    """创建知识库（对标Langchain-Chatchat的知识库管理）"""
    try:
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

        # 添加文档
        stats = knowledge_base_manager.bulk_add_documents(
            kb_name=request.kb_name,
            file_paths=request.file_paths
        )

        return KnowledgeBaseResponse(
            kb_name=request.kb_name,
            document_count=stats.get("valid_chunks", 0),
            status="created"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge_base/list")
async def list_knowledge_bases():
    """列出知识库"""
    try:
        kbs = knowledge_base_manager.list_knowledge_bases()
        return {"knowledge_bases": kbs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge_base/search")
async def search_knowledge_base(kb_name: str, query: str, k: int = 5):
    """搜索知识库"""
    try:
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


@app.get("/tools/list")
async def list_tools():
    """列出可用工具"""
    try:
        tools = await mcp_client.list_tools()
        return {"tools": [t.dict() for t in tools]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/call")
async def call_tool(tool_name: str, arguments: Dict[str, Any]):
    """调用工具"""
    try:
        result = await mcp_client.call_tool_simple(tool_name, arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861)
