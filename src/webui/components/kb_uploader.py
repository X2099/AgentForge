# -*- coding: utf-8 -*-
"""
知识库文档上传组件
"""
import streamlit as st
from pathlib import Path


class KnowledgeBaseUploader:
    """知识库文档上传组件"""

    def __init__(self, kb_manager):
        self.kb_manager = kb_manager

    def render(self):
        """渲染文档上传页面"""
        st.subheader("📤 上传文档到知识库")

        # 选择目标知识库
        available_kbs = self._get_available_knowledge_bases()
        if not available_kbs:
            st.warning("⚠️ 没有可用的知识库，请先创建知识库")
            return

        selected_kb = st.selectbox(
            "选择目标知识库",
            options=list(available_kbs.keys()),
            format_func=lambda x: available_kbs[x],
            help="选择要上传文档的知识库"
        )

        if selected_kb:
            # 显示知识库信息
            kb_info = self._get_kb_info(selected_kb)
            if kb_info:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("文档数量", kb_info.get("document_count", 0))
                with col2:
                    st.metric("向量维度", kb_info.get("vector_dim", "未知"))
                with col3:
                    st.metric("状态", "活跃" if kb_info.get("active", False) else "离线")

            # 文件上传区域
            self._render_file_upload(selected_kb)

            # 上传按钮
            self._render_upload_button(selected_kb)

    def _get_available_knowledge_bases(self):
        """获取可用的知识库列表"""
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
                        # 格式化为显示名称，可以添加更多信息如文档数量等
                        display_name = f"{kb_name}"
                        kbs[kb_name] = display_name
                return kbs
            else:
                st.error(f"获取知识库列表失败 (状态码: {response.status_code})")
                return {}
        except requests.exceptions.ConnectionError:
            st.error("🌐 无法连接到API服务器，请确保服务器正在运行")
            return {}
        except Exception as e:
            st.error(f"获取知识库列表失败: {str(e)}")
            return {}

    def _get_kb_info(self, kb_name):
        """获取知识库信息"""
        try:
            import requests
            from .. import API_BASE_URL

            # 调用API获取知识库统计信息
            response = requests.get(f"{API_BASE_URL}/knowledge_base/list", timeout=5)
            if response.status_code == 200:
                data = response.json()
                for kb in data.get("knowledge_bases", []):
                    if kb.get("name") == kb_name:
                        # 返回知识库信息，添加默认值
                        return {
                            "document_count": kb.get("document_count", 0),
                            "vector_dim": kb.get("vector_dim", 768),  # 默认768维
                            "active": True  # 假设存在的知识库都是活跃的
                        }
                return None
            else:
                st.warning(f"获取知识库信息失败 (状态码: {response.status_code})")
                return None
        except requests.exceptions.ConnectionError:
            st.warning("🌐 无法连接到API服务器，显示默认信息")
            return {
                "document_count": 0,
                "vector_dim": "未知",
                "active": False
            }
        except Exception as e:
            st.warning(f"获取知识库信息失败: {str(e)}")
            return None

    def _render_file_upload(self, kb_name):
        """渲染文件上传区域"""
        st.subheader("📁 选择要上传的文件")

        upload_method = st.radio(
            "上传方式",
            ["本地文件上传", "文件夹批量导入", "网络链接导入"],
            key=f"upload_method_{kb_name}"
        )

        file_paths = []

        if upload_method == "本地文件上传":
            uploaded_files = st.file_uploader(
                "选择文档文件",
                type=["pdf", "txt", "md", "docx", "html", "csv"],
                accept_multiple_files=True,
                help="支持PDF、TXT、Markdown、Word、HTML、CSV格式",
                key=f"file_uploader_{kb_name}"
            )

            if uploaded_files:
                # 显示文件列表
                st.write("已选择文件:")
                for uploaded_file in uploaded_files:
                    st.write(f"- {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

                # 保存文件
                upload_dir = Path(f"./uploads/{kb_name}")
                upload_dir.mkdir(parents=True, exist_ok=True)

                for uploaded_file in uploaded_files:
                    file_path = upload_dir / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    file_paths.append(str(file_path))

        elif upload_method == "文件夹批量导入":
            folder_path = st.text_input(
                "文件夹路径",
                value="./data/documents",
                help="包含文档文件的文件夹路径",
                key=f"folder_path_{kb_name}"
            )

            if st.button("扫描文件夹", key=f"scan_folder_{kb_name}"):
                folder = Path(folder_path)
                if folder.exists() and folder.is_dir():
                    # 查找支持的文档文件
                    supported_extensions = ['.pdf', '.txt', '.md', '.docx', '.html', '.csv']
                    for ext in supported_extensions:
                        for file in folder.glob(f"**/*{ext}"):
                            file_paths.append(str(file))

                    st.success(f"找到 {len(file_paths)} 个文档文件")

                    # 显示文件列表
                    with st.expander("查看文件列表"):
                        for fp in file_paths[:20]:  # 限制显示数量
                            st.write(f"- {Path(fp).name}")
                        if len(file_paths) > 20:
                            st.write(f"... 还有 {len(file_paths) - 20} 个文件")
                else:
                    st.error("文件夹不存在或路径无效")

        elif upload_method == "网络链接导入":
            urls = st.text_area(
                "输入URL列表（每行一个）",
                height=100,
                help="输入文档的URL链接，每行一个",
                key=f"urls_{kb_name}"
            )

            if urls:
                url_list = [url.strip() for url in urls.split('\n') if url.strip()]
                file_paths.extend(url_list)
                st.info(f"添加了 {len(url_list)} 个网络链接")

        # 存储文件路径到session state
        st.session_state[f"upload_file_paths_{kb_name}"] = file_paths

    def _render_upload_button(self, kb_name):
        """渲染上传按钮"""
        st.divider()

        file_paths = st.session_state.get(f"upload_file_paths_{kb_name}", [])

        if st.button("📤 开始上传", type="primary", disabled=not file_paths, key=f"upload_btn_{kb_name}"):
            with st.spinner("正在上传文档..."):
                try:
                    # 调用API上传文档
                    import requests
                    from .. import API_BASE_URL

                    payload = {
                        "kb_name": kb_name,
                        "file_paths": file_paths
                    }

                    response = requests.post(f"{API_BASE_URL}/knowledge_base/upload_documents", json=payload, timeout=300)

                    if response.status_code == 200:
                        result = response.json()

                        # 显示结果
                        st.success("🎉 文档上传成功！")

                        # 显示统计信息
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("处理文件", result.get("processed_files", 0))
                        with col2:
                            st.metric("失败文件", result.get("failed_files", 0))
                        with col3:
                            st.metric("总文本块", result.get("total_chunks", 0))
                        with col4:
                            st.metric("有效块", result.get("valid_chunks", 0))

                        # 显示详细结果
                        with st.expander("📊 详细处理结果"):
                            st.json(result)

                        # 清空上传的文件路径
                        st.session_state[f"upload_file_paths_{kb_name}"] = []

                        # 刷新页面以更新知识库信息
                        st.rerun()

                    else:
                        st.error(f"上传失败 (状态码: {response.status_code})")
                        st.caption(f"错误详情: {response.text}")

                except requests.exceptions.Timeout:
                    st.error("⏰ 上传超时，请稍后重试或减少文件数量")
                except requests.exceptions.ConnectionError:
                    st.error("🌐 网络连接失败，请检查服务器是否运行")
                except Exception as e:
                    st.error(f"❌ 上传出错: {str(e)}")
                    st.caption("请检查网络连接或联系管理员")
