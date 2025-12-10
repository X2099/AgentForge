# -*- coding: utf-8 -*-
"""
知识库创建组件
"""
import streamlit as st
from pathlib import Path
import yaml


class KnowledgeBaseCreator:
    """知识库创建组件"""

    def __init__(self, kb_manager):
        self.kb_manager = kb_manager

    def render(self):
        """渲染创建知识库页面"""
        st.subheader("🚀 创建新知识库")

        # 知识库基本信息
        col1, col2 = st.columns(2)
        with col1:
            kb_name = st.text_input("知识库名称", value="my_knowledge_base")
        with col2:
            kb_description = st.text_input("描述", value="我的知识库")

        # 向量存储配置
        self._render_vector_config()

        # 嵌入模型配置
        self._render_embedder_config()

        # 文本处理配置
        self._render_text_config()

        # 文件上传区域
        self._render_file_upload(kb_name)

        # 创建按钮
        self._render_create_button(kb_name, kb_description)

    def _render_vector_config(self):
        """渲染向量存储配置"""
        st.subheader("💾 向量存储配置")

        vector_config_col1, vector_config_col2 = st.columns(2)

        with vector_config_col1:
            # 向量存储类型
            vector_store_type = st.selectbox(
                "向量数据库",
                ["chroma", "faiss", "milvus"],
                format_func=lambda x: {
                    "chroma": "ChromaDB (推荐)",
                    "faiss": "FAISS (本地)",
                    "milvus": "Milvus (生产)"
                }[x]
            )

            # 嵌入模型配置
            embedder_type = st.selectbox(
                "嵌入模型",
                ["openai", "local", "bge"],
                format_func=lambda x: {
                    "openai": "OpenAI Embeddings",
                    "local": "本地 Sentence Transformers",
                    "bge": "BGE中文模型"
                }[x]
            )

        with vector_config_col2:
            # 向量存储特定配置
            if vector_store_type == "chroma":
                persist_dir = st.text_input(
                    "持久化目录",
                    value=f"./data/vector_stores/{st.session_state.get('kb_name', 'kb')}"
                )
                collection_name = st.text_input("集合名称", value=st.session_state.get('kb_name', 'kb'))

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
            'embedder_type': embedder_type,
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
            embedder_type = st.session_state.vector_config.get('embedder_type', 'bge')

            if embedder_type == "openai":
                openai_key = st.text_input("OpenAI API Key", type="password")
                model_name = st.selectbox(
                    "模型",
                    ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]
                )
                dimensions = st.number_input(
                    "维度",
                    min_value=256,
                    max_value=3072,
                    value=1536,
                    help="嵌入向量维度"
                )

            elif embedder_type == "local":
                model_name = st.selectbox(
                    "模型名称",
                    [
                        "sentence-transformers/all-MiniLM-L6-v2",
                        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                        "自定义模型路径"
                    ]
                )
                if model_name == "自定义模型路径":
                    model_name = st.text_input("模型路径")

            elif embedder_type == "bge":
                model_name = st.selectbox(
                    "BGE模型",
                    [
                        "BAAI/bge-small-zh-v1.5",
                        "BAAI/bge-base-zh-v1.5",
                        "BAAI/bge-large-zh-v1.5"
                    ]
                )
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
                ["auto", "cpu", "cuda"],
                help="模型运行设备，auto为自动选择"
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

    def _render_file_upload(self, kb_name):
        """渲染文件上传区域"""
        st.subheader("📁 上传文档")

        upload_method = st.radio(
            "上传方式",
            ["本地文件上传", "文件夹批量导入", "网络链接导入"]
        )

        file_paths = []

        if upload_method == "本地文件上传":
            uploaded_files = st.file_uploader(
                "选择文档文件",
                type=["pdf", "txt", "md", "docx", "html", "csv"],
                accept_multiple_files=True,
                help="支持PDF、TXT、Markdown、Word、HTML、CSV格式"
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
                help="包含文档文件的文件夹路径"
            )

            if st.button("扫描文件夹"):
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
                help="输入文档的URL链接，每行一个"
            )

            if urls:
                url_list = [url.strip() for url in urls.split('\n') if url.strip()]
                file_paths.extend(url_list)
                st.info(f"添加了 {len(url_list)} 个网络链接")

        # 存储文件路径到session state
        st.session_state.file_paths = file_paths

    def _render_create_button(self, kb_name, kb_description):
        """渲染创建按钮"""
        st.divider()

        file_paths = st.session_state.get('file_paths', [])

        if st.button("🚀 创建知识库", type="primary", disabled=not file_paths):
            with st.spinner("正在创建知识库..."):
                try:
                    # 构建配置
                    kb_config = self._build_kb_config(kb_name, kb_description)

                    # 创建知识库
                    kb = self.kb_manager.create_knowledge_base(kb_config)

                    # 添加文档
                    stats = self.kb_manager.bulk_add_documents(
                        kb_name=kb_name,
                        file_paths=file_paths,
                        show_progress=True
                    )

                    # 显示结果
                    st.success("🎉 知识库创建成功！")

                    # 显示统计信息
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("处理文件", stats["processed_files"])
                    with col2:
                        st.metric("失败文件", stats["failed_files"])
                    with col3:
                        st.metric("总文本块", stats["total_chunks"])
                    with col4:
                        st.metric("有效块", stats["valid_chunks"])

                    # 显示详细结果
                    with st.expander("📊 详细处理结果"):
                        st.json(stats)

                    # 保存配置
                    self._save_kb_config(kb_config)

                except Exception as e:
                    st.error(f"创建失败: {str(e)}")
                    st.exception(e)

    def _build_kb_config(self, kb_name, kb_description):
        """构建知识库配置"""
        vector_config = st.session_state.get('vector_config', {})
        embedder_config = st.session_state.get('embedder_config', {})
        text_config = st.session_state.get('text_config', {})

        kb_config = {
            "name": kb_name,
            "description": kb_description,
            "splitter_type": text_config.get('splitter_type', 'recursive'),
            "chunk_size": text_config.get('chunk_size', 500),
            "chunk_overlap": text_config.get('chunk_overlap', 50),
            "embedder": {
                "embedder_type": embedder_config.get('embedder_type', 'bge'),
                "model": embedder_config.get('model_name', 'BAAI/bge-small-zh-v1.5'),
                "dimensions": embedder_config.get('dimensions'),
                "normalize_embeddings": embedder_config.get('normalize_embeddings'),
                "device": embedder_config.get('device', 'auto')
            },
            "vector_store": {
                "store_type": vector_config.get('store_type', 'chroma'),
                "collection_name": vector_config.get('collection_name', kb_name),
                "persist_directory": vector_config.get('persist_dir', f"./data/vector_stores/{kb_name}"),
                "host": vector_config.get('host'),
                "port": vector_config.get('port')
            }
        }

        # 添加语义分割特定配置
        if text_config.get('splitter_type') == "semantic":
            kb_config["semantic_threshold"] = text_config.get('semantic_threshold', 0.5)
            kb_config["semantic_model"] = text_config.get('semantic_model', 'paraphrase-multilingual-MiniLM-L12-v2')

        return kb_config

    def _save_kb_config(self, kb_config):
        """保存知识库配置"""
        config_dir = Path("./configs/knowledge_bases")
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / f"{kb_config['name']}.yaml"

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(kb_config, f, default_flow_style=False, allow_unicode=True)

        st.info(f"配置文件已保存: {config_file}")
