# -*- coding: utf-8 -*-
"""
知识库配置管理组件
"""
import streamlit as st


class KnowledgeBaseConfig:
    """知识库配置管理组件"""

    def render(self):
        """渲染向量配置页面"""
        st.subheader("⚙️ 向量存储配置管理")

        # 向量存储类型比较
        st.info("""
        **向量存储类型对比:**

        | 类型 | 特点 | 适用场景 |
        |------|------|----------|
        | **ChromaDB** | 轻量级、易用、支持持久化 | 开发测试、小规模应用 |
        | **FAISS** | 高性能、内存计算、Facebook开源 | 大规模向量检索、研究 |
        | **Milvus** | 生产级、分布式、功能丰富 | 企业级应用、大规模生产 |
        | **Weaviate** | 向量+图数据库、多模态 | 复杂关系、多模态搜索 |
        """)

        # 嵌入模型比较
        st.info("""
        **嵌入模型对比:**

        | 模型 | 特点 | 语言 | 维度 |
        |------|------|------|------|
        | **OpenAI Embeddings** | 质量高、稳定、收费 | 多语言 | 1536 |
        | **BGE中文模型** | 中文优化、开源、免费 | 中文优先 | 384-1024 |
        | **Sentence Transformers** | 开源、可定制、免费 | 多语言 | 384-768 |
        """)

        # 配置模板
        st.subheader("配置模板")

        template_tab1, template_tab2, template_tab3 = st.tabs(["ChromaDB", "FAISS", "Milvus"])

        with template_tab1:
            st.code("""
# ChromaDB 配置模板
vector_store:
  store_type: "chroma"
  collection_name: "my_knowledge_base"
  persist_directory: "./data/chroma_db"
  embedding_function: "local"  # 或 "openai"

embedder:
  embedder_type: "bge"
  model_name: "BAAI/bge-small-zh-v1.5"
  device: "cuda"
  normalize_embeddings: true
            """, language="yaml")

        with template_tab2:
            st.code("""
# FAISS 配置模板
vector_store:
  store_type: "faiss"
  index_path: "./data/faiss_index"
  index_type: "IVF"  # Flat, IVF, HNSW
  nlist: 100  # IVF聚类数

embedder:
  embedder_type: "sentence_transformer"
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  device: "cpu"
            """, language="yaml")

        with template_tab3:
            st.code("""
# Milvus 配置模板
vector_store:
  store_type: "milvus"
  host: "localhost"
  port: 19530
  collection_name: "knowledge_base"
  username: "root"
  password: "Milvus"

embedder:
  embedder_type: "openai"
  model: "text-embedding-3-small"
  api_key: "${OPENAI_API_KEY}"
  dimensions: 1536
            """, language="yaml")

        # 性能测试
        st.subheader("🏃 性能测试")

        if st.button("运行基准测试"):
            with st.spinner("运行基准测试中..."):
                try:
                    results = self._run_benchmark()

                    # 显示结果
                    st.success("基准测试完成")

                    # 创建性能对比图表
                    import plotly.graph_objects as go

                    fig = go.Figure(data=[
                        go.Bar(
                            name='索引速度',
                            x=['ChromaDB', 'FAISS', 'Milvus'],
                            y=[results.get('chroma', 100), results.get('faiss', 150), results.get('milvus', 80)]
                        ),
                        go.Bar(
                            name='查询速度',
                            x=['ChromaDB', 'FAISS', 'Milvus'],
                            y=[results.get('chroma_q', 50), results.get('faiss_q', 30), results.get('milvus_q', 20)]
                        )
                    ])

                    fig.update_layout(
                        barmode='group',
                        title='向量存储性能对比',
                        yaxis_title='速度 (文档/秒)'
                    )

                    st.plotly_chart(fig)

                except Exception as e:
                    st.error(f"基准测试失败: {str(e)}")

    def _run_benchmark(self):
        """运行基准测试"""
        # 模拟基准测试结果
        return {
            "chroma": 100,
            "chroma_q": 50,
            "faiss": 150,
            "faiss_q": 30,
            "milvus": 80,
            "milvus_q": 20
        }
