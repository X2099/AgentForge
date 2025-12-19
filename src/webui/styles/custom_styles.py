# -*- coding: utf-8 -*-
"""
自定义样式和主题
"""
import streamlit as st


def apply_custom_styles():
    """应用自定义样式"""
    # 隐藏默认的Streamlit样式并应用全局样式
    custom_css = """
        <style>
        /* ---------------- Global Reset & Typography ---------------- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1f2937;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Main container background */
        .stApp {
            background-color: #f9fafb; /* Very light gray/white */
        }

        /* ---------------- Scrollbars ---------------- */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: #d1d5db;
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #9ca3af;
        }

        /* ---------------- Layout & Grid System ---------------- */
        /* 强制左右布局 - 确保聊天和会话列表水平排列 */
        .stColumns {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important; /* 防止换行 */
            gap: 0 !important; /* 移除gap，使用自定义分隔 */
            align-items: flex-start !important;
            width: 100% !important;
        }

        .stColumns > div {
            flex-shrink: 0 !important;
            height: fit-content !important;
        }

        /* 左侧聊天区域 (75%) */
        .stColumns > div:first-child {
            flex: 3 !important;
            min-width: 60% !important;
            background-color: white !important;
            padding: 2rem !important;
            min-height: 85vh !important;
            border-radius: 16px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            margin-right: 1rem !important;
            border: 1px solid #f3f4f6;
        }

        /* 中间分隔 (Hidden/Small) */
        .stColumns > div:nth-child(2) {
            flex: 0.1 !important;
            min-width: 8px !important;
            max-width: 12px !important;
            display: flex !important;
            align-items: stretch !important;
            justify-content: center !important;
            padding: 0 !important;
        }

        /* 右侧会话列表区域 (25%) */
        .stColumns > div:last-child {
            flex: 1 !important;
            min-width: 280px !important;
            max-width: 350px !important;
            background-color: #f8f9fa !important;
            padding: 1.5rem !important;
            border-radius: 16px !important;
            box-shadow: -4px 0 12px rgba(0,0,0,0.08) !important;
            overflow-y: auto !important;
            max-height: 85vh !important;
            position: relative !important;
            border: 1px solid #f3f4f6;
        }

        /* ---------------- Chat Input Area ---------------- */
        div[data-testid="stChatInput"] {
            position: fixed;
            bottom: 3.5rem;
            left: 50%;
            transform: translateX(-50%);
            width: min(850px, calc(100% - 4rem));
            z-index: 999;
            background-color: rgba(243, 244, 246, 0.95); /* Elegant light gray (Gray 100) */
            backdrop-filter: blur(12px);
            padding: 1.2rem 1.5rem;
            border-radius: 20px;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.5); /* Subtle inner highlight */
            transition: all 0.3s ease;
        }

        div[data-testid="stChatInput"]:focus-within {
            background-color: rgba(255, 255, 255, 0.98); /* Light up on focus */
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(16, 185, 129, 0.2);
            transform: translateX(-50%) translateY(-2px);
        }
        
        /* Hide the default streamlit input border/background to use our custom one */
        .stChatInputContainer {
            background: transparent !important;
        }
        
        /* ---------------- Components ---------------- */
        
        /* Buttons */
        .stButton button {
            border-radius: 10px;
            font-weight: 600;
            border: none;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            transition: all 0.2s;
            padding: 0.5rem 1rem;
        }

        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        /* Primary Buttons (Streamlit default primary) */
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
        }

        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox select {
            border-radius: 10px;
            border: 1px solid #e5e7eb;
            background-color: #f9fafb;
            padding: 0.5rem 0.75rem;
            transition: all 0.2s;
        }

        .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus {
            background-color: white;
            border-color: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }

        /* Expanders (Session List Items) */
        .stExpander {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }
        
        .stExpander > div:first-child {
            border: 1px solid #e5e7eb !important;
            border-radius: 12px !important;
            background-color: white !important;
            margin-bottom: 0.5rem;
        }
        
        /* ---------------- Chat Messages ---------------- */
        .stChatMessage {
            background-color: transparent !important;
            padding: 1rem !important;
            border-radius: 12px;
            margin-bottom: 1rem;
        }

        .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
            /* User message usually */
        }

        /* Avatars */
        .stChatMessage .stAvatar {
            background-color: #e5e7eb;
            color: #4b5563;
        }
        
        /* ---------------- Typography ---------------- */
        h1, h2, h3 {
            font-weight: 700;
            color: #111827;
            letter-spacing: -0.025em;
        }
        
        p, li, span {
            line-height: 1.6;
        }
        
        /* ---------------- Right Panel Specifics ---------------- */
        
        /* 标题样式 */
        .stColumns > div:last-child .stMarkdown h3 {
            color: #374151 !important;
            font-size: 1.3em !important;
            font-weight: 600 !important;
            margin: 0 0 16px 0 !important;
            padding-bottom: 8px !important;
            border-bottom: 2px solid #10b981 !important;
        }

        /* 第一个标题（会话列表）使用绿色分割线 */
        .stColumns > div:last-child .stMarkdown h3:first-of-type {
            border-bottom-color: #10b981 !important;
        }

        /* 分割线样式 - 更微妙 */
        .stColumns > div:last-child .stDivider {
            margin: 16px 0 !important;
            border-color: #f3f4f6 !important;
            border-width: 1px !important;
        }

        /* 优化按钮样式 */
        .stColumns > div:last-child .stButton > button {
            width: 100% !important;
            margin-bottom: 8px !important;
            border-radius: 6px !important;
        }

        /* 优化expander样式 */
        .stColumns > div:last-child .stExpander {
            background-color: #f8f9fa !important;
            border-radius: 8px !important;
            border: 1px solid #e0e0e0 !important;
            margin-bottom: 16px !important;
        }

        .stColumns > div:last-child .stExpander > div:first-child {
            background-color: #f8f9fa !important;
            border-radius: 8px 8px 0 0 !important;
            border-bottom: 1px solid #e0e0e0 !important;
        }

        .stColumns > div:last-child .stExpander > div:last-child {
            background-color: white !important;
            border-radius: 0 0 8px 8px !important;
        }

        /* 优化会话列表项样式 */
        .stColumns > div:last-child .stExpander .stContainer {
            margin-bottom: 8px !important;
            padding: 8px !important;
            border-radius: 6px !important;
            border: 1px solid #e5e7eb !important;
            background-color: white !important;
            transition: all 0.2s ease !important;
        }

        .stColumns > div:last-child .stExpander .stContainer:hover {
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            transform: translateY(-1px) !important;
        }

        /* 当前会话高亮 */
        .stColumns > div:last-child .stExpander .stContainer:has([data-testid*="session"]:has-text("🔵")) {
            background-color: #dbeafe !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
        }

        /* 响应式调整 */
        @media (max-width: 768px) {
            .stColumns > div:last-child {
                padding: 16px !important;
                margin-left: 0.5rem !important;
            }

            .stColumns > div:last-child .stMarkdown h3 {
                font-size: 1.2em !important;
            }
        }
        
        section[data-testid="stSidebar"] {
            background: #ffffff !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 30px rgba(0,0,0,0.08) !important;
            border: 1px solid #f3f4f6 !important;
        }
        
        section[data-testid="stSidebar"] .block-container {
            padding: 1rem 1rem !important;
        }
        
        section[data-testid="stSidebar"] .stMarkdown h3 {
            color: #374151 !important;
            font-size: 1.15em !important;
            font-weight: 600 !important;
            margin: 0 0 12px 0 !important;
            padding-bottom: 8px !important;
            border-bottom: 2px solid #10b981 !important;
        }
        
        section[data-testid="stSidebar"] .stButton > button {
            width: 100% !important;
            border-radius: 10px !important;
            margin-bottom: 10px !important;
        }
        
        section[data-testid="stSidebar"] .stSelectbox select,
        section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"],
        section[data-testid="stSidebar"] .stTextInput input,
        section[data-testid="stSidebar"] .stNumberInput input {
            background-color: #f9fafb !important;
            border: 1px solid #e5e7eb !important;
            border-radius: 10px !important;
            padding: 0.5rem 0.75rem !important;
        }
        
        section[data-testid="stSidebar"] .stSelectbox select:focus,
        section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"]:focus-within,
        section[data-testid="stSidebar"] .stTextInput input:focus,
        section[data-testid="stSidebar"] .stNumberInput input:focus {
            background-color: #ffffff !important;
            border-color: #10b981 !important;
            box-shadow: 0 0 0 3px rgba(16,185,129,0.1) !important;
        }
        
        section[data-testid="stSidebar"] .stMetric {
            background: #f8fafc !important;
            border: 1px solid #eef2f7 !important;
            border-radius: 12px !important;
            padding: 0.75rem !important;
            margin-bottom: 10px !important;
        }
        </style>
    """

    st.markdown(custom_css, unsafe_allow_html=True)


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
