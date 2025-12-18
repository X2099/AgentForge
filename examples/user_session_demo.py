# -*- coding: utf-8 -*-
"""
@File    : user_session_demo.py
@Time    : 2025/12/16
@Desc    : 用户和会话管理API演示
"""
import asyncio
import requests
import json
from datetime import datetime

# API基础URL
API_BASE_URL = "http://localhost:8000"


def test_user_management():
    """测试用户管理功能"""
    print("=== 用户管理测试 ===")

    # 1. 创建用户
    user_data = {
        "username": "test_user",
        "email": "test@example.com",
        "display_name": "测试用户"
    }

    try:
        response = requests.post(f"{API_BASE_URL}/users", json=user_data)
        if response.status_code == 200:
            user = response.json()
            print(f"✅ 创建用户成功: {user['username']} (ID: {user['user_id']})")
            return user['user_id']
        else:
            print(f"❌ 创建用户失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None


def test_user_session_management(user_id):
    """测试会话管理功能"""
    print("\n=== 会话管理测试 ===")

    if not user_id:
        print("❌ 无用户ID，跳过会话测试")
        return None

    # 1. 创建会话
    session_data = {
        "user_id": user_id,
        "title": "测试对话",
        "model_name": "gpt-3.5-turbo",
        "kb_name": "default",
        "tools_config": ["calculator", "web_search"]
    }

    try:
        response = requests.post(f"{API_BASE_URL}/user-sessions", json=session_data)
        if response.status_code == 200:
            session = response.json()
            print(f"✅ 创建会话成功: {session['title']} (ID: {session['session_id']})")
            return session['session_id']
        else:
            print(f"❌ 创建会话失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None


def test_message_management(session_id, user_id):
    """测试消息管理功能"""
    print("\n=== 消息管理测试 ===")

    if not session_id or not user_id:
        print("❌ 无会话ID或用户ID，跳过消息测试")
        return

    # 1. 添加用户消息
    user_message = {
        "session_id": session_id,
        "user_id": user_id,
        "role": "user",
        "content": "你好，请介绍一下Python编程语言"
    }

    try:
        response = requests.post(f"{API_BASE_URL}/user-messages", json=user_message)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 添加用户消息成功: {result['message_id']}")
        else:
            print(f"❌ 添加用户消息失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")

    # 2. 添加助手消息
    assistant_message = {
        "session_id": session_id,
        "user_id": user_id,
        "role": "assistant",
        "content": "Python是一种高级编程语言，以其简洁明了的语法和强大的功能而闻名。",
        "model_name": "gpt-3.5-turbo",
        "sources": [{"source": "wikipedia", "content": "Python is a programming language"}]
    }

    try:
        response = requests.post(f"{API_BASE_URL}/user-messages", json=assistant_message)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 添加助手消息成功: {result['message_id']}")
        else:
            print(f"❌ 添加助手消息失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")


def test_session_retrieval(user_id, session_id):
    """测试会话数据检索"""
    print("\n=== 数据检索测试 ===")

    if not user_id:
        print("❌ 无用户ID，跳过检索测试")
        return

    # 1. 获取用户会话列表
    try:
        response = requests.get(f"{API_BASE_URL}/users/{user_id}/sessions")
        if response.status_code == 200:
            sessions = response.json()
            print(f"✅ 获取用户会话列表成功: {len(sessions)} 个会话")
            for session in sessions:
                print(f"   - {session['title']} ({session['total_messages']} 条消息)")
        else:
            print(f"❌ 获取会话列表失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")

    # 2. 获取单个会话详情
    if session_id:
        try:
            response = requests.get(f"{API_BASE_URL}/user-sessions/{session_id}")
            if response.status_code == 200:
                session = response.json()
                print(f"✅ 获取会话详情成功: {session['title']}")
            else:
                print(f"❌ 获取会话详情失败: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")

    # 3. 获取会话消息历史
    if session_id:
        try:
            response = requests.get(f"{API_BASE_URL}/user-sessions/{session_id}/messages")
            if response.status_code == 200:
                messages = response.json()
                print(f"✅ 获取消息历史成功: {len(messages)} 条消息")
                for msg in messages:
                    print(f"   - {msg['role']}: {msg['content'][:50]}...")
            else:
                print(f"❌ 获取消息历史失败: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")

    # 4. 获取用户统计
    try:
        response = requests.get(f"{API_BASE_URL}/users/{user_id}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ 获取用户统计成功: {stats['total_sessions']} 个会话, {stats['total_messages']} 条消息")
        else:
            print(f"❌ 获取用户统计失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")


def main():
    """主函数"""
    print("🚀 用户和会话管理API演示")
    print("=" * 50)

    # 检查API是否运行
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API服务器未运行，请先启动服务器")
            print("运行命令: python scripts/start_server.py --mode api")
            return
    except Exception as e:
        print(f"❌ 无法连接到API服务器: {str(e)}")
        print("请确保API服务器正在运行在 http://localhost:8000")
        return

    # 运行测试
    user_id = test_user_management()
    session_id = test_user_session_management(user_id)
    test_message_management(session_id, user_id)
    test_session_retrieval(user_id, session_id)

    print("\n" + "=" * 50)
    print("🎉 演示完成！")


if __name__ == "__main__":
    main()
