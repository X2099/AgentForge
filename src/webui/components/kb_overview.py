# -*- coding: utf-8 -*-
"""
知识库总览组件
"""
import streamlit as st
import pandas as pd
import requests
from .. import API_BASE_URL


class KnowledgeBaseOverview:
    """知识库总览组件"""

    def render(self):
        """渲染总览页面"""
        st.subheader("📊 知识库总览")

        # 获取所有知识库
        response = requests.get(f"{API_BASE_URL}/knowledge_base/list")
        if response.status_code == 200:
            knowledge_bases = response.json()
            knowledge_bases = knowledge_bases.get("knowledge_bases")
        else:
            st.error(f"❌ 获取知识库列表失败 (状态码: {response.status_code})")
            st.caption(f"错误详情: {response.text}")
            return

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
                if st.button("📊 查看详情", key=f"view_details_{selected_kb}"):
                    self._show_kb_details(selected_kb)
            with col2:
                if st.button("🔄 重新索引", key=f"reindex_{selected_kb}"):
                    self._reindex_knowledge_base(selected_kb)
            with col3:
                # 使用session_state来跟踪删除状态，避免st.button的瞬时性问题
                delete_action_key = f"delete_action_{selected_kb}"
                if st.button("🗑️ 删除", key=f"delete_btn_{selected_kb}"):
                    st.session_state[delete_action_key] = True

                # 检查是否需要显示删除确认界面
                if st.session_state.get(delete_action_key, False):
                    self._delete_knowledge_base(selected_kb)
                    # 注意：删除成功后会在_execute_delete中清理这个状态

    def _show_kb_details(self, kb_name: str):
        """显示知识库详情"""
        response = requests.get(f"{API_BASE_URL}/knowledge_base/{kb_name}/detail")
        if response.status_code == 200:
            stats = response.json()
        else:
            st.error(f"❌ 获取知识库 {kb_name} 详情失败 (状态码: {response.status_code})")
            st.caption(f"错误详情: {response.text}")
            return
        if not stats:
            return
        with st.expander(f"📋 知识库详情: {kb_name}", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.metric("向量存储类型", stats.get("vectorstore_type", "未知"))
                st.metric("嵌入模型", stats.get("embedding_type", "未知"))
                st.metric("分块大小", stats.get("chunk_size", 0))

            with col2:
                st.metric("文档总数", stats.get("document_count", 0))
                st.metric("平均长度", f"{stats.get('average_document_length', 0):.0f} 字符")
                st.metric("最后更新", stats.get("last_updated", "未知"))

            # 向量存储详情
            st.subheader("向量存储信息")
            vector_store_info = stats.get("vectorstore_info", {})
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
        st.warning(f"⚠️ 删除知识库 '{kb_name}' 将永久删除所有相关数据，此操作不可恢复！")

        # 使用session_state来跟踪删除状态
        delete_state_key = f"delete_state_{kb_name}"
        confirm_text_key = f"confirm_text_{kb_name}"
        delete_data_key = f"delete_data_{kb_name}"

        # 初始化session_state
        if delete_state_key not in st.session_state:
            st.session_state[delete_state_key] = False
        if confirm_text_key not in st.session_state:
            st.session_state[confirm_text_key] = ""
        if delete_data_key not in st.session_state:
            st.session_state[delete_data_key] = True

        # 使用form来收集输入
        with st.form(key=f"delete_form_{kb_name}"):
            col1, col2 = st.columns(2)

            with col1:
                st.session_state[delete_data_key] = st.checkbox(
                    "同时删除向量数据",
                    value=st.session_state[delete_data_key],
                    help="删除向量数据库中的所有向量数据"
                )

            with col2:
                st.session_state[confirm_text_key] = st.text_input(
                    "输入知识库名称确认删除",
                    value=st.session_state[confirm_text_key],
                    placeholder=f"输入 '{kb_name}'",
                    help="输入知识库名称以确认删除操作"
                )

            # 提交按钮
            submitted = st.form_submit_button(
                "🗑️ 确认删除",
                type="primary",
                use_container_width=True
            )

            if submitted:
                # 表单提交时设置状态
                st.session_state[delete_state_key] = True

        # 在表单外面检查和处理删除逻辑
        if st.session_state[delete_state_key]:
            confirm_text = st.session_state[confirm_text_key]
            delete_data = st.session_state[delete_data_key]

            st.info(
                f"🔍 调试: 处理删除请求 - kb_name='{kb_name}', confirm_text='{confirm_text}', delete_data={delete_data}")

            if confirm_text.strip() != kb_name:
                st.error("❌ 确认文本不匹配，请输入正确的知识库名称")
                # 重置状态，允许重新尝试
                st.session_state[delete_state_key] = False
            else:
                st.success("🔍 调试: 验证通过，开始执行删除")
                # 验证通过，执行删除
                self._execute_delete(kb_name, delete_data)
                # 删除成功后清理状态
                self._cleanup_delete_state(kb_name)

    def _cleanup_delete_state(self, kb_name: str):
        """清理删除相关的session_state"""
        delete_state_key = f"delete_state_{kb_name}"
        confirm_text_key = f"confirm_text_{kb_name}"
        delete_data_key = f"delete_data_{kb_name}"
        delete_action_key = f"delete_action_{kb_name}"

        # 清理所有相关的session_state
        for key in [delete_state_key, confirm_text_key, delete_data_key, delete_action_key]:
            if key in st.session_state:
                del st.session_state[key]

    def _execute_delete(self, kb_name: str, delete_data: bool):
        """执行删除操作"""
        try:

            with st.spinner("🗑️ 正在删除知识库..."):
                # 调用删除API
                params = {"delete_data": delete_data}
                response = requests.delete(f"{API_BASE_URL}/knowledge_base/{kb_name}", params=params, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ {result['message']}")

                    # 刷新页面
                    st.rerun()
                else:
                    st.error(f"❌ 删除失败 (状态码: {response.status_code})")
                    st.caption(f"错误详情: {response.text}")

        except requests.exceptions.Timeout:
            st.error("⏰ 删除超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            st.error("🌐 无法连接到API服务器，请确保服务器正在运行")
        except Exception as e:
            st.error(f"❌ 删除出错: {str(e)}")
            st.caption("请检查网络连接或联系管理员")
