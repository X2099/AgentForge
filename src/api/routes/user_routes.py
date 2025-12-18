# -*- coding: utf-8 -*-
"""
用户和会话管理相关API路由
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, List

from src.core.agents.agent_manager import AgentManager
from ..models import (
    UserResponse,
    UserSessionCreateRequest, UserSessionResponse,
    UserStatsResponse
)

# 创建路由器
router = APIRouter()

# 全局组件（将在应用启动时初始化）
agent_manager: Optional[AgentManager] = None


def init_user_dependencies(ag_manager):
    """初始化用户路由的依赖"""
    global agent_manager
    agent_manager = ag_manager


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """获取用户信息"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="用户管理功能未启用")

    try:
        user = agent_manager.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        return UserResponse(**user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/touch")
async def user_touch(user_id: str):
    """更新用户最后活动时间"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="用户管理功能未启用")

    try:
        agent_manager.update_user_login(user_id)
        return {"message": "用户活动已更新", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-sessions", response_model=UserSessionResponse)
async def create_user_session(request: UserSessionCreateRequest):
    """创建用户会话"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="会话管理功能未启用")

    try:
        session_id = agent_manager.create_user_session(
            user_id=request.user_id,
            title=request.title,
            model_name=request.model_name,
            kb_name=request.kb_name,
            graph_type=request.mode,
            tools_config=request.tools_config
        )

        session = agent_manager.get_user_session(session_id)
        if not session:
            raise HTTPException(status_code=500, detail="创建会话失败")

        return UserSessionResponse(**session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/sessions", response_model=List[UserSessionResponse])
async def get_user_sessions(user_id: str, mode: str, limit: int = 50):
    """获取用户的会话列表"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="会话管理功能未启用")

    try:
        sessions = agent_manager.get_user_sessions(user_id, mode, limit)
        return [UserSessionResponse(**session) for session in sessions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-sessions/{session_id}", response_model=UserSessionResponse)
async def get_user_session(session_id: str):
    """获取单个会话详情"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="会话管理功能未启用")

    try:
        session = agent_manager.get_user_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        return UserSessionResponse(**session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/user-sessions/{session_id}")
async def update_user_session(session_id: str, title: Optional[str] = None):
    """更新用户会话"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="会话管理功能未启用")

    try:
        agent_manager.update_user_session(session_id, title=title)
        return {"message": "会话更新成功", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user-sessions/{session_id}")
async def delete_user_session(session_id: str):
    """删除用户会话"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="会话管理功能未启用")

    try:
        agent_manager.delete_user_session(session_id)
        return {"message": "会话删除成功", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(user_id: str):
    """获取用户统计信息"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="统计功能未启用")

    try:
        # 由于消息存储在checkpointer中，我们只返回会话统计
        conn = agent_manager.db_conn
        cursor = conn.cursor()

        # 总会话数
        cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE user_id = ? AND is_active = 1", (user_id,))
        total_sessions = cursor.fetchone()[0]

        # 消息数量无法精确统计，因为存储在checkpointer中
        # 返回估算值或0
        return UserStatsResponse(
            total_sessions=total_sessions,
            total_messages=0  # 消息数量现在由checkpointer管理
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
