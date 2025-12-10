# -*- coding: utf-8 -*-
"""
知识库侧边栏组件
"""
import streamlit as st
from pathlib import Path


class KnowledgeBaseSidebar:
    """知识库侧边栏组件"""

    def render(self):
        """渲染侧边栏"""
        with st.sidebar:
            st.header("📚 知识库设置")

            # 向量存储类型选择
            vector_store_types = ["ChromaDB", "FAISS", "Milvus", "Weaviate"]
            selected_store = st.selectbox(
                "向量存储类型",
                vector_store_types,
                help="选择向量数据库类型"
            )

            # 嵌入模型选择
            embedder_types = [
                "OpenAI Embeddings",
                "BGE (本地中文)",
                "Sentence Transformers",
                "自定义模型"
            ]
            selected_embedder = st.selectbox(
                "嵌入模型",
                embedder_types,
                help="选择文本嵌入模型"
            )

            # 分块参数
            st.subheader("文本分块参数")
            col1, col2 = st.columns(2)
            with col1:
                chunk_size = st.number_input(
                    "分块大小",
                    min_value=100,
                    max_value=2000,
                    value=500,
                    help="每个文本块的最大字符数"
                )
            with col2:
                chunk_overlap = st.number_input(
                    "重叠大小",
                    min_value=0,
                    max_value=500,
                    value=50,
                    help="相邻文本块之间的重叠字符数"
                )

            # 分割器类型
            splitter_types = ["递归分割", "语义分割", "固定长度分割"]
            splitter_type = st.selectbox(
                "分割器类型",
                splitter_types
            )

            # 额外配置（根据选择显示）
            if selected_embedder == "OpenAI Embeddings":
                st.text_input("OpenAI API Key", type="password", key="openai_key")
                st.selectbox(
                    "模型版本",
                    ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-3-ada-002"]
                )

            elif selected_embedder == "BGE (本地中文)":
                st.selectbox(
                    "BGE模型",
                    [
                        "BAAI/bge-small-zh-v1.5",
                        "BAAI/bge-base-zh-v1.5",
                        "BAAI/bge-large-zh-v1.5"
                    ]
                )
                st.checkbox("使用GPU加速", value=True)

            # 向量存储配置
            if selected_store == "ChromaDB":
                st.text_input(
                    "持久化目录",
                    value="./data/chroma_db",
                    help="ChromaDB数据存储目录"
                )

            elif selected_store == "FAISS":
                st.selectbox(
                    "索引类型",
                    ["Flat", "IVF", "HNSW"],
                    help="FAISS索引算法"
                )

            elif selected_store == "Milvus":
                st.text_input("Milvus地址", value="localhost:19530")
                st.text_input("集合名称", value="knowledge_base")

            # 保存配置按钮
            if st.button("💾 保存配置模板"):
                self._save_config_template(
                    vector_store=selected_store,
                    embedder=selected_embedder,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )

    def _save_config_template(self, **config):
        """保存配置模板"""
        config_file = "./configs/knowledge_bases/template.yaml"
        Path(config_file).parent.mkdir(parents=True, exist_ok=True)

        # 将配置转换为YAML格式
        import yaml
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        st.success(f"配置模板已保存到: {config_file}")
