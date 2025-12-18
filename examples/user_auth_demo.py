# -*- coding: utf-8 -*-
"""
@File    : user_auth_demo.py
@Time    : 2025/12/16
@Desc    : 用户认证API演示
"""
import requests
import json

# API基础URL
API_BASE_URL = "http://localhost:8000"


def test_user_registration():
    """测试用户注册功能"""
    print("=== 用户注册测试 ===")

    # 注册新用户
    user_data = {
        "username": "testuser123",
        "password": "testpass123",
        "email": "test@example.com",
        "display_name": "测试用户"
    }

    try:
        response = requests.post(f"{API_BASE_URL}/auth/register", json=user_data)
        print(f"注册请求状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"注册结果: {result}")

            if result.get("success"):
                print("✅ 用户注册成功")
                return result.get("user", {}).get("user_id")
            else:
                print(f"❌ 注册失败: {result.get('message')}")
                return None
        else:
            print(f"❌ 注册请求失败: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None


def test_user_login():
    """测试用户登录功能"""
    print("\n=== 用户登录测试 ===")

    # 使用已注册的用户登录
    login_data = {
        "username": "testuser123",
        "password": "testpass123"
    }

    try:
        response = requests.post(f"{API_BASE_URL}/auth/login", json=login_data)
        print(f"登录请求状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"登录结果: {result}")

            if result.get("success"):
                print("✅ 用户登录成功")
                user = result.get("user", {})
                print(f"用户信息: {user.get('display_name')} (@{user.get('username')})")
                return user.get("user_id")
            else:
                print(f"❌ 登录失败: {result.get('message')}")
                return None
        else:
            print(f"❌ 登录请求失败: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None


def test_user_management(user_id):
    """测试用户管理功能"""
    print(f"\n=== 用户管理测试 (用户ID: {user_id}) ===")

    if not user_id:
        print("❌ 无用户ID，跳过用户管理测试")
        return

    # 获取用户信息
    try:
        response = requests.get(f"{API_BASE_URL}/users/{user_id}")
        if response.status_code == 200:
            user = response.json()
            print("✅ 获取用户信息成功")
            print(f"用户名: {user.get('username')}")
            print(f"显示名称: {user.get('display_name')}")
            print(f"邮箱: {user.get('email')}")
            print(f"创建时间: {user.get('created_at')}")
        else:
            print(f"❌ 获取用户信息失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")

    # 用户登录（更新最后登录时间）
    try:
        response = requests.post(f"{API_BASE_URL}/users/{user_id}/login")
        if response.status_code == 200:
            print("✅ 用户登录时间更新成功")
        else:
            print(f"❌ 更新登录时间失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")


def test_demo_user():
    """测试演示用户登录"""
    print("\n=== 演示用户测试 ===")

    # 尝试使用演示账号登录（如果存在的话）
    demo_data = {
        "username": "demo",
        "password": "demo"
    }

    try:
        response = requests.post(f"{API_BASE_URL}/auth/login", json=demo_data)
        print(f"演示用户登录状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 演示用户登录成功")
                return result.get("user", {}).get("user_id")
            else:
                print("ℹ️ 演示用户不存在或密码错误")
                return None
        else:
            print(f"❌ 演示用户登录失败: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None


def main():
    """主函数"""
    print("AgentForge 用户认证API演示")
    print("=" * 50)

    # 检查API是否运行
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API服务器未运行")
            print("请先运行: python scripts/start_server.py --mode api")
            return
    except Exception as e:
        print(f"❌ 无法连接到API服务器: {str(e)}")
        print("请确保API服务器在 http://localhost:8000 运行")
        return

    # 测试演示用户
    demo_user_id = test_demo_user()

    # 如果演示用户不存在，注册新用户
    if not demo_user_id:
        user_id = test_user_registration()
    else:
        user_id = demo_user_id

    # 测试登录
    if not demo_user_id:  # 如果不是演示用户，需要登录
        login_user_id = test_user_login()
        if login_user_id:
            user_id = login_user_id

    # 测试用户管理
    if user_id:
        test_user_management(user_id)

    print("\n" + "=" * 50)
    print("🎉 认证API演示完成！")
    print("\n💡 Web界面使用说明:")
    print("1. 启动Streamlit: streamlit run src/webui/streamlit_app.py")
    print("2. 在侧边栏点击 '登录' 或 '注册' 按钮")
    print("3. 输入用户名和密码进行认证")
    print("4. 认证成功后即可使用对话功能")


if __name__ == "__main__":
    main()
