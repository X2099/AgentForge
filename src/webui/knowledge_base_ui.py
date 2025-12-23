# -*- coding: utf-8 -*-
"""
@File    : knowledge_base_ui.py
@Time    : 2025/12/9 15:29
@Desc    : 知识库管理界面主模块
"""
import streamlit as st

from .components.kb_overview import KnowledgeBaseOverview
from .components.kb_creator import KnowledgeBaseCreator
from .components.kb_uploader import KnowledgeBaseUploader
from .components.kb_search import KnowledgeBaseSearch
from .components.kb_config import KnowledgeBaseConfig


class KnowledgeBaseUI:
    """知识库管理界面"""

    def __init__(self):
        self.overview = KnowledgeBaseOverview()
        self.creator = KnowledgeBaseCreator()
        self.uploader = KnowledgeBaseUploader()
        self.search = KnowledgeBaseSearch()
        self.config = KnowledgeBaseConfig()

    def render_main_page(self):
        """渲染主页面"""
        st.title("📚 知识库管理系统")

        # 标签页
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏠 总览",
            "➕ 创建知识库",
            "📤 上传文件",
            "🔍 搜索测试",
            "⚙️ 向量配置"
        ])

        with tab1:
            self.overview.render()

        with tab2:
            self.creator.render()

        with tab3:
            self.uploader.render()

        with tab4:
            self.search.render()

        with tab5:
            self.config.render()


def main():
    """主函数"""
    # 页面配置
    st.set_page_config(
        page_title="知识库管理系统",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 创建UI实例
    ui = KnowledgeBaseUI()

    # 渲染页面
    ui.render_main_page()


if __name__ == "__main__":
    main()
