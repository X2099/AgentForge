# -*- coding: utf-8 -*-
"""
用户认证相关API路由
"""
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.core.agents.agent_manager import AgentManager
from ..models import (
    LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
    UserResponse
)

# 创建路由器
router = APIRouter()

# 全局组件（将在应用启动时初始化）
agent_manager: Optional[AgentManager] = None


def init_auth_dependencies(ag_manager):
    """初始化认证路由的依赖"""
    global agent_manager
    agent_manager = ag_manager


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    try:
        if not request.username or not request.password:
            return LoginResponse(
                success=False,
                message="用户名和密码不能为空"
            )

        if not agent_manager:
            return LoginResponse(
                success=False,
                message="认证服务不可用"
            )

        # 验证用户名和密码
        user = agent_manager.verify_password(request.username, request.password)
        if user:
            # 更新登录时间
            agent_manager.update_user_login(user["user_id"])

            # 创建响应时移除密码哈希
            user_response_data = user.copy()
            user_response_data.pop('password_hash', None)

            return LoginResponse(
                success=True,
                user=UserResponse(**user_response_data),
                message="登录成功"
            )

        return LoginResponse(
            success=False,
            message="用户名或密码错误"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/auth/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        if not request.username or not request.password:
            return RegisterResponse(
                success=False,
                message="用户名和密码不能为空"
            )

        if not agent_manager:
            return RegisterResponse(
                success=False,
                message="注册服务不可用"
            )

        # 检查用户名是否已存在
        if agent_manager.get_user_by_username(request.username):
            return RegisterResponse(
                success=False,
                message="用户名已存在"
            )

        # 创建用户
        user_id = agent_manager.create_user(
            username=request.username,
            password=request.password,
            email=request.email,
            display_name=request.display_name or request.username
        )

        user = agent_manager.get_user(user_id)
        if user:
            # 创建响应时移除密码哈希
            user_response_data = user.copy()
            user_response_data.pop('password_hash', None)

            return RegisterResponse(
                success=True,
                user=UserResponse(**user_response_data),
                message="注册成功"
            )
        else:
            return RegisterResponse(
                success=False,
                message="注册失败，请稍后重试"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")
