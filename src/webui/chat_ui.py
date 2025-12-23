# -*- coding: utf-8 -*-
"""
@File    : chat_ui.py
@Time    : 2025/12/9 15:54
@Desc    : 
"""
from datetime import datetime
import requests
import streamlit as st

from . import API_BASE_URL
from .styles.custom_styles import apply_custom_styles


def check_api_health():
    """检查API服务器健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        st.error(f"检查API服务器健康状态异常：{e}")
        return False


def fetch_user_sessions(user_id, mode, limit=50):
    """从API获取用户会话列表"""
    try:
        response = requests.get(f"{API_BASE_URL}/users/{user_id}/sessions", params={"mode": mode, "limit": limit},
                                timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取会话列表失败: {response.status_code}")
            return []
    except Exception as e:
        print(f"获取会话列表异常: {str(e)}")
        return []


def create_session_via_api(user_id, mode, title=None, model_name=None):
    """通过API创建新会话"""
    try:
        data = {
            "user_id": user_id,
            "title": title or f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "model_name": model_name,
            "mode": mode
        }
        response = requests.post(f"{API_BASE_URL}/user-sessions", json=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"创建会话失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"创建会话异常: {str(e)}")
        return None


def delete_session_via_api(session_id):
    """通过API删除会话"""
    try:
        response = requests.delete(f"{API_BASE_URL}/user-sessions/{session_id}", timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"删除会话异常: {str(e)}")
        return False


def get_session_messages_via_api(session_id, limit=100):
    """从API获取会话消息"""
    try:
        response = requests.get(f"{API_BASE_URL}/sessions/{session_id}/messages", params={"limit": limit},
                                timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取会话消息失败: {response.status_code}")
            return []
    except Exception as e:
        print(f"获取会话消息异常: {str(e)}")
        return []


def render_api_status():
    """渲染系统状态信息"""
    st.markdown("### 🔌 系统状态")

    # API健康状态
    api_healthy = check_api_health()
    if api_healthy:
        st.success("🟢 API服务正常")
    else:
        st.error("🔴 API服务离线")
        st.caption("请检查API服务器是否运行")

    # 知识库状态
    kb_count = len(st.session_state.get('knowledge_bases', []))
    if kb_count > 0:
        st.info(f"📚 已加载 {kb_count} 个知识库")
    else:
        st.warning("📚 未加载知识库")

    # 模型状态
    model_count = len(st.session_state.get('available_models', []))
    if model_count > 0:
        st.info(f"🤖 已加载 {model_count} 个模型")
    else:
        st.caption("🤖 模型信息暂未加载")

    # 显示最后更新时间
    last_update = st.session_state.get('last_update')
    if last_update:
        from datetime import datetime
        if isinstance(last_update, (int, float)):
            update_time = datetime.fromtimestamp(last_update).strftime('%H:%M:%S')
        else:
            update_time = "最近"
        st.caption(f"最后更新: {update_time}")

    # 如果API不健康，显示警告信息
    if not api_healthy:
        st.warning("⚠️ API服务不可用。智能对话功能将受限。")
        st.caption("启动命令: `python scripts/start_server.py --mode api`")


def process_user_input(user_input: str, mode: str, selected_model: str = None):
    """处理用户输入并生成回复"""
    # 获取当前设置
    selected_tools = st.session_state.get('selected_tools', [])
    use_kb = st.session_state.get('use_kb', True)
    current_session_id = st.session_state.get(f'current_session_id_{mode}')

    # 生成助手回复
    with st.chat_message("assistant"):
        with st.spinner("🤖 正在思考中..."):
            try:
                # 准备历史消息（不包括当前用户消息，因为它已经在历史中了）
                history = st.session_state.conversation_history[:-1]

                # 调用API，传递会话ID和用户ID（如果已登录）
                payload = {
                    "query": user_input,
                    "conversation_id": current_session_id,  # 传递会话ID
                    "user_id": st.session_state.current_user.get("user_id") if st.session_state.get(
                        "user_authenticated") and st.session_state.get("current_user") else None,  # 传递用户ID
                    "history": history,
                    "knowledge_base_name": st.session_state.current_kb,
                    "use_knowledge_base": use_kb,
                    "tools": selected_tools,
                    "model": selected_model,
                    "mode": mode
                }

                response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=60)

                if response.status_code == 200:
                    # 解析响应
                    response_data = response.json()
                    assistant_message = response_data.get("response", "")
                    sources = response_data.get("sources", [])
                    conversation_id = response_data.get("conversation_id")

                    # 更新当前会话ID（如果API返回了新的会话ID）
                    if conversation_id and conversation_id != current_session_id:
                        st.session_state[f'current_session_id_{mode}'] = conversation_id

                    # 显示回复
                    if assistant_message:
                        st.write(assistant_message)
                    else:
                        st.warning("助手没有返回有效回复")

                    # 创建列来并排显示来源和元数据
                    col1, col2 = st.columns(2)

                    # 显示来源
                    with col1:
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
                        "role": "ai",
                        "content": assistant_message,
                        "sources": sources
                    })

                    # 更新当前会话的消息和时间戳
                    current_session = get_current_session(mode)
                    if current_session:
                        current_session["messages"] = st.session_state.conversation_history.copy()
                        current_session["updated_at"] = datetime.now()

                        # 如果是第一次对话，根据用户输入自动更新标题
                        if len(current_session["messages"]) == 2:  # 用户消息 + 助手消息
                            first_user_msg = current_session["messages"][0]["content"]
                            if len(first_user_msg) > 20:
                                current_session["title"] = f"{first_user_msg[:20]}..."
                            else:
                                current_session["title"] = first_user_msg
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


def render_rag_interface():
    """RAG问答界面"""
    st.header("📚 基于知识库的RAG问答")
    st.caption("基于您选择的知识库进行智能问答")

    # RAG专用设置
    with st.sidebar:
        st.header("⚙️ RAG设置")

        # 模型选择
        available_models = st.session_state.get("available_models", [])
        model_options = [model["display_name"] for model in available_models]
        model_names = [model["name"] for model in available_models]

        selected_index = st.selectbox(
            "选择模型",
            range(len(model_options)),
            format_func=lambda x: model_options[x] if model_options else "默认模型",
            key="rag_model_select"
        )
        selected_model = model_names[selected_index] if model_names else None

        # 知识库选择
        kb_names = [kb["name"] for kb in st.session_state.get("knowledge_bases", [])]
        selected_kb = st.selectbox(
            "选择知识库",
            kb_names if kb_names else ["default"],
            key="rag_kb_select"
        )
        st.session_state.current_kb = selected_kb

        # RAG状态显示
        st.subheader("📊 RAG状态")

        col1, col2 = st.columns(2)
        with col1:
            kb_count = len(st.session_state.get('knowledge_bases', []))
            kb_help = f"已加载 {kb_count} 个知识库" if kb_count > 0 else "未加载知识库"
            st.metric("知识库", kb_count, help=kb_help)
        with col2:
            if st.session_state.knowledge_bases:
                kb_info = next(
                    (kb for kb in st.session_state.knowledge_bases if kb["name"] == selected_kb),
                    {}
                )
                if kb_info:
                    st.metric("文档数", f"{kb_info.get('document_count', 0)} 篇")
                else:
                    st.metric("知识库状态", "未选择")

        # 设置会话状态
        st.session_state.selected_model = selected_model
        st.session_state.use_kb = True
        st.session_state.selected_tools = []  # RAG模式不使用工具

    # 创建左右布局：左侧聊天界面，右侧会话列表
    col1, separator, col2 = st.columns([3, 0.1, 1.0])

    with col1:
        # 左侧：RAG聊天界面
        render_chat_interface("rag")

    with separator:
        # 中间分隔区域
        st.markdown("""
        <div style="
            width: 100%;
            height: 100%;
            background: linear-gradient(180deg, #e5e7eb 0%, #d1d5db 50%, #e5e7eb 100%);
            border-radius: 2px;
            box-shadow: 0 0 8px rgba(0,0,0,0.1);
            margin: 0 2px;
        "></div>
        """, unsafe_allow_html=True)

    with col2:
        # 右侧：会话列表面板
        render_session_panel("rag")


def render_agent_interface():
    """Agent工具界面"""
    st.header("🔧 基于工具的Agent助手")
    st.caption("智能助手可以调用各种工具来帮助您解决问题")

    # Agent专用设置
    with st.sidebar:
        st.header("⚙️ Agent设置")

        # 模型选择
        available_models = st.session_state.get("available_models", [])
        model_options = [model["display_name"] for model in available_models]
        model_names = [model["name"] for model in available_models]

        selected_index = st.selectbox(
            "选择模型",
            range(len(model_options)),
            format_func=lambda x: model_options[x] if model_options else "默认模型",
            key="agent_model_select"
        )
        selected_model = model_names[selected_index] if model_names else None

        # 工具选择
        if st.session_state.available_tools:
            st.subheader("🔧 工具设置")

            tool_names = [tool.get('name', '') for tool in st.session_state.available_tools]
            if not st.session_state.get('selected_tools'):
                st.session_state.selected_tools = tool_names.copy()

            selected_tools = st.multiselect(
                "选择要使用的工具",
                options=tool_names,
                default=st.session_state.selected_tools,
                help="选择助手可以使用的工具",
                key="agent_tools_select"
            )
            st.session_state.selected_tools = selected_tools
        else:
            st.session_state.selected_tools = []

        # Agent状态显示
        st.subheader("📊 Agent状态")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("对话轮数", len([msg for msg in st.session_state.conversation_history if msg["role"] == "user"]))
        with col2:
            tool_count = len(st.session_state.get('selected_tools', []))
            st.metric("激活工具", tool_count)

        # 设置会话状态
        st.session_state.selected_model = selected_model
        st.session_state.use_kb = False

    # 创建左右布局：左侧聊天界面，右侧会话列表
    col1, separator, col2 = st.columns([3, 0.1, 1.0])

    with col1:
        # 左侧：Agent聊天界面
        render_chat_interface("agent")

    with separator:
        # 中间分隔区域
        st.markdown("""
        <div style="
            width: 100%;
            height: 100%;
            background: linear-gradient(180deg, #e5e7eb 0%, #d1d5db 50%, #e5e7eb 100%);
            border-radius: 2px;
            box-shadow: 0 0 8px rgba(0,0,0,0.1);
            margin: 0 2px;
        "></div>
        """, unsafe_allow_html=True)

    with col2:
        # 右侧：会话列表面板
        render_session_panel("agent")


def render_chat_interface(mode):
    """渲染聊天界面"""
    # 为不同模式使用独立的会话历史
    history_key = f"conversation_history_{mode}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    # 使用模式特定的历史
    original_history = st.session_state.get("conversation_history", [])
    st.session_state.conversation_history = st.session_state[history_key]

    try:
        # 显示当前会话标题
        current_session = get_current_session(mode)
        if current_session:
            st.subheader(f"💬 {current_session['title']} ({mode.upper()})")
        else:
            st.subheader(f"💬 新对话 ({mode.upper()})")

        # 显示对话历史
        for msg in st.session_state.conversation_history:
            if msg["role"] == "human":
                with st.chat_message("user"):
                    st.write(msg["content"])
            elif msg["role"] == "ai":
                with st.chat_message("assistant"):
                    st.write(msg["content"])

                    # 创建列来并排显示来源和元数据
                    col1, col2 = st.columns(2)

                    # 显示来源（如果有）
                    with col1:
                        if msg.get("sources"):
                            with st.expander("📚 信息来源"):
                                for i, source in enumerate(msg["sources"]):
                                    st.caption(f"**来源 {i + 1}:** {source.get('source', '未知')}")
                                    content = source.get("content", "")
                                    if len(content) > 150:
                                        content = content[:150] + "..."
                                    st.caption(content)

                    # 显示响应元数据（如果有）
                    with col2:
                        if msg.get("response_metadata"):
                            with st.expander("🔍 响应元数据"):
                                metadata = msg["response_metadata"]
                                st.caption(f"**查询:** {metadata.get('query', 'N/A')[:50]}...")
                                st.caption(f"**文档数量:** {len(metadata.get('documents', []))}")
                                st.caption(f"**来源数量:** {len(metadata.get('sources', []))}")
                                st.caption(f"**上下文长度:** {metadata.get('context_length', 0)}")
                                if metadata.get('timestamp'):
                                    st.caption(f"**生成时间:** {metadata['timestamp'][:19]}")
                                if metadata.get('error'):
                                    st.error(f"**错误:** {metadata['error'][:100]}...")
            elif msg["role"] == "tool":
                with st.chat_message("tool"):
                    # 工具消息使用特殊的样式
                    st.markdown("🔧 **工具调用结果**")
                    st.code(msg["content"], language="json")
            else:
                # 其他类型的消息
                with st.chat_message("assistant"):
                    st.markdown(f"**{msg['role'].upper()}**: {msg['content']}")

        placeholder = "问我关于知识库的问题..." if mode == "rag" else "让我帮您解决问题..."
        user_input = st.chat_input(
            placeholder,
            key=f"{mode}_input",
            max_chars=2000
        )

        if user_input and user_input.strip():
            # 显示用户消息
            with st.chat_message("user"):
                st.write(user_input.strip())

            # 添加到历史
            st.session_state.conversation_history.append({
                "role": "human",
                "content": user_input.strip()
            })

            # 更新当前会话的消息
            current_session = get_current_session(mode)
            if current_session:
                current_session["messages"] = st.session_state.conversation_history.copy()
                current_session["updated_at"] = datetime.now()

            # 处理回复
            process_user_input(user_input.strip(), mode, st.session_state.selected_model)

    finally:
        # 恢复原始历史
        st.session_state.conversation_history = original_history


def main():
    """主界面"""
    st.title("🤖 AgentForge")
    st.caption("基于LangGraph实现的智能对话系统")

    # 检查用户认证状态
    if not st.session_state.get("user_authenticated", False):
        st.warning("⚠️ 请先登录以使用对话功能")
        st.info("点击左侧边栏的登录按钮进行认证")
        return

    # 检查API状态
    api_healthy = check_api_health()
    if not api_healthy:
        st.error("⚠️ API服务器未运行，请先启动服务器")
        st.info("运行 `python scripts/start_server.py --mode api` 启动API服务器")
        return

    # 初始化会话管理
    initialize_session_management()
    # 应用集中样式
    apply_custom_styles()

    tab = st.radio(
        "选择模式",
        ["🔧 Agent问答", "📚 RAG问答"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if tab == "🔧 Agent问答":
        render_agent_interface()
    elif tab == "📚 RAG问答":
        render_rag_interface()


def initialize_session_management():
    """初始化会话管理相关的session state"""
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []

    # 初始化输入框状态
    if "chat_input_text" not in st.session_state:
        st.session_state.chat_input_text = ""

    # 初始化右侧面板折叠状态
    if "session_panel_expanded" not in st.session_state:
        st.session_state.session_panel_expanded = True


def get_current_session(mode):
    """获取当前会话信息（简化版）"""
    session_id = st.session_state.get(f"current_session_id_{mode}")
    if session_id:
        # 这里可以从API获取会话详情，但为了性能暂时返回基本信息
        return {
            "session_id": session_id,
            "title": f"对话 {session_id[:8]}..."  # 临时标题
        }
    return None


def render_session_panel(mode="default"):
    """渲染右侧会话记录面板"""
    # 获取当前用户信息
    user_authenticated = st.session_state.get("user_authenticated", False)
    current_user = st.session_state.get("current_user") if user_authenticated else None

    if not user_authenticated or not current_user:
        st.caption("请先登录以查看会话记录")
        return

    user_id = current_user.get("user_id")
    current_session_id = st.session_state.get(f"current_session_id_{mode}")

    # New Chat按钮 - 始终可见
    if st.button("➕ 新建对话", use_container_width=True, type="primary", key=f"new_chat_{mode}"):
        # 通过API创建新会话
        new_session = create_session_via_api(user_id, mode, model_name=st.session_state.get("selected_model"))
        if new_session:
            session_id = new_session.get("session_id")
            st.session_state[f"current_session_id_{mode}"] = session_id
            st.session_state.rrent_session_id = session_id
            # 清空当前模式的对话历史
            history_key = f"conversation_history_{mode}"
            st.session_state[history_key] = []
            st.success(f"已创建新对话: {new_session.get('title', '新对话')}")
            st.rerun()
        else:
            st.error("创建新对话失败")

    # 可折叠的会话列表
    with st.expander(f"📋 {mode.title()} 会话列表", expanded=st.session_state.session_panel_expanded):
        # 从API获取会话列表
        sessions = fetch_user_sessions(user_id, mode, limit=50)

        if not sessions:
            st.caption("暂无会话记录")
            return

        # 按更新时间倒序排列
        sorted_sessions = sorted(
            sessions,
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )

        for session in sorted_sessions:
            session_id = session["session_id"]
            title = session["title"]
            is_current = session_id == current_session_id

            # 会话项容器
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    # 会话标题
                    button_label = f"{'🔵' if is_current else ''} {title}"
                    if st.button(button_label, key=f"session_{session_id}_{mode}", use_container_width=True):
                        # 切换到选中会话
                        st.session_state[f"current_session_id_{mode}"] = session_id
                        # 从API加载会话消息
                        messages = get_session_messages_via_api(session_id)
                        # 转换为前端格式
                        conversation_history = []
                        for msg in messages:
                            conversation_history.append({
                                "role": msg["role"],
                                "content": msg["content"],
                                "sources": msg["sources"]
                            })
                        # 设置模式特定的会话历史
                        history_key = f"conversation_history_{mode}"
                        st.session_state[history_key] = conversation_history
                        st.rerun()

                with col2:
                    # 删除按钮
                    if st.button("🗑️", key=f"delete_{session_id}_{mode}", help="删除会话"):
                        if delete_session_via_api(session_id):
                            st.success("会话已删除")
                            # 如果删除的是当前会话，清空状态
                            if session_id == current_session_id:
                                st.session_state[f"current_session_id_{mode}"] = None
                                # 清空当前模式的对话历史
                                history_key = f"conversation_history_{mode}"
                                st.session_state[history_key] = []
                            st.rerun()
                        else:
                            st.error("删除会话失败")

            # 分隔线
            st.divider()
