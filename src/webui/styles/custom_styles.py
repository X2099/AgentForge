# -*- coding: utf-8 -*-
"""
自定义样式和主题
"""
import streamlit as st


def apply_custom_styles():
    """应用自定义样式"""
    # 隐藏默认的Streamlit样式
    hide_default_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* 自定义滚动条 */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }

        /* 自定义按钮样式 */
        .stButton button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        /* 自定义输入框样式 */
        .stTextInput input, .stNumberInput input, .stSelectbox select {
            border-radius: 8px;
            border: 2px solid #e0e0e0;
            transition: border-color 0.3s ease;
        }

        .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus {
            border-color: #4CAF50;
            box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
        }

        /* 自定义卡片样式 */
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 10px 0;
            border-left: 4px solid #4CAF50;
        }

        /* 自定义消息样式 */
        .user-message {
            background: #e3f2fd;
            border-radius: 12px;
            padding: 12px 16px;
            margin: 8px 0;
            border-left: 4px solid #2196F3;
        }

        .assistant-message {
            background: #f5f5f5;
            border-radius: 12px;
            padding: 12px 16px;
            margin: 8px 0;
            border-left: 4px solid #4CAF50;
        }

        /* 自定义状态指示器 */
        .status-healthy {
            color: #4CAF50;
            font-weight: bold;
        }

        .status-error {
            color: #f44336;
            font-weight: bold;
        }

        .status-warning {
            color: #ff9800;
            font-weight: bold;
        }

        /* 自定义表格样式 */
        .dataframe {
            border-radius: 8px;
            overflow: hidden;
        }

        .dataframe th {
            background: #f8f9fa;
            font-weight: 600;
        }

        /* 聊天界面样式 */
        .chat-container {
            max-height: 70vh;
            overflow-y: auto;
            margin-bottom: 20px;
        }

        /* 输入框样式优化 */
        .stChatInput {
            position: sticky;
            bottom: 0;
            background: white;
            padding: 20px 0;
            border-top: 1px solid #e0e0e0;
            margin-top: 20px;
        }

        /* 对话消息样式 */
        .stChatMessage {
            margin-bottom: 16px;
        }

        .stChatMessage.user {
            margin-left: auto;
            margin-right: 0;
            max-width: 70%;
        }

        .stChatMessage.assistant {
            margin-left: 0;
            margin-right: auto;
            max-width: 70%;
        }

        /* 自定义标签页样式 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
        }
        </style>
    """

    st.markdown(hide_default_style, unsafe_allow_html=True)


def apply_dark_theme():
    """应用暗色主题"""
    dark_theme = """
        <style>
        /* 暗色主题变量 */
        :root {
            --bg-color: #1e1e1e;
            --text-color: #ffffff;
            --secondary-bg: #2d2d2d;
            --accent-color: #4CAF50;
        }

        /* 应用暗色主题 */
        .main {
            background-color: var(--bg-color);
            color: var(--text-color);
        }

        .stTextInput input, .stNumberInput input, .stSelectbox select {
            background-color: var(--secondary-bg);
            color: var(--text-color);
            border-color: #555;
        }

        .stButton button {
            background-color: var(--accent-color);
            color: white;
        }

        .card {
            background: var(--secondary-bg);
            border-left-color: var(--accent-color);
        }

        .user-message {
            background: #1a237e;
            border-left-color: #2196F3;
        }

        .assistant-message {
            background: var(--secondary-bg);
            border-left-color: var(--accent-color);
        }
        </style>
    """

    st.markdown(dark_theme, unsafe_allow_html=True)


def create_message_bubble(content: str, is_user: bool = False):
    """创建消息气泡"""
    bubble_class = "user-message" if is_user else "assistant-message"

    html = f"""
        <div class="{bubble_class}">
            {content}
        </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def create_status_card(title: str, value: str, status: str = "info"):
    """创建状态卡片"""
    status_colors = {
        "healthy": "#4CAF50",
        "error": "#f44336",
        "warning": "#ff9800",
        "info": "#2196F3"
    }

    color = status_colors.get(status, "#2196F3")

    html = f"""
        <div class="card" style="border-left-color: {color};">
            <h4>{title}</h4>
            <p style="margin: 0; font-size: 1.2em; color: {color};">{value}</p>
        </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def create_metric_card(label: str, value: str, delta: str = None, delta_color: str = "normal"):
    """创建指标卡片"""
    delta_html = ""
    if delta:
        color = {"positive": "#4CAF50", "negative": "#f44336", "normal": "#666"}.get(delta_color, "#666")
        delta_html = f'<span style="color: {color}; font-size: 0.8em;">{delta}</span>'

    html = f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.9em; color: #666;">{label}</span>
                {delta_html}
            </div>
            <div style="font-size: 1.5em; font-weight: bold; margin-top: 8px;">{value}</div>
        </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def initialize_theme():
    """初始化主题"""
    # 应用自定义样式
    apply_custom_styles()

    # 检查是否启用暗色主题
    if st.session_state.get('dark_theme', False):
        apply_dark_theme()


# 主题切换函数
def toggle_theme():
    """切换明暗主题"""
    current_theme = st.session_state.get('dark_theme', False)
    st.session_state.dark_theme = not current_theme

    if st.session_state.dark_theme:
        apply_dark_theme()
    else:
        apply_custom_styles()

    st.rerun()
