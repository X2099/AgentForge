# -*- coding: utf-8 -*-
"""
FastAPI应用主入口
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router, init_dependencies
from ..knowledge.kb_manager import KnowledgeBaseManager
from ..config.system_config import SystemConfig
from ..tools.transports import TransportType
from ..tools.mcp_client import MCPClient


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
    app.include_router(router)

    # 初始化全局依赖
    _init_dependencies(app)

    return app


def _init_dependencies(app: FastAPI):
    """初始化全局依赖"""
    # 创建全局组件
    knowledge_base_manager = KnowledgeBaseManager()
    system_config = SystemConfig()
    mcp_client = MCPClient(
        transport_type=TransportType.HTTP,
        transport_config={"url": "http://localhost:8000/mcp"}
    )

    # 初始化路由依赖
    init_dependencies(knowledge_base_manager, system_config, mcp_client)


def run_server(host: str = "0.0.0.0", port: int = 7861):
    """运行服务器"""
    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
