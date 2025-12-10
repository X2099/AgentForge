# -*- coding: utf-8 -*-
"""
知识库搜索测试组件
"""
import streamlit as st


class KnowledgeBaseSearch:
    """知识库搜索测试组件"""

    def __init__(self, kb_manager):
        self.kb_manager = kb_manager

    def render(self):
        """渲染搜索测试页面"""
        st.subheader("🔍 知识库搜索测试")

        # 选择知识库
        knowledge_bases = self.kb_manager.list_knowledge_bases()
        if not knowledge_bases:
            st.warning("请先创建知识库")
            return

        kb_names = [kb["name"] for kb in knowledge_bases]
        selected_kb = st.selectbox("选择知识库", kb_names)

        if selected_kb:
            kb = self.kb_manager.get_knowledge_base(selected_kb)
            if not kb:
                st.error(f"知识库 '{selected_kb}' 不存在")
                return

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
                self._perform_search(kb, query, top_k)

    def _perform_search(self, kb, query, top_k):
        """执行搜索"""
        with st.spinner("搜索中..."):
            try:
                # 执行搜索
                results = kb.search(query, k=top_k)

                if not results:
                    st.info("未找到相关结果")
                    return

                # 显示统计
                st.metric("找到结果", len(results))

                # 显示结果
                for i, doc in enumerate(results, 1):
                    with st.container():
                        col1, col2 = st.columns([4, 1])

                        with col1:
                            # 显示内容
                            content = doc.content
                            if len(content) > 300:
                                content = content[:300] + "..."

                            st.write(f"**结果 {i}**")
                            st.write(content)

                            # 显示元数据
                            metadata = doc.metadata
                            source = metadata.get("source", "未知")
                            st.caption(f"来源: {source}")

                        with col2:
                            # 显示相似度分数
                            similarity = metadata.get("similarity_score", 0)
                            st.metric("相似度", f"{similarity:.3f}")

                        st.divider()

                # 显示向量搜索信息
                with st.expander("📊 搜索详情"):
                    st.json({
                        "query": query,
                        "vector_store": kb.config.get("vector_store", {}).get("store_type"),
                        "embedder": kb.config.get("embedder", {}).get("embedder_type"),
                        "results_count": len(results)
                    })

            except Exception as e:
                st.error(f"搜索失败: {str(e)}")
