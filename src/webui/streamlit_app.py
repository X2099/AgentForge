# -*- coding: utf-8 -*-
"""
@File    : streamlit_app.py
@Time    : 2025/12/9 14:43
@Desc    : LangGraph-AgentForge 主应用
"""
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.langgraph_api import (
    chat, create_knowledge_base, list_knowledge_bases,
    search_knowledge_base, list_tools, call_tool
)
from src.webui.knowledge_base_ui import main as kb_main
from src.webui.chat_ui import main as chat_main
from src.webui.tools_ui import main as tools_main


class SessionManager:
    """会话状态管理器"""

    DEFAULT_STATE = {
        # 对话相关
        "conversation_history": [],
        "current_kb": "default",

        # 工具相关
        "available_tools": [],

        # 知识库相关
        "knowledge_bases": [],

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
    async def check_api_health() -> bool:
        """检查API健康状态"""
        try:
            # 导入requests库来调用健康检查端点
            import requests
            from src.webui.chat_ui import BASE_URL

            # 调用专门的健康检查端点
            response = requests.get(f"{BASE_URL}/health", timeout=5)

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
                'Get Help': 'https://github.com/your-repo/LangGraph-AgentForge',
                'Report a bug': 'https://github.com/your-repo/LangGraph-AgentForge/issues',
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
    def render_sidebar() -> str:
        """渲染侧边栏并返回选择的页面"""
        with st.sidebar:
            st.title("🚀 AgentForge")
            st.caption("智能对话与知识库管理系统")

            # 系统状态
            UIManager._render_system_status()

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

            # 快捷操作
            UIManager._render_quick_actions()

            return selected_page

    @staticmethod
    def _render_system_status():
        """渲染系统状态"""
        api_healthy = st.session_state.get('api_health', False)

        col1, col2 = st.columns(2)
        with col1:
            if api_healthy:
                status_icon = "🟢"
                status_text = "正常"
                help_text = "API服务运行正常"
            else:
                status_icon = "🔴"
                status_text = "离线"
                help_text = "API服务未启动，请运行: python scripts/start_server.py --mode api"

            st.metric("API状态", f"{status_icon} {status_text}", help=help_text)

        with col2:
            kb_count = len(st.session_state.get('knowledge_bases', []))
            kb_help = f"已加载 {kb_count} 个知识库" if kb_count > 0 else "未加载知识库"
            st.metric("知识库", kb_count, help=kb_help)

        # 如果API不健康，显示警告信息
        if not api_healthy:
            st.warning("⚠️ API服务不可用。智能对话和知识库功能将受限。请先启动API服务器。")
            st.info("启动命令: `python scripts/start_server.py --mode api`")

    @staticmethod
    def _render_quick_actions():
        """渲染快捷操作"""
        st.subheader("快捷操作")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 刷新数据", use_container_width=True):
                asyncio.run(UIManager._refresh_all_data())

        with col2:
            if st.button("🗑️ 清空对话", use_container_width=True):
                SessionManager.reset_conversation()
                st.success("对话已清空")
                st.rerun()

    @staticmethod
    async def _refresh_all_data():
        """刷新所有数据"""
        with st.spinner("刷新数据中..."):
            kb_success = await APIManager.load_knowledge_bases()
            tools_success = await APIManager.load_tools()
            health_success = await APIManager.check_api_health()

            if kb_success and tools_success and health_success:
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
            st.caption("🔗 [GitHub](https://github.com/your-repo/LangGraph-AgentForge)")


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
        except Exception as e:
            print(f"加载知识库失败: {str(e)}")

    # 如果API不健康，不加载数据，但允许应用继续运行
    if not api_healthy:
        print("API服务不可用，某些功能可能受限")


def main():
    """主函数"""
    # 设置页面配置
    UIManager.setup_page_config()

    # 初始化应用
    asyncio.run(initialize_app())

    # 渲染侧边栏并获取选择的页面
    selected_page = UIManager.render_sidebar()

    # 页面路由
    try:
        if selected_page == "智能体对话":
            chat_main()
        elif selected_page == "知识库管理":
            kb_main()
        elif selected_page == "工具管理":
            tools_main()
    except Exception as e:
        st.error(f"页面加载错误: {str(e)}")
        st.exception(e)

    # 渲染页脚
    UIManager.render_footer()


if __name__ == "__main__":
    main()
