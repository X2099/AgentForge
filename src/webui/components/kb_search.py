# -*- coding: utf-8 -*-
"""
知识库搜索测试组件
"""
import streamlit as st


class KnowledgeBaseSearch:
    """知识库搜索测试组件"""

    def __init__(self, kb_manager):
        self.kb_manager = kb_manager
        self._available_kbs = None

    def render(self):
        """渲染搜索测试页面"""
        st.subheader("🔍 知识库搜索测试")

        # 选择知识库
        available_kbs = self._get_available_knowledge_bases()
        if not available_kbs:
            st.warning("⚠️ 没有可用的知识库，请先创建知识库")
            return

        selected_kb = st.selectbox(
            "选择知识库",
            options=list(available_kbs.keys()),
            format_func=lambda x: available_kbs[x],
            help="选择要搜索的知识库"
        )

        if selected_kb:
            # 搜索配置
            col1, col2 = st.columns(2)
            with col1:
                query = st.text_input("搜索查询", value="人工智能", placeholder="输入搜索关键词...")
            with col2:
                top_k = st.slider("返回结果数", min_value=1, max_value=20, value=5)

            # 高级搜索选项
            with st.expander("🔧 高级搜索选项"):
                col1, col2 = st.columns(2)
                with col1:
                    similarity_threshold = st.slider(
                        "相似度阈值",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.5,
                        help="过滤低相似度结果"
                    )
                    use_hybrid_search = st.checkbox("混合搜索", value=True)

                with col2:
                    filter_source = st.text_input("来源过滤", help="按来源过滤文档")
                    filter_metadata = st.text_input("元数据过滤", help="JSON格式的元数据过滤")

            # 搜索按钮
            if st.button("🔎 开始搜索", type="primary"):
                self._perform_search(selected_kb, query, top_k)

    def _get_available_knowledge_bases(self):
        """获取可用的知识库列表"""
        if self._available_kbs is None:
            try:
                import requests
                from .. import API_BASE_URL

                # 调用API获取知识库列表
                response = requests.get(f"{API_BASE_URL}/knowledge_base/list", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    kbs = {}
                    for kb in data.get("knowledge_bases", []):
                        kb_name = kb.get("name", "")
                        if kb_name:
                            # 显示名称可以包含文档数量等信息
                            doc_count = kb.get("document_count", 0)
                            display_name = f"{kb_name} ({doc_count} 文档)"
                            kbs[kb_name] = display_name
                    self._available_kbs = kbs
                else:
                    st.error(f"获取知识库列表失败 (状态码: {response.status_code})")
                    self._available_kbs = {}
            except requests.exceptions.ConnectionError:
                st.error("🌐 无法连接到API服务器，请确保服务器正在运行")
                self._available_kbs = {}
            except Exception as e:
                st.error(f"获取知识库列表失败: {str(e)}")
                self._available_kbs = {}
        return self._available_kbs

    def _perform_search(self, kb_name, query, top_k):
        """执行搜索"""
        with st.spinner("🔍 正在搜索中..."):
            try:
                import requests
                from .. import API_BASE_URL

                # 调用后端搜索API
                params = {
                    "kb_name": kb_name,
                    "query": query,
                    "k": top_k
                }

                response = requests.post(f"{API_BASE_URL}/knowledge_base/search", params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        st.info("📭 未找到相关结果")
                        return

                    # 显示统计
                    result_count = len(results)
                    st.metric("找到结果", result_count)

                    # 显示结果
                    for i, result in enumerate(results, 1):
                        with st.container():
                            col1, col2 = st.columns([4, 1])

                            with col1:
                                # 显示内容
                                content = result.get("content", "")
                                if len(content) > 300:
                                    content = content[:300] + "..."

                                st.write(f"**结果 {i}**")
                                st.write(content)

                                # 显示来源
                                source = result.get("source", "未知")
                                st.caption(f"📄 来源: {source}")

                            with col2:
                                # 显示相似度分数
                                score = result.get("score", 0)
                                st.metric("相似度", f"{score:.3f}")

                            st.divider()

                    # 显示搜索详情
                    with st.expander("📊 搜索详情"):
                        search_info = {
                            "知识库": kb_name,
                            "查询": query,
                            "返回结果数": result_count,
                            "API状态": "成功"
                        }
                        st.json(search_info)

                else:
                    st.error(f"搜索请求失败 (状态码: {response.status_code})")
                    st.caption(f"错误详情: {response.text}")

            except requests.exceptions.Timeout:
                st.error("⏰ 搜索超时，请稍后重试或减少返回结果数")
            except requests.exceptions.ConnectionError:
                st.error("🌐 无法连接到API服务器，请确保服务器正在运行")
            except Exception as e:
                st.error(f"❌ 搜索出错: {str(e)}")
                st.caption("请检查网络连接或联系管理员")
