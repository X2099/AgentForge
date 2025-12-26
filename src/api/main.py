# -*- coding: utf-8 -*-
"""
FastAPI应用主入口
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient

from .routes import (
    system_router, init_system_dependencies,
    chat_router, init_chat_dependencies,
    kb_router, init_kb_dependencies,
    tool_router, init_tool_dependencies,
    auth_router, init_auth_dependencies,
    user_router, init_user_dependencies
)
from ..knowledge.knowledge_manager import KnowledgeBaseManager
from ..config import SystemConfig, mcp_servers_config
from ..core.agents.agent_manager import AgentManager


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(title="LangGraph-ChatChat API", version="1.0.0")

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 包含路由
    app.include_router(system_router, tags=["system"])
    app.include_router(chat_router, tags=["chat"])
    app.include_router(kb_router, tags=["knowledge_base"])
    app.include_router(tool_router, tags=["mcp"])
    app.include_router(auth_router, tags=["auth"])
    app.include_router(user_router, tags=["user"])

    # 初始化全局依赖
    _init_dependencies(app)

    return app


def _init_dependencies(app: FastAPI):
    """初始化全局依赖"""
    # 创建全局组件
    knowledge_base_manager = KnowledgeBaseManager()
    system_config = SystemConfig()
    mcp_client = MultiServerMCPClient(mcp_servers_config)
    agent_manager = AgentManager()  # 创建智能体管理器

    # 初始化路由依赖
    init_system_dependencies(knowledge_base_manager, system_config)
    init_chat_dependencies(knowledge_base_manager, system_config, mcp_client, agent_manager)
    init_kb_dependencies(knowledge_base_manager)
    init_tool_dependencies(mcp_client)
    init_auth_dependencies(agent_manager)
    init_user_dependencies(agent_manager)


def run_server(host: str = "0.0.0.0", port: int = 7861):
    """运行服务器"""
    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
