# -*- coding: utf-8 -*-
"""
@File    : streamlit_app.py
@Time    : 2025/12/9 14:43
@Desc    : 
"""
import sys
import asyncio
from pathlib import Path

import streamlit as st
import pandas as pd

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.langgraph_api import (
    chat, create_knowledge_base, list_knowledge_bases,
    search_knowledge_base, list_tools, call_tool
)

# 页面配置
st.set_page_config(
    page_title="LangGraph-AgentForge",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化session state
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "current_kb" not in st.session_state:
    st.session_state.current_kb = "default"

if "available_tools" not in st.session_state:
    st.session_state.available_tools = []


def init_session():
    """初始化会话"""
    asyncio.run(load_tools())
    asyncio.run(load_knowledge_bases())


async def load_tools():
    """加载工具列表"""
    try:
        tools_data = await list_tools()
        st.session_state.available_tools = tools_data.get("tools", [])
    except:
        st.session_state.available_tools = []


async def load_knowledge_bases():
    """加载知识库列表"""
    try:
        kbs_data = await list_knowledge_bases()
        st.session_state.knowledge_bases = kbs_data.get("knowledge_bases", [])
    except:
        st.session_state.knowledge_bases = []


def main():
    """主界面"""
    st.title("🤖 LangGraph-AgentForge")
    st.caption("基于LangGraph实现的智能对话系统")

    # 侧边栏
    with st.sidebar:
        st.header("设置")

        # 模型选择
        model_option = st.selectbox(
            "选择模型",
            ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet", "本地模型"]
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
        if st.session_state.available_tools:
            st.subheader("可用工具")
            for tool in st.session_state.available_tools:
                st.caption(f"🔧 {tool.get('name')}: {tool.get('description', '')}")

        # 清空对话
        if st.button("清空对话历史"):
            st.session_state.conversation_history = []
            st.rerun()

        # 系统状态
        st.divider()
        st.subheader("系统状态")
        st.metric("对话轮数", len(st.session_state.conversation_history))

        if st.session_state.knowledge_bases:
            kb_info = next(
                (kb for kb in st.session_state.knowledge_bases if kb["name"] == selected_kb),
                {}
            )
            st.metric("知识库文档数", kb_info.get("document_count", 0))

    # 主聊天区域
    chat_container = st.container()

    with chat_container:
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

        # 输入区域
        user_input = st.chat_input("请输入您的问题...")

        if user_input:
            # 添加用户消息
            with st.chat_message("user"):
                st.write(user_input)

            st.session_state.conversation_history.append({
                "role": "user",
                "content": user_input
            })

            # 生成助手回复
            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    try:
                        # 准备历史
                        history = st.session_state.conversation_history[:-1]

                        # 调用API
                        response = asyncio.run(chat(
                            query=user_input,
                            history=history,
                            knowledge_base_name=st.session_state.current_kb,
                            use_knowledge_base=use_kb
                        ))

                        # 显示回复
                        st.write(response.response)

                        # 显示来源
                        if response.sources:
                            with st.expander("查看信息来源"):
                                for source in response.sources:
                                    st.caption(f"📄 {source.get('source', '未知')}")
                                    st.caption(source.get("content", "")[:200])

                        # 添加到历史
                        st.session_state.conversation_history.append({
                            "role": "assistant",
                            "content": response.response,
                            "sources": response.sources
                        })

                    except Exception as e:
                        st.error(f"请求失败: {str(e)}")


def knowledge_base_page():
    """知识库管理页面"""
    st.title("📚 知识库管理")

    tab1, tab2, tab3 = st.tabs(["创建知识库", "搜索知识库", "知识库列表"])

    with tab1:
        st.subheader("创建新知识库")

        kb_name = st.text_input("知识库名称", value="my_knowledge_base")

        col1, col2 = st.columns(2)
        with col1:
            chunk_size = st.number_input("分块大小", min_value=100, max_value=2000, value=500)
        with col2:
            chunk_overlap = st.number_input("重叠大小", min_value=0, max_value=500, value=50)

        uploaded_files = st.file_uploader(
            "上传文档",
            type=["pdf", "txt", "md", "docx"],
            accept_multiple_files=True
        )

        if st.button("创建知识库") and uploaded_files:
            with st.spinner("正在创建知识库..."):
                try:
                    # 保存上传的文件
                    file_paths = []
                    for uploaded_file in uploaded_files:
                        file_path = f"./uploads/{uploaded_file.name}"
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        file_paths.append(file_path)

                    # 调用API创建知识库
                    response = asyncio.run(create_knowledge_base(
                        kb_name=kb_name,
                        file_paths=file_paths,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    ))

                    st.success(f"知识库 '{kb_name}' 创建成功！")
                    st.metric("文档数量", response.document_count)

                except Exception as e:
                    st.error(f"创建失败: {str(e)}")

    with tab2:
        st.subheader("搜索知识库")

        kb_names = [kb["name"] for kb in st.session_state.get("knowledge_bases", [])]
        selected_kb = st.selectbox("选择知识库", kb_names if kb_names else ["default"])

        search_query = st.text_input("搜索查询")

        if st.button("搜索") and search_query:
            with st.spinner("搜索中..."):
                try:
                    results = asyncio.run(search_knowledge_base(
                        kb_name=selected_kb,
                        query=search_query,
                        k=5
                    ))

                    st.metric("搜索结果数", results["count"])

                    for i, result in enumerate(results["results"], 1):
                        with st.expander(f"结果 {i} (相似度: {result['score']:.3f})"):
                            st.write(result["content"])
                            st.caption(f"来源: {result['source']}")

                except Exception as e:
                    st.error(f"搜索失败: {str(e)}")

    with tab3:
        st.subheader("知识库列表")

        if st.session_state.get("knowledge_bases"):
            df = pd.DataFrame(st.session_state.knowledge_bases)
            st.dataframe(df)
        else:
            st.info("暂无知识库")


def tools_page():
    """工具管理页面"""
    st.title("🔧 工具管理")

    # 工具列表
    st.subheader("可用工具")

    if not st.session_state.available_tools:
        st.info("正在加载工具列表...")
        asyncio.run(load_tools())

    for tool in st.session_state.available_tools:
        with st.expander(f"{tool.get('name')}"):
            st.write(tool.get("description", ""))

            # 工具参数
            if tool.get("inputSchema"):
                st.caption("参数模式:")
                st.json(tool["inputSchema"])

            # 工具测试
            if st.button(f"测试 {tool.get('name')}", key=f"test_{tool.get('name')}"):
                # 根据工具类型提供不同的测试界面
                if tool.get("name") == "calculator":
                    expression = st.text_input("输入表达式", value="2 + 3 * 4")
                    if st.button("计算"):
                        try:
                            result = asyncio.run(call_tool(
                                tool_name="calculator",
                                arguments={"expression": expression}
                            ))
                            st.success(f"结果: {result['result']}")
                        except Exception as e:
                            st.error(f"计算失败: {str(e)}")

                elif tool.get("name") == "web_search":
                    query = st.text_input("搜索查询", value="人工智能")
                    if st.button("搜索"):
                        try:
                            result = asyncio.run(call_tool(
                                tool_name="web_search",
                                arguments={"query": query, "max_results": 3}
                            ))
                            st.success("搜索完成")
                            st.write(result["result"])
                        except Exception as e:
                            st.error(f"搜索失败: {str(e)}")


# 导航
st.sidebar.title("导航")
page = st.sidebar.radio(
    "选择页面",
    ["智能体对话", "知识库管理", "工具管理"]
)

# 初始化
init_session()

# 页面路由
if page == "智能体对话":
    main()
elif page == "知识库管理":
    knowledge_base_page()
elif page == "工具管理":
    tools_page()
