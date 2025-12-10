# -*- coding: utf-8 -*-
"""
@File    : chat_ui.py
@Time    : 2025/12/9 15:54
@Desc    : 
"""
import asyncio

import requests
import streamlit as st

from src.api.langgraph_api import chat

BASE_URL = "http://127.0.0.1:7861"


def check_api_health():
    """检查API服务器健康状态"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def process_user_input(user_input: str):
    """处理用户输入并生成回复"""
    # 获取当前设置
    selected_tools = st.session_state.get('selected_tools', [])
    use_kb = st.session_state.get('use_kb', True)

    # 生成助手回复
    with st.chat_message("assistant"):
        with st.spinner("🤖 正在思考中..."):
            try:
                # 准备历史消息（不包括当前用户消息，因为它已经在历史中了）
                history = st.session_state.conversation_history[:-1]

                # 调用API
                payload = {
                    "query": user_input,
                    "history": history,
                    "knowledge_base_name": st.session_state.current_kb,
                    "use_knowledge_base": use_kb,
                    "tools": selected_tools
                }

                response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=60)

                if response.status_code == 200:
                    # 解析响应
                    response_data = response.json()
                    assistant_message = response_data.get("response", "")
                    sources = response_data.get("sources", [])

                    # 显示回复
                    if assistant_message:
                        st.write(assistant_message)
                    else:
                        st.warning("助手没有返回有效回复")

                    # 显示来源
                    if sources:
                        with st.expander("📚 信息来源"):
                            for i, source in enumerate(sources, 1):
                                st.caption(f"**来源 {i}:** {source.get('source', '未知')}")
                                content = source.get("content", "")
                                if len(content) > 200:
                                    content = content[:200] + "..."
                                st.caption(content)

                    # 添加到历史
                    st.session_state.conversation_history.append({
                        "role": "assistant",
                        "content": assistant_message,
                        "sources": sources
                    })
                else:
                    st.error(f"API请求失败 (状态码: {response.status_code})")
                    st.caption(f"错误详情: {response.text}")

            except requests.exceptions.Timeout:
                st.error("⏰ 请求超时，请稍后重试")
            except requests.exceptions.ConnectionError:
                st.error("🌐 网络连接失败，请检查服务器是否运行")
            except Exception as e:
                st.error(f"❌ 发生错误: {str(e)}")
                st.caption("请检查网络连接或联系管理员")

    # 清空输入框
    st.session_state.chat_input_text = ""


def main():
    """主界面"""
    st.title("🤖 LangGraph-AgentForge")
    st.caption("基于LangGraph实现的智能对话系统")

    # 检查API状态
    api_healthy = check_api_health()
    if not api_healthy:
        st.error("⚠️ API服务器未运行，请先启动服务器")
        st.info("运行 `python scripts/start_server.py --mode api` 启动API服务器")
        return

    # 侧边栏
    with st.sidebar:
        st.header("设置")

        # 模型选择
        model_option = st.selectbox(
            "选择模型",
            ["deepseek-chat", "gpt-4", "本地模型"]
        )

        # 知识库选择
        kb_names = [kb["name"] for kb in st.session_state.get("knowledge_bases", [])]
        selected_kb = st.selectbox(
            "选择知识库",
            kb_names if kb_names else ["default"],
            index=0
        )
        st.session_state.current_kb = selected_kb

        use_kb = st.checkbox("使用知识库", value=True)

        # 工具选择
        selected_tools = []
        if st.session_state.available_tools:
            st.subheader("🔧 工具设置")

            # 默认选择全部工具
            tool_names = [tool.get('name', '') for tool in st.session_state.available_tools]
            if not st.session_state.get('selected_tools'):
                st.session_state.selected_tools = tool_names.copy()

            # 工具选择控制
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ 全选", key="select_all_tools"):
                    st.session_state.selected_tools = tool_names.copy()
                    st.rerun()
            with col2:
                if st.button("❌ 清空", key="clear_tools"):
                    st.session_state.selected_tools = []
                    st.rerun()
            with col3:
                if st.button("🔄 重置", key="reset_tools"):
                    # 重新加载工具列表
                    import asyncio
                    from src.webui.streamlit_app import APIManager
                    asyncio.run(APIManager.load_tools())
                    st.session_state.selected_tools = tool_names.copy()
                    st.rerun()

            # 多选框选择工具
            selected_tools = st.multiselect(
                "选择要使用的工具",
                options=tool_names,
                default=st.session_state.selected_tools,
                help="选择助手可以使用的工具，不选择则仅使用对话能力",
                key="tool_selector"
            )
            st.session_state.selected_tools = selected_tools

            # 显示选择统计
            total_tools = len(tool_names)
            selected_count = len(selected_tools)
            st.caption(f"已选择 {selected_count}/{total_tools} 个工具")

            # 显示选中的工具详情
            if selected_tools:
                with st.expander("📋 选中的工具详情", expanded=False):
                    for tool in st.session_state.available_tools:
                        if tool.get('name') in selected_tools:
                            st.markdown(f"**🔧 {tool.get('name')}**")
                            st.caption(tool.get('description', '暂无描述'))
                            if tool.get('inputSchema'):
                                with st.expander(f"参数模式 - {tool.get('name')}", expanded=False):
                                    st.json(tool['inputSchema'])
                            st.divider()

        # 清空对话
        if st.button("清空对话历史"):
            st.session_state.conversation_history = []
            st.rerun()

        # 系统状态
        st.divider()
        st.subheader("📊 系统状态")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("对话轮数", len([msg for msg in st.session_state.conversation_history if msg["role"] == "user"]))
        with col2:
            api_status = "🟢 正常" if api_healthy else "🔴 离线"
            st.metric("API状态", api_status)
        with col3:
            tool_count = len(st.session_state.get('selected_tools', []))
            st.metric("激活工具", tool_count)

        # 知识库状态
        if st.session_state.knowledge_bases:
            kb_info = next(
                (kb for kb in st.session_state.knowledge_bases if kb["name"] == selected_kb),
                {}
            )
            if kb_info:
                st.metric("当前知识库", f"{kb_info.get('document_count', 0)} 文档")
            else:
                st.metric("当前知识库", "未选择")
        else:
            st.metric("知识库状态", "未加载")

    # 获取工具选择状态
    selected_tools = st.session_state.get('selected_tools', [])
    use_kb = st.session_state.get('use_kb', True)

    # ChatGPT风格的样式定义
    st.markdown("""
    <style>
    /* 减少标题间距 */
    .stTitle {
        margin-bottom: 10px !important;
        padding-bottom: 5px !important;
    }

    .stCaption {
        margin-bottom: 15px !important;
        color: #666 !important;
        font-size: 14px !important;
    }

    /* 紧凑的页面布局 */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }

    /* 优化chat_input发送按钮垂直居中 */
    .stChatInput {
        align-items: center !important;
    }

    .stChatInput > div {
        display: flex !important;
        align-items: center !important;
    }

    .stChatInput button {
        align-self: center !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }

    /* 确保输入框和按钮在同一水平线上 */
    .stChatInput input {
        line-height: normal !important;
    }

    .chat-input-fixed {
        position: fixed;
        bottom: 20px;
        left: 320px; /* 留出侧边栏的空间 */
        right: 20px;
        background: white;
        padding: 20px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
        z-index: 1000;
        backdrop-filter: blur(10px);
    }

    /* 响应式设计 */
    @media (max-width: 1024px) {
        .chat-input-fixed {
            left: 280px;
        }
    }

    @media (max-width: 768px) {
        .chat-input-fixed {
            left: 10px;
            right: 10px;
            bottom: 10px;
            padding: 15px;
        }
    }

    /* 聊天消息样式优化 */
    .stChatMessage {
        margin-bottom: 16px;
        padding: 12px;
        border-radius: 12px;
    }

    .stChatMessage.user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: auto;
        margin-right: 0;
        max-width: 70%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .stChatMessage.assistant {
        background: white;
        border: 1px solid #e5e7eb;
        margin-left: 0;
        margin-right: auto;
        max-width: 70%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* 输入框容器样式 */
    .input-container {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    /* 改进的按钮样式 */
    .send-button {
        min-width: 44px;
        height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #2563eb;
        color: white;
        border: none;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .send-button:hover {
        background: #1d4ed8;
        transform: scale(1.05);
    }

    /* 优化chat_input样式 */
    .stChatInput {
        position: fixed !important;
        bottom: 20px !important;
        left: 320px !important;
        right: 20px !important;
        z-index: 1000 !important;
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 24px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
        padding: 12px 20px !important;
        max-width: 768px !important;
        margin: 0 auto !important;
    }

    .stChatInput input {
        border: none !important;
        outline: none !important;
        background: transparent !important;
        font-size: 16px !important;
        line-height: 24px !important;
        color: #374151 !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }

    .stChatInput input::placeholder {
        color: #9ca3af !important;
    }

    .stChatInput button {
        background: #2563eb !important;
        border: none !important;
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        opacity: 0.7 !important;
    }

    .stChatInput button:hover {
        background: #1d4ed8 !important;
        transform: scale(1.05) !important;
        opacity: 1 !important;
    }

    .stChatInput button svg {
        width: 16px !important;
        height: 16px !important;
    }

    /* 响应式设计 */
    @media (max-width: 1024px) {
        .stChatInput {
            left: 280px !important;
        }
    }

    @media (max-width: 768px) {
        .stChatInput {
            left: 10px !important;
            right: 10px !important;
            bottom: 10px !important;
            padding: 8px 16px !important;
        }
    }

    /* 隐藏不需要的列 */
    .stColumn > div:empty {
        display: none !important;
    }

    </style>
    """, unsafe_allow_html=True)

    # 显示对话历史
    for msg in st.session_state.conversation_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])

                # 显示来源（如果有）
                if msg.get("sources"):
                    with st.expander("查看来源"):
                        for source in msg["sources"]:
                            st.caption(f"来源: {source.get('source', '未知')}")
                            st.caption(source.get("content", "")[:200])

    # 极简输入框
    user_input = st.chat_input(
        "说点什么...",
        key="simple_input",
        max_chars=2000
    )

    # 处理输入
    if user_input and user_input.strip():
        # 显示用户消息
        with st.chat_message("user"):
            st.write(user_input.strip())

        # 添加到历史
        st.session_state.conversation_history.append({
            "role": "user",
            "content": user_input.strip()
        })

        # 处理回复
        process_user_input(user_input.strip())

    # 添加少量底部空间
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

