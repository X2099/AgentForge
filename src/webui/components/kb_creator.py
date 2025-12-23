# -*- coding: utf-8 -*-
"""
知识库创建组件
"""
import streamlit as st
import requests
from .. import API_BASE_URL


class KnowledgeBaseCreator:
    """知识库创建组件"""

    def __init__(self):
        self._vector_store_options = None
        self._embedder_options = None

    def _get_vector_store_options(self):
        """获取向量存储选项"""
        if self._vector_store_options is None:
            try:
                response = requests.get(f"{API_BASE_URL}/vector-stores/list", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self._vector_store_options = data.get("vector_stores", [])
                else:
                    st.error(f"❌ 获取向量库列表失败 (状态码: {response.status_code})")
                    st.caption(f"错误详情: {response.text}")
                    return
            except Exception as e:
                # 网络错误，使用默认选项
                st.error(f"❌ 获取向量库列表异常：{e}")
                st.caption(f"错误详情: {e}")
                return
        return self._vector_store_options

    def _get_embedder_options(self):
        """获取嵌入器选项"""
        if self._embedder_options is None:
            try:
                response = requests.get(f"{API_BASE_URL}/embedders/list", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self._embedder_options = data.get("embedders", [])
                else:
                    st.error(f"❌ 获取embeddings模型列表失败 (状态码: {response.status_code})")
                    st.caption(f"错误详情: {response.text}")
                    return
            except Exception as e:
                # 网络错误，使用默认选项
                st.error(f"❌ 获取embeddings模型列表异常：{e}")
                st.caption(f"错误详情: {e}")
        return self._embedder_options

    def render(self):
        """渲染创建知识库页面"""
        st.subheader("🚀 创建新知识库")

        # 知识库基本信息
        col1, col2 = st.columns(2)
        with col1:
            kb_name = st.text_input("知识库名称", placeholder="只能使用字母、数字和_，不能以数字开头")
        with col2:
            kb_description = st.text_input("描述", placeholder="知识库描述")

        # 向量存储配置
        self._render_vector_config()

        # 嵌入模型配置
        self._render_embedder_config()

        # 文本处理配置
        self._render_text_config()

        # 创建按钮
        self._render_create_button(kb_name, kb_description)

    def _render_vector_config(self):
        """渲染向量存储配置"""
        st.subheader("💾 向量存储配置")

        vector_config_col1, vector_config_col2 = st.columns(2)

        with vector_config_col1:
            # 获取向量存储类型列表
            vector_store_options = self._get_vector_store_options()
            vector_store_type = st.selectbox(
                "向量数据库",
                options=[opt["type"] for opt in vector_store_options],
                format_func=lambda x: next((opt["name"] for opt in vector_store_options if opt["type"] == x), x)
            )

        with vector_config_col2:
            # 向量存储特定配置
            if vector_store_type == "chroma":
                collection_name = st.text_input("集合名称", placeholder="不填的话默认同知识库名")

            elif vector_store_type == "faiss":
                index_type = st.selectbox(
                    "索引类型",
                    ["Flat", "IVF", "HNSW"],
                    help="FAISS索引算法"
                )
                nlist = st.number_input("聚类数量", min_value=1, max_value=10000,
                                        value=100) if index_type == "IVF" else None

            elif vector_store_type == "milvus":
                host = st.text_input("Milvus地址", value="localhost")
                port = st.number_input("端口", min_value=1, max_value=65535, value=19530)
                collection_name = st.text_input("集合名称", value=st.session_state.get('kb_name', 'kb'))

        # 存储配置到session state
        st.session_state.vector_config = {
            'store_type': vector_store_type,
            'persist_dir': locals().get('persist_dir'),
            'collection_name': locals().get('collection_name'),
            'host': locals().get('host'),
            'port': locals().get('port'),
            'index_type': locals().get('index_type'),
            'nlist': locals().get('nlist')
        }

    def _render_embedder_config(self):
        """渲染嵌入模型配置"""
        st.subheader("🧠 嵌入模型配置")

        embed_config_col1, embed_config_col2 = st.columns(2)

        with embed_config_col1:
            # 获取嵌入器类型选项
            embedder_options = self._get_embedder_options()
            embedder_type = st.selectbox(
                "嵌入模型类型",
                options=[opt["type"] for opt in embedder_options],
                format_func=lambda x: next((opt["name"] for opt in embedder_options if opt["type"] == x), x),
                help="选择要使用的嵌入模型类型"
            )

            # 获取当前选中嵌入器的模型列表
            embedder_options = self._get_embedder_options()
            current_embedder = next((opt for opt in embedder_options if opt["type"] == embedder_type), None)

            if current_embedder and "models" in current_embedder:
                # 从配置中获取模型选项
                model_options = current_embedder["models"]
                model_names = [model["name"] for model in model_options]

                # 添加自定义选项（如果需要）
                if embedder_type == "local":
                    model_names.append("自定义模型路径")

                model_name = st.selectbox(
                    "模型",
                    model_names,
                    format_func=lambda x: next(
                        (f'{model["name"]} - {model["description"]}' for model in model_options if model["name"] == x),
                        x),
                    help="选择要使用的具体模型"
                )

                # 如果是自定义模型路径，显示输入框
                if model_name == "自定义模型路径":
                    model_name = st.text_input("模型路径")

                # 显示模型维度信息（如果可用）
                selected_model_info = next((model for model in model_options if model["name"] == model_name), None)
                if selected_model_info and "dimensions" in selected_model_info:
                    st.info(f"📏 向量维度: {selected_model_info['dimensions']}")

            else:
                st.caption(f"未获取到有效的嵌入模型配置。")
                return

                # OpenAI特有的配置
            if embedder_type == "openai":
                openai_key = st.text_input("OpenAI API Key", type="password")

            # BGE特有的配置
            if embedder_type == "bge":
                normalize_embeddings = st.checkbox("归一化向量", value=True)

        with embed_config_col2:
            # 通用嵌入配置
            batch_size = st.number_input(
                "批处理大小",
                min_value=1,
                max_value=1000,
                value=32,
                help="批量处理文本的数量"
            )
            device = st.selectbox(
                "运行设备",
                ["cpu", "cuda"],
                help="模型运行设备"
            )

        # 存储配置到session state
        st.session_state.embedder_config = {
            'embedder_type': embedder_type,
            'model_name': locals().get('model_name'),
            'openai_key': locals().get('openai_key'),
            'dimensions': locals().get('dimensions'),
            'normalize_embeddings': locals().get('normalize_embeddings'),
            'batch_size': batch_size,
            'device': device
        }

    def _render_text_config(self):
        """渲染文本处理配置"""
        st.subheader("📝 文本处理配置")

        text_config_col1, text_config_col2 = st.columns(2)

        with text_config_col1:
            # 分割器配置
            splitter_type = st.selectbox(
                "分割器类型",
                ["recursive", "semantic", "fixed"],
                format_func=lambda x: {
                    "recursive": "递归分割 (推荐)",
                    "semantic": "语义分割",
                    "fixed": "固定长度分割"
                }[x]
            )

            chunk_size = st.number_input(
                "分块大小",
                min_value=100,
                max_value=2000,
                value=500,
                help="每个文本块的最大字符数"
            )

        with text_config_col2:
            chunk_overlap = st.number_input(
                "重叠大小",
                min_value=0,
                max_value=500,
                value=50,
                help="相邻文本块之间的重叠字符数"
            )

            if splitter_type == "semantic":
                semantic_threshold = st.slider(
                    "语义相似度阈值",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    help="句子合并的相似度阈值"
                )
                semantic_model = st.selectbox(
                    "语义分割模型",
                    ["paraphrase-multilingual-MiniLM-L12-v2", "all-MiniLM-L6-v2"]
                )

        # 存储配置到session state
        st.session_state.text_config = {
            'splitter_type': splitter_type,
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap,
            'semantic_threshold': locals().get('semantic_threshold'),
            'semantic_model': locals().get('semantic_model')
        }

    def _render_create_button(self, kb_name, kb_description):
        """渲染创建按钮"""
        st.divider()

        if st.button("🚀 创建知识库", type="primary"):
            with st.spinner("正在创建知识库..."):
                try:
                    # 构建配置
                    kb_config = self._build_kb_config(kb_name, kb_description)
                    # 调用API创建空的知识库
                    payload = {
                        "kb_name": kb_name,
                        "kb_desc": kb_description,
                        "splitter_type": kb_config["splitter_type"],
                        "chunk_size": kb_config["chunk_size"],
                        "chunk_overlap": kb_config["chunk_overlap"],
                        "embedder": kb_config["embedder"],
                        "vector_store": kb_config["vector_store"],
                        "semantic_config": kb_config.get("semantic_config", {})
                    }

                    response = requests.post(f"{API_BASE_URL}/knowledge_base/create", json=payload, timeout=60)

                    if response.status_code == 200:
                        result = response.json()

                        # 显示结果
                        st.success("🎉 知识库创建成功！")
                        st.info("💡 知识库已创建完成，您可以在'上传文件'页面中添加文档。")

                        # 显示知识库信息
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("知识库名称", result["kb_name"])
                        with col2:
                            st.metric("初始文档数", result["document_count"])

                        # 刷新知识库列表
                        st.rerun()

                    else:
                        st.error(f"创建失败 (状态码: {response.status_code})")
                        st.caption(f"错误详情: {response.text}")

                except requests.exceptions.Timeout:
                    st.error("⏰ 创建超时，请稍后重试")
                except requests.exceptions.ConnectionError:
                    st.error("🌐 网络连接失败，请检查服务器是否运行")
                except Exception as e:
                    st.error(f"❌ 创建出错: {str(e)}")
                    st.caption("请检查网络连接或联系管理员")

    def _build_kb_config(self, kb_name, kb_description):
        """构建知识库配置"""
        vector_config = st.session_state.get('vector_config', {})
        embedder_config = st.session_state.get('embedder_config', {})
        text_config = st.session_state.get('text_config', {})

        kb_config = {
            "name": kb_name,
            "description": kb_description,
            "splitter_type": text_config.get('splitter_type'),
            "chunk_size": text_config.get('chunk_size'),
            "chunk_overlap": text_config.get('chunk_overlap'),
            "embedder": {
                "embedder_type": embedder_config.get('embedder_type'),
                "model": embedder_config.get('model_name'),
                "dimensions": embedder_config.get('dimensions'),
                "normalize_embeddings": embedder_config.get('normalize_embeddings'),
                "device": embedder_config.get('device', 'cpu')
            },
            "vector_store": {
                "store_type": vector_config.get('store_type', 'chroma'),
                "collection_name": vector_config.get('collection_name', kb_name),
                "host": vector_config.get('host'),
                "port": vector_config.get('port')
            }
        }

        # 添加语义分割特定配置
        if text_config.get('splitter_type') == "semantic":
            kb_config["semantic_config"] = {
                "semantic_threshold": text_config.get('semantic_threshold', 0.5),
                "semantic_model": text_config.get('semantic_model', 'paraphrase-multilingual-MiniLM-L12-v2')
            }

        return kb_config
