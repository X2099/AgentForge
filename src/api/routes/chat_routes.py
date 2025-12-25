# -*- coding: utf-8 -*-
"""
聊天相关API路由
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.store.sqlite import SqliteStore
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.config import SystemConfig
from src.core.agents.agent_manager import AgentManager
from src.knowledge.knowledge_manager import KnowledgeBaseManager
from src.graphs import create_react_graph, create_rag_graph
from ..models import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CHECKPOINT_DB = (BASE_DIR / "data" / "checkpoint.db").as_posix()
STORE_DB = (BASE_DIR / "data" / "store.db").as_posix()

# 创建路由器
router = APIRouter()

# 全局组件（将在应用启动时初始化）
knowledge_base_manager: Optional[KnowledgeBaseManager] = None
system_config: Optional[SystemConfig] = None
mcp_client: Optional[MultiServerMCPClient] = None
agent_manager: Optional[AgentManager] = None


def init_chat_dependencies(kb_manager, sys_conf, mcp_cl, ag_manager):
    """初始化聊天路由的依赖"""
    global knowledge_base_manager, system_config, mcp_client, agent_manager
    knowledge_base_manager = kb_manager
    system_config = sys_conf
    mcp_client = mcp_cl
    agent_manager = ag_manager


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""

    try:
        # 处理用户会话和消息记录
        session_id = request.conversation_id
        user_id = request.user_id
        graph_type = request.mode
        # 如果提供了user_id，创建或更新会话记录
        if user_id and agent_manager:
            if not session_id:
                # 创建新会话
                session_id = agent_manager.create_user_session(
                    user_id=user_id,
                    title=f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    graph_type=graph_type,
                    model_name=request.model
                )
            else:
                # 检查会话是否存在，如果不存在则创建
                try:
                    existing_session = agent_manager.get_user_session(session_id)
                    if not existing_session:
                        # 会话不存在，创建一个新的
                        session_id = agent_manager.create_user_session(
                            user_id=user_id,
                            title=f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            model_name=request.model
                        )
                except Exception as e:
                    logger.error(f"创建会话失败：{e}")
                    raise HTTPException(status_code=500, detail=f"聊天服务暂时不可用: {str(e)}")
        # 获取LLM模型
        llm = system_config.create_client(model=request.model)
        # 创建工作流
        async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
            with SqliteStore.from_conn_string(STORE_DB) as store:
                # 使用RAG对话
                if request.mode == "rag":
                    # 获取知识库
                    kb = knowledge_base_manager.get_knowledge_base(request.knowledge_base_name)
                    graph = create_rag_graph(
                        llm,
                        knowledge_base=kb,
                        checkpointer=checkpointer
                    )
                else:
                    # 获取选中的工具
                    tools = await mcp_client.get_tools()
                    tools_map = {tool.name: tool for tool in tools}
                    selected_tools = []
                    for tool_name in request.tools:
                        tool = tools_map.get(tool_name)
                        if tool:
                            selected_tools.append(tool)
                    graph = create_react_graph(
                        llm,
                        tools=selected_tools,
                        checkpointer=checkpointer,
                        store=store
                    )
                # 准备初始状态
                initial_state = {
                    "messages": [HumanMessage(content=request.query)],
                    "query": request.query
                }
                config = {"configurable": {"thread_id": session_id}}

                # 执行工作流
                try:
                    result = await graph.ainvoke(initial_state, config)
                    response_content = result["messages"][-1].content if result["messages"] else ""
                    sources = result.get('sources', [])

                    for m in result['messages']:
                        m.pretty_print()

                    return ChatResponse(
                        response=response_content,
                        conversation_id=session_id,
                        sources=sources
                    )

                except Exception as e:
                    raise e
                    error_msg = f"工作流执行失败: {str(e)}"
                    raise HTTPException(status_code=500, detail=error_msg)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"聊天服务暂时不可用: {str(e)}")


@router.get("/sessions/{session_id}/messages")
async def get_session_messages_from_checkpointer(session_id: str, limit: int = 100):
    """从checkpointer获取会话消息历史"""
    try:
        async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
            # 从checkpointer加载会话历史
            config = {"configurable": {"thread_id": session_id}}
            checkpoint = await checkpointer.aget(config)
            if not checkpoint:
                return []

            channel_values = checkpoint["channel_values"]
            if "display_messages" in channel_values:
                messages = channel_values.get("display_messages", [])
            else:
                messages = channel_values.get("messages", [])

            # 转换为API响应格式
            response_messages = []
            for i, msg in enumerate(messages[-limit:]):  # 限制数量
                if isinstance(msg, dict):
                    message = msg.get("message")
                    sources = msg.get("sources", [])
                else:
                    message = msg
                    sources = []
                if hasattr(message, "type") and hasattr(message, "content"):
                    response_messages.append({
                        "message_id": f"msg_{i}",
                        "session_id": session_id,
                        "role": message.type,
                        "content": message.content,
                        "model_name": getattr(message, "name", None),
                        "created_at": getattr(message, "timestamp", None),
                        "sources": sources,
                        "metadata": {}
                    })

            return response_messages

    except Exception as e:
        logger.error(f"Error loading messages from checkpointer: {e}")
        raise HTTPException(status_code=500, detail=f"获取消息历史失败: {str(e)}")
