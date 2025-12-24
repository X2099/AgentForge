# -*- coding: utf-8 -*-
"""
@File    : streamlit_app.py
@Time    : 2025/12/9 14:43
@Desc    : LangGraph-AgentForge 主应用
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import requests
import streamlit as st

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.api_compat import list_knowledge_bases, list_tools
from src.webui.knowledge_base_ui import main as kb_main
from src.webui.chat_ui import main as chat_main
from src.webui.tools_ui import main as tools_main
from src.webui import API_BASE_URL


class SessionManager:
    """会话状态管理器"""

    DEFAULT_STATE = {
        # 对话相关
        "conversation_history": [],
        "current_kb": "",

        # 工具相关
        "available_tools": [],

        # 知识库相关
        "knowledge_bases": [],

        # 模型相关
        "available_models": [],

        # 用户认证相关
        "user_authenticated": False,
        "current_user": None,
        "user_token": None,
        "show_auth_modal": False,
        "auth_mode": "login",  # "login" or "register"

        # UI状态
        "sidebar_expanded": True,
        "current_page": "智能体对话",

        # 系统状态
        "api_health": None,
        "last_update": None
    }

    @classmethod
    def initialize_session_state(cls):
        """初始化会话状态"""
        for key, default_value in cls.DEFAULT_STATE.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @classmethod
    def reset_conversation(cls):
        """重置对话历史"""
        st.session_state.conversation_history = []
        st.session_state.current_kb = "default"

    @classmethod
    def update_knowledge_bases(cls, kbs: list):
        """更新知识库列表"""
        st.session_state.knowledge_bases = kbs
        st.session_state.last_update = asyncio.get_event_loop().time() if asyncio.get_event_loop() else None

    @classmethod
    def update_tools(cls, tools: list):
        """更新工具列表"""
        st.session_state.available_tools = tools

    @classmethod
    def update_models(cls, models: list):
        """更新模型列表"""
        st.session_state.available_models = models

    @classmethod
    def login_user(cls, user_data: dict, token: str = None):
        """用户登录"""
        st.session_state.user_authenticated = True
        st.session_state.current_user = user_data
        st.session_state.user_token = token
        # 保存登录状态到本地文件
        cls._save_login_state(user_data, token)

    @classmethod
    def logout_user(cls):
        """用户登出"""
        st.session_state.user_authenticated = False
        st.session_state.current_user = None
        st.session_state.user_token = None
        # 清除保存的登录状态
        cls._clear_login_state()
        # 清除会话相关数据
        cls.reset_conversation()

    @classmethod
    def _save_login_state(cls, user_data: dict, token: str = None):
        """保存登录状态到本地文件"""
        try:
            import json
            import os
            from pathlib import Path

            # 创建数据目录
            data_dir = Path("./data/user_sessions")
            data_dir.mkdir(parents=True, exist_ok=True)

            # 保存登录状态
            state_data = {
                "user_authenticated": True,
                "current_user": user_data,
                "user_token": token,
                "login_time": str(datetime.now())
            }

            state_file = data_dir / "login_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"保存登录状态失败: {e}")

    @classmethod
    def _clear_login_state(cls):
        """清除保存的登录状态"""
        try:
            from pathlib import Path
            state_file = Path("./data/user_sessions/login_state.json")
            if state_file.exists():
                state_file.unlink()
        except Exception as e:
            print(f"清除登录状态失败: {e}")

    @classmethod
    def _load_login_state(cls):
        """从本地文件加载登录状态"""
        try:
            import json
            from pathlib import Path
            from datetime import datetime, timedelta

            state_file = Path("./data/user_sessions/login_state.json")
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)

                # 验证登录状态是否仍然有效
                if state_data.get("user_authenticated"):
                    # 检查登录时间是否过期（7天）
                    login_time_str = state_data.get("login_time")
                    if login_time_str:
                        try:
                            login_time = datetime.fromisoformat(login_time_str)
                            if datetime.now() - login_time > timedelta(days=7):
                                # 登录状态过期，删除文件
                                state_file.unlink()
                                return None
                        except:
                            # 时间解析失败，视为过期
                            state_file.unlink()
                            return None

                    return state_data

        except Exception as e:
            print(f"加载登录状态失败: {e}")

        return None

    @classmethod
    def restore_login_state(cls):
        """恢复登录状态（在应用启动时调用）"""
        state_data = cls._load_login_state()
        if state_data:
            st.session_state.user_authenticated = state_data.get("user_authenticated", False)
            st.session_state.current_user = state_data.get("current_user")
            st.session_state.user_token = state_data.get("user_token")
            # 标记这是从文件恢复的登录状态
            st.session_state._restored_from_file = True
            return True
        return False

    @classmethod
    def is_authenticated(cls) -> bool:
        """检查用户是否已认证"""
        return st.session_state.get("user_authenticated", False)

    @classmethod
    def set_current_page(cls, page: str):
        """设置当前页面"""
        st.session_state.current_page = page


class APIManager:
    """API管理器"""

    @staticmethod
    async def load_knowledge_bases() -> bool:
        """加载知识库列表"""
        try:
            kbs_data = await list_knowledge_bases()
            st.info(kbs_data)
            SessionManager.update_knowledge_bases(kbs_data.get("knowledge_bases", []))
            return True
        except Exception as e:
            st.error(f"加载知识库失败: {str(e)}")
            SessionManager.update_knowledge_bases([])
            return False

    @staticmethod
    async def load_tools() -> bool:
        """加载工具列表"""
        try:
            tools_data = await list_tools()
            SessionManager.update_tools(tools_data.get("tools", []))
            return True
        except Exception as e:
            st.error(f"加载工具失败: {str(e)}")
            SessionManager.update_tools([])
            return False

    @staticmethod
    async def load_models() -> bool:
        """加载模型列表"""
        try:
            # 调用模型列表端点
            response = requests.get(f"{API_BASE_URL}/models/list", timeout=5)

            if response.status_code == 200:
                models_data = response.json()
                SessionManager.update_models(models_data.get("models", []))
                return True
            else:
                st.error(f"获取模型列表失败 (状态码: {response.status_code})")
                SessionManager.update_models([])
                return False

        except Exception as e:
            st.error(f"加载模型失败: {str(e)}")
            SessionManager.update_models([])
            return False

    @staticmethod
    async def check_api_health() -> bool:
        """检查API健康状态"""
        try:
            # 调用专门的健康检查端点
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)

            if response.status_code == 200:
                try:
                    health_data = response.json()
                    if health_data.get("status") == "healthy":
                        st.session_state.api_health = True
                        return True
                except ValueError:
                    # 如果响应不是有效的JSON，可能是服务器错误
                    pass

            # 如果状态码不是200或者响应格式不正确，认为服务不健康
            st.session_state.api_health = False
            return False

        except requests.exceptions.ConnectionError:
            # 连接失败 - 服务器没有启动
            st.session_state.api_health = False
            return False
        except requests.exceptions.Timeout:
            # 请求超时
            st.session_state.api_health = False
            return False
        except Exception as e:
            # 其他错误
            print(f"API健康检查失败: {str(e)}")
            st.session_state.api_health = False
            return False


class UIManager:
    """UI管理器"""

    @staticmethod
    def setup_page_config():
        """设置页面配置"""
        st.set_page_config(
            page_title="LangGraph-AgentForge",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': 'https://github.com/X2099/AgentForge',
                'Report a bug': 'https://github.com/X2099/AgentForge/issues',
                'About': '''
                    ## AgentForge
                    基于LangGraph实现的智能对话系统
                    - 🤖 智能对话
                    - 📚 知识库管理
                    - 🔧 工具集成
                '''
            }
        )

    @staticmethod
    def render_user_auth_section():
        """渲染用户认证区域"""
        if SessionManager.is_authenticated():
            # 已登录用户显示用户信息和登出按钮
            user = st.session_state.current_user
            with st.container():
                col1, col2 = st.columns([2.2, 1.8])
                with col1:
                    st.markdown(f"**👤 {user.get('display_name', user.get('username', '用户'))}**")
                    st.caption(f"@{user.get('username', '')}")
                with col2:
                    if st.button("🚪登出", key="logout_btn", use_container_width=True):
                        SessionManager.logout_user()
                        st.success("已成功登出")
                        st.rerun()

            # 显示自动登录提示（如果是从本地恢复的）
            if hasattr(st.session_state, '_restored_from_file') and st.session_state._restored_from_file:
                # 只显示一次
                st.session_state._restored_from_file = False
        else:
            # 未登录用户显示登录/注册按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔐 登录", key="login_btn", use_container_width=True, type="primary"):
                    st.session_state.show_auth_modal = True
                    st.session_state.auth_mode = "login"
                    st.rerun()
            with col2:
                if st.button("📝 注册", key="register_btn", use_container_width=True):
                    st.session_state.show_auth_modal = True
                    st.session_state.auth_mode = "register"
                    st.rerun()

    @staticmethod
    def render_auth_modal():
        """渲染认证模态框"""
        if not st.session_state.get("show_auth_modal", False):
            return

        with st.container():
            # 关闭按钮
            col1, col2, col3 = st.columns([1, 2, 1])
            with col3:
                if st.button("✕", key="close_auth_modal"):
                    st.session_state.show_auth_modal = False
                    st.rerun()

            # 标题
            title = "用户登录" if st.session_state.auth_mode == "login" else "用户注册"
            st.markdown(f"### {title}")

            # 表单
            with st.form(key=f"{st.session_state.auth_mode}_form"):
                username = st.text_input("用户名", key="auth_username")
                password = st.text_input("密码", type="password", key="auth_password")

                if st.session_state.auth_mode == "register":
                    email = st.text_input("邮箱（可选）", key="auth_email")
                    display_name = st.text_input("显示名称", key="auth_display_name")

                submitted = st.form_submit_button(title)

                if submitted:
                    UIManager.handle_auth_submission()

            # 切换模式
            if st.session_state.auth_mode == "login":
                st.caption("还没有账号？")
                if st.button("立即注册", key="switch_to_register"):
                    st.session_state.auth_mode = "register"
                    st.rerun()
            else:
                st.caption("已有账号？")
                if st.button("立即登录", key="switch_to_login"):
                    st.session_state.auth_mode = "login"
                    st.rerun()

    @staticmethod
    def handle_auth_submission():
        """处理认证表单提交"""
        mode = st.session_state.auth_mode
        username = st.session_state.auth_username
        password = st.session_state.auth_password

        if not username or not password:
            st.error("用户名和密码不能为空")
            return

        try:
            if mode == "login":
                # 调用登录API（这里暂时模拟）
                success, user_data = UIManager.authenticate_user(username, password)
                if success:
                    SessionManager.login_user(user_data)
                    st.session_state.show_auth_modal = False
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error("用户名或密码错误")

            else:  # register
                email = st.session_state.get("auth_email", "")
                display_name = st.session_state.get("auth_display_name", username)

                # 调用注册API（这里暂时模拟）
                success, user_data = UIManager.register_user(username, password, email, display_name)
                if success:
                    SessionManager.login_user(user_data)
                    st.session_state.show_auth_modal = False
                    st.success("注册成功！")
                    st.rerun()
                else:
                    st.error("注册失败，请稍后重试")

        except Exception as e:
            st.error(f"认证失败: {str(e)}")

    @staticmethod
    def authenticate_user(username: str, password: str) -> tuple:
        """用户认证（调用API）"""
        try:
            import requests
            response = requests.post(f"{API_BASE_URL}/auth/login", json={
                "username": username,
                "password": password
            }, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return True, data.get("user", {})
                else:
                    return False, None
            else:
                print(f"认证API返回错误: {response.status_code} - {response.text}")
                return False, None

        except requests.exceptions.ConnectionError:
            st.error("无法连接到服务器，请检查网络连接")
            return False, None
        except Exception as e:
            print(f"认证API调用失败: {str(e)}")
            st.error(f"登录失败: {str(e)}")
            return False, None

    @staticmethod
    def register_user(username: str, password: str, email: str, display_name: str) -> tuple:
        """用户注册（调用API）"""
        try:
            import requests
            response = requests.post(f"{API_BASE_URL}/auth/register", json={
                "username": username,
                "password": password,
                "email": email,
                "display_name": display_name
            }, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return True, data.get("user", {})
                else:
                    st.error(data.get("message", "注册失败"))
                    return False, None
            else:
                print(f"注册API返回错误: {response.status_code} - {response.text}")
                st.error("注册失败，请稍后重试")
                return False, None

        except requests.exceptions.ConnectionError:
            st.error("无法连接到服务器，请检查网络连接")
            return False, None
        except Exception as e:
            print(f"注册API调用失败: {str(e)}")
            st.error(f"注册失败: {str(e)}")
            return False

    @staticmethod
    def render_welcome_page():
        """渲染欢迎页面（未登录用户）"""
        st.title("🚀 欢迎使用 AgentForge")
        st.markdown("""
        ## 智能对话与知识库管理系统

        **AgentForge** 是一个基于 LangGraph 实现的智能对话系统，提供以下核心功能：

        ### ✨ 主要功能
        - 🤖 **智能对话** - 基于大语言模型的多轮对话
        - 📚 **知识库管理** - 文档上传、处理和检索
        - 🔧 **工具集成** - 扩展各种实用工具
        - 💾 **会话记忆** - 保持对话上下文和历史

        ### 🚀 快速开始
        1. 点击左侧边栏的 **"🔐 登录"** 或 **"📝 注册"** 按钮
        2. 如果还没有账号，请先注册新用户
        3. 登录后即可开始使用所有功能

        ### 💡 提示
        - 首次使用建议先浏览知识库管理，上传一些文档
        - 智能对话支持工具调用，可以执行计算、搜索等任务
        - 所有对话历史都会被保存，可以随时查看

        ---
        """)

        # 功能预览
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("🤖 智能对话")
            st.write("与AI助手进行自然对话，支持工具调用和知识库检索")
            st.info("需要登录后使用")

        with col2:
            st.subheader("📚 知识库")
            st.write("上传和管理文档，建立专属知识库")
            st.info("需要登录后使用")

        with col3:
            st.subheader("🔧 工具集成")
            st.write("配置和使用各种实用工具")
            st.info("需要登录后使用")

        st.divider()

        # 快速操作
        st.subheader("🔑 立即开始")
        st.markdown("请点击左侧边栏进行登录或注册")

        # 系统状态展示
        if st.session_state.get('api_health', False):
            st.success("🟢 系统运行正常")
        else:
            st.warning("🟡 系统正在启动中，请稍候...")

        # 版本信息
        st.caption("AgentForge v1.0.0 | 基于 LangGraph + Streamlit"), None

    @staticmethod
    def render_sidebar() -> str:
        """渲染侧边栏并返回选择的页面"""
        with st.sidebar:
            st.title("🚀 AgentForge")
            st.caption("智能对话与知识库管理系统")

            # 用户认证区域
            UIManager.render_user_auth_section()

            st.divider()

            # 系统状态
            UIManager._render_system_status()

            # 快捷操作
            UIManager._render_quick_actions()

            # 只有在用户登录后才显示导航菜单和系统状态
            if SessionManager.is_authenticated():

                st.divider()

                # 导航菜单
                pages = {
                    "🤖 智能体对话": "智能体对话",
                    "📚 知识库管理": "知识库管理",
                    "🔧 工具管理": "工具管理"
                }

                page_icons = list(pages.keys())
                selected_icon = st.radio(
                    "导航",
                    page_icons,
                    index=page_icons.index("🤖 智能体对话") if st.session_state.current_page == "智能体对话"
                    else page_icons.index("📚 知识库管理") if st.session_state.current_page == "知识库管理"
                    else page_icons.index("🔧 工具管理"),
                    label_visibility="collapsed"
                )

                selected_page = pages[selected_icon]
                SessionManager.set_current_page(selected_page)
                st.divider()
                return selected_page
            else:
                # 未登录用户显示提示信息
                st.divider()
                st.info("🔐 请先登录以访问系统功能")
                st.markdown("""
                **可用功能：**
                - 用户注册和登录
                - 密码找回（即将上线）

                请点击上方登录或注册按钮开始使用。
                """)

                # 返回默认页面（不会被使用，因为未登录用户无法访问主要功能）
                return "未登录"

    @staticmethod
    def _render_system_status():
        """渲染系统状态"""
        api_healthy = st.session_state.get('api_health', False)
        if api_healthy:
            status_icon = "🟢"
            status_text = "正常"
            help_text = "API服务运行正常"
        else:
            status_icon = "🔴"
            status_text = "离线"
            help_text = "API服务未启动，请运行: python scripts/start_server.py --mode api"

        st.metric("API状态", f"{status_icon} {status_text}", help=help_text)

        # 如果API不健康，显示警告信息
        if not api_healthy:
            st.warning("⚠️ API服务不可用。智能对话和知识库功能将受限。请先启动API服务器。")
            st.info("启动命令: `python scripts/start_server.py --mode api`")

    @staticmethod
    def _render_quick_actions():
        """渲染快捷操作"""
        st.subheader("快捷操作")
        if st.button("🔄 刷新数据", use_container_width=True):
            asyncio.run(UIManager._refresh_all_data())

    @staticmethod
    async def _refresh_all_data():
        """刷新所有数据"""
        with st.spinner("刷新数据中..."):
            kb_success = await APIManager.load_knowledge_bases()
            tools_success = await APIManager.load_tools()
            models_success = await APIManager.load_models()
            health_success = await APIManager.check_api_health()

            if kb_success and tools_success and models_success and health_success:
                st.success("✅ 数据刷新完成")
            else:
                st.warning("⚠️ 部分数据刷新失败")

    @staticmethod
    def render_footer():
        """渲染页脚"""
        st.divider()
        col1, col2, col3 = st.columns(3)

        with col1:
            st.caption("🛠️ 技术栈: LangGraph + Streamlit")

        with col2:
            st.caption("📊 版本: v1.0.0")

        with col3:
            st.caption("🔗 [GitHub](https://github.com/X2099/LangGraph-AgentForge)")


async def initialize_app():
    """初始化应用"""
    # 初始化会话状态
    SessionManager.initialize_session_state()

    # 检查API健康状态
    api_healthy = await APIManager.check_api_health()

    # 如果API健康，加载基础数据
    if api_healthy and not st.session_state.knowledge_bases:
        try:
            await APIManager.load_knowledge_bases()
            await APIManager.load_models()
            await APIManager.load_tools()
        except Exception as e:
            print(f"加载基础数据失败: {str(e)}")

    # 如果API不健康，不加载数据，但允许应用继续运行
    if not api_healthy:
        print("API服务不可用，某些功能可能受限")


def main():
    """主函数"""
    # 设置页面配置
    UIManager.setup_page_config()

    # 初始化应用
    asyncio.run(initialize_app())

    # 尝试恢复登录状态
    SessionManager.restore_login_state()

    # 渲染认证模态框（如果需要）
    UIManager.render_auth_modal()

    # 渲染侧边栏并获取选择的页面
    selected_page = UIManager.render_sidebar()

    st.divider()
    # 页面路由
    try:
        if SessionManager.is_authenticated():
            # 已登录用户可以访问所有功能
            if selected_page == "智能体对话":
                chat_main()
            elif selected_page == "知识库管理":
                kb_main()
            elif selected_page == "工具管理":
                tools_main()
        else:
            # 未登录用户显示欢迎页面
            UIManager.render_welcome_page()
    except Exception as e:
        st.error(f"页面加载错误: {str(e)}")
        st.exception(e)

    # 渲染页脚
    UIManager.render_footer()


if __name__ == "__main__":
    main()
