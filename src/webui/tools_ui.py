# -*- coding: utf-8 -*-
"""
@File    : tools_ui.py
@Time    : 2025/12/9 15:54
@Desc    : 工具管理界面
"""
import asyncio
import streamlit as st
from src.api.api_compat import list_tools, call_tool


async def load_tools():
    """加载工具列表"""
    try:
        tools_data = await list_tools()
        st.session_state.available_tools = tools_data.get("mcp", [])
        return True
    except Exception as e:
        st.error(f"加载工具列表失败: {str(e)}")
        st.session_state.available_tools = []
        return False


def get_tool_category(tool_name: str) -> str:
    """根据工具名称获取分类"""
    categories = {
        "calculator": "🧮 计算工具",
        "web_search": "🌐 搜索工具",
        "knowledge_base": "📚 知识库工具",
        "file_loader": "📁 文件处理",
        "api_call": "🔌 API工具"
    }

    for key, category in categories.items():
        if key in tool_name.lower():
            return category

    return "🔧 其他工具"


def render_tool_tester(tool):
    """渲染工具测试界面"""
    tool_name = tool.get('name')

    # 根据工具类型提供不同的测试界面
    if tool_name == "calculator":
        return render_calculator_tester()
    elif tool_name == "web_search":
        return render_web_search_tester()
    elif tool_name == "knowledge_base":
        return render_knowledge_base_tester()
    else:
        return render_generic_tester(tool)


def render_calculator_tester():
    """渲染计算器测试界面"""
    col1, col2 = st.columns([3, 1])

    with col1:
        expression = st.text_input(
            "输入数学表达式",
            value="2 + 3 * 4",
            placeholder="例如: 2 + 3 * (4 - 1)",
            key="calc_expression"
        )

    with col2:
        if st.button("🧮 计算", type="primary", key="calc_button"):
            if not expression.strip():
                st.error("请输入表达式")
                return

            with st.spinner("计算中..."):
                try:
                    result = asyncio.run(call_tool(
                        tool_name="calculator",
                        arguments={"expression": expression}
                    ))
                    st.success(f"✅ 结果: **{result['result']}**")

                    # 显示计算历史
                    if 'calc_history' not in st.session_state:
                        st.session_state.calc_history = []
                    st.session_state.calc_history.append({
                        'expression': expression,
                        'result': result['result']
                    })

                except Exception as e:
                    st.error(f"❌ 计算失败: {str(e)}")


def render_web_search_tester():
    """渲染网络搜索测试界面"""
    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input(
            "搜索查询",
            value="人工智能发展趋势",
            placeholder="输入搜索关键词...",
            key="search_query"
        )

    with col2:
        max_results = st.number_input(
            "结果数量",
            min_value=1,
            max_value=10,
            value=3,
            key="search_max_results"
        )

    if st.button("🔍 搜索", type="primary", key="search_button"):
        if not query.strip():
            st.error("请输入搜索查询")
            return

        with st.spinner("搜索中..."):
            try:
                result = asyncio.run(call_tool(
                    tool_name="web_search",
                    arguments={
                        "query": query,
                        "max_results": max_results
                    }
                ))

                st.success("✅ 搜索完成")

                # 显示搜索结果
                search_results = result.get("result", [])
                if isinstance(search_results, list):
                    for i, item in enumerate(search_results, 1):
                        with st.container():
                            if isinstance(item, dict):
                                title = item.get('title', f'结果 {i}')
                                url = item.get('url', '')
                                snippet = item.get('snippet', '')

                                st.markdown(f"**{i}. {title}**")
                                if url:
                                    st.caption(f"🔗 {url}")
                                if snippet:
                                    st.write(snippet[:200] + "..." if len(snippet) > 200 else snippet)
                            else:
                                st.write(f"**{i}.** {str(item)}")
                            st.divider()
                else:
                    st.write(result["result"])

            except Exception as e:
                st.error(f"❌ 搜索失败: {str(e)}")


def render_knowledge_base_tester():
    """渲染知识库工具测试界面"""
    st.info("知识库工具测试功能开发中...")
    # TODO: 实现知识库工具测试界面


def render_generic_tester(tool):
    """渲染通用工具测试界面"""
    st.warning(f"工具 '{tool.get('name')}' 的专用测试界面未实现")

    # 显示参数模式
    if tool.get("inputSchema"):
        st.subheader("参数配置")
        st.json(tool["inputSchema"])

        # 通用参数输入
        st.text_area(
            "输入参数 (JSON格式)",
            placeholder='{"param1": "value1", "param2": "value2"}',
            key=f"generic_params_{tool.get('name')}"
        )

        if st.button("🚀 执行工具", key=f"generic_test_{tool.get('name')}"):
            st.info("通用工具测试功能开发中...")


def main():
    """工具管理页面"""
    st.title("🔧 工具管理系统")
    st.caption("管理和测试各种AI工具")

    # 加载工具按钮
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("🔄 刷新工具列表", type="secondary"):
            with st.spinner("加载中..."):
                success = asyncio.run(load_tools())
                if success:
                    st.success("✅ 工具列表已更新")
                st.rerun()

    with col2:
        if st.button("📊 工具统计", type="secondary"):
            show_tool_stats()

    # 工具列表
    st.subheader("🛠️ 可用工具")

    if not st.session_state.get('available_tools'):
        st.info("🔄 正在加载工具列表...")
        success = asyncio.run(load_tools())
        if not success:
            st.error("❌ 无法加载工具列表，请检查API连接")
            return

    tools = st.session_state.available_tools

    if not tools:
        st.warning("⚠️ 没有找到可用的工具")
        st.info("请确保API服务器正在运行且MCP服务已正确配置")
        return

    # 按分类分组显示工具
    tools_by_category = {}
    for tool in tools:
        category = get_tool_category(tool.get('name', 'unknown'))
        if category not in tools_by_category:
            tools_by_category[category] = []
        tools_by_category[category].append(tool)

    # 显示工具统计
    total_tools = len(tools)
    active_tools = len([t for t in tools if t.get('available', True)])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 总工具数", total_tools)
    with col2:
        st.metric("✅ 可用工具", active_tools)
    with col3:
        st.metric("❌ 不可用工具", total_tools - active_tools)

    # 按分类显示工具
    for category, category_tools in tools_by_category.items():
        with st.expander(f"{category} ({len(category_tools)}个)", expanded=True):
            for tool in category_tools:
                render_tool_card(tool)


def render_tool_card(tool):
    """渲染工具卡片"""
    tool_name = tool.get('name', '未知工具')
    description = tool.get('description', '暂无描述')
    available = tool.get('available', True)

    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        status_icon = "✅" if available else "❌"
        st.markdown(f"**{status_icon} {tool_name}**")

    with col2:
        st.caption(description[:100] + "..." if len(description) > 100 else description)

    with col3:
        if available:
            if st.button("🧪 测试", key=f"test_btn_{tool_name}", type="secondary"):
                st.session_state.selected_tool = tool
        else:
            st.button("❌ 不可用", key=f"disabled_{tool_name}", disabled=True)

    # 如果选择了这个工具，显示测试界面
    if st.session_state.get('selected_tool') == tool:
        st.divider()
        render_tool_tester(tool)


def show_tool_stats():
    """显示工具统计信息"""
    tools = st.session_state.get('available_tools', [])

    if not tools:
        st.warning("没有工具数据")
        return

    # 统计信息
    categories = {}
    for tool in tools:
        category = get_tool_category(tool.get('name', 'unknown'))
        categories[category] = categories.get(category, 0) + 1

    st.subheader("📊 工具统计")

    # 显示分类统计
    for category, count in categories.items():
        st.metric(category, count)

    # 显示详细列表
    with st.expander("查看详细工具列表"):
        for tool in tools:
            available = "✅ 可用" if tool.get('available', True) else "❌ 不可用"
            st.write(f"- **{tool.get('name')}**: {available}")
