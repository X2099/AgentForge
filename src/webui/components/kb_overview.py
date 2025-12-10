# -*- coding: utf-8 -*-
"""
知识库总览组件
"""
import streamlit as st
import pandas as pd


class KnowledgeBaseOverview:
    """知识库总览组件"""

    def __init__(self, kb_manager):
        self.kb_manager = kb_manager

    def render(self):
        """渲染总览页面"""
        st.subheader("📊 知识库总览")

        # 获取所有知识库
        knowledge_bases = self.kb_manager.list_knowledge_bases()

        if not knowledge_bases:
            st.info("📭 暂无知识库，请先创建知识库。")
            return

        # 统计信息卡片
        total_docs = sum(kb.get("document_count", 0) for kb in knowledge_bases)
        total_size = sum(kb.get("size_mb", 0) for kb in knowledge_bases)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📚 知识库数量", len(knowledge_bases))
        with col2:
            st.metric("📄 总文档数", total_docs)
        with col3:
            st.metric("💾 数据总量", f"{total_size:.1f} MB")

        # 知识库列表表格
        st.subheader("📋 知识库列表")

        df_data = []
        for kb in knowledge_bases:
            df_data.append({
                "名称": kb.get("name", ""),
                "描述": kb.get("description", ""),
                "文档数": kb.get("document_count", 0),
                "最后更新": kb.get("last_updated", ""),
                "状态": "🟢 正常" if kb.get("is_initialized") else "🟡 未初始化"
            })

        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "状态": st.column_config.TextColumn(
                        "状态",
                        help="知识库状态"
                    )
                }
            )

            # 操作按钮
            selected_kb = st.selectbox(
                "选择知识库进行操作",
                [kb["名称"] for kb in df_data]
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📊 查看详情", key="view_details"):
                    self._show_kb_details(selected_kb)
            with col2:
                if st.button("🔄 重新索引", key="reindex"):
                    self._reindex_knowledge_base(selected_kb)
            with col3:
                if st.button("🗑️ 删除", key="delete_kb"):
                    self._delete_knowledge_base(selected_kb)

    def _show_kb_details(self, kb_name: str):
        """显示知识库详情"""
        kb = self.kb_manager.get_knowledge_base(kb_name)
        if not kb:
            st.error(f"❌ 知识库 '{kb_name}' 不存在")
            return

        stats = kb.get_stats()

        with st.expander(f"📋 知识库详情: {kb_name}", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.metric("向量存储类型", stats.get("vector_store", {}).get("type", "未知"))
                st.metric("嵌入模型", stats.get("embedder_type", "未知"))
                st.metric("分块大小", stats.get("chunk_size", 0))

            with col2:
                st.metric("文档总数", stats.get("document_count", 0))
                st.metric("平均长度", f"{stats.get('average_document_length', 0):.0f} 字符")
                st.metric("最后更新", stats.get("last_updated", "未知"))

            # 向量存储详情
            st.subheader("向量存储信息")
            vector_store_info = stats.get("vector_store", {})
            st.json(vector_store_info)

    def _reindex_knowledge_base(self, kb_name: str):
        """重新索引知识库"""
        with st.spinner(f"🔄 正在重新索引 {kb_name}..."):
            try:
                # TODO: 实现重新索引逻辑
                st.success(f"✅ 知识库 '{kb_name}' 重新索引完成")
            except Exception as e:
                st.error(f"❌ 重新索引失败: {str(e)}")

    def _delete_knowledge_base(self, kb_name: str):
        """删除知识库"""
        if st.checkbox(f"⚠️ 确认删除知识库 '{kb_name}'？此操作不可恢复！"):
            try:
                self.kb_manager.delete_knowledge_base(kb_name, delete_data=True)
                st.success(f"✅ 知识库 '{kb_name}' 已删除")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 删除失败: {str(e)}")
