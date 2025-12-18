# -*- coding: utf-8 -*-
"""
通用UI组件
"""
import streamlit as st
from typing import List, Dict, Any, Optional, Callable
import pandas as pd


class Card:
    """卡片组件"""

    @staticmethod
    def create(title: str, content: Any = None, icon: str = "", collapsed: bool = False):
        """创建卡片"""
        with st.container():
            if icon:
                st.subheader(f"{icon} {title}")
            else:
                st.subheader(title)

            if content:
                if collapsed:
                    with st.expander("查看详情"):
                        content()
                else:
                    content()


class MetricGrid:
    """指标网格组件"""

    @staticmethod
    def create(metrics: List[Dict[str, Any]], columns: int = 3):
        """创建指标网格"""
        cols = st.columns(columns)
        for i, metric in enumerate(metrics):
            with cols[i % columns]:
                delta = metric.get('delta')
                if delta is not None:
                    st.metric(
                        metric['label'],
                        metric['value'],
                        delta=delta,
                        help=metric.get('help')
                    )
                else:
                    st.metric(
                        metric['label'],
                        metric['value'],
                        help=metric.get('help')
                    )


class DataTable:
    """数据表格组件"""

    @staticmethod
    def create(
            data: List[Dict],
            columns: Optional[List[str]] = None,
            title: str = "",
            searchable: bool = False,
            selectable: bool = False
    ):
        """创建数据表格"""
        if not data:
            st.info("暂无数据")
            return None

        if title:
            st.subheader(title)

        df = pd.DataFrame(data)

        if columns:
            df = df[columns]

        # 添加搜索功能
        if searchable and len(data) > 5:
            search_term = st.text_input("搜索", key=f"search_{title}")
            if search_term:
                mask = df.astype(str).apply(
                    lambda x: x.str.contains(search_term, case=False, na=False)
                ).any(axis=1)
                df = df[mask]

        # 显示表格
        if selectable:
            return st.dataframe(
                df,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun"
            )
        else:
            return st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )


class TabView:
    """标签页视图组件"""

    @staticmethod
    def create(tabs: Dict[str, Callable], default_tab: str = None):
        """创建标签页视图"""
        tab_names = list(tabs.keys())
        if default_tab and default_tab in tab_names:
            default_index = tab_names.index(default_tab)
        else:
            default_index = 0

        selected_tab = st.radio(
            "选择标签页",
            tab_names,
            index=default_index,
            horizontal=True,
            label_visibility="collapsed"
        )

        # 执行选中的标签页内容
        if selected_tab in tabs:
            tabs[selected_tab]()


class ActionButton:
    """操作按钮组件"""

    @staticmethod
    def create(
            label: str,
            on_click: Callable,
            type: str = "secondary",
            icon: str = "",
            help_text: str = "",
            disabled: bool = False,
            key: str = None
    ):
        """创建操作按钮"""
        button_label = f"{icon} {label}" if icon else label

        if st.button(
                button_label,
                type=type,
                disabled=disabled,
                help=help_text,
                key=key
        ):
            try:
                result = on_click()
                return result
            except Exception as e:
                st.error(f"操作失败: {str(e)}")
                return False

        return None


class StatusBadge:
    """状态徽章组件"""

    @staticmethod
    def create(status: str, status_type: str = "info") -> str:
        """创建状态徽章"""
        status_map = {
            "success": "🟢",
            "error": "🔴",
            "warning": "🟡",
            "info": "🔵",
            "loading": "⏳",
            "disabled": "⚪"
        }

        icon = status_map.get(status_type, "⚪")
        return f"{icon} {status}"


class FormBuilder:
    """表单构建器组件"""

    def __init__(self, title: str = "", submit_label: str = "提交"):
        self.title = title
        self.submit_label = submit_label
        self.fields = {}

    def add_text_input(self, key: str, label: str, value: str = "", **kwargs):
        """添加文本输入框"""
        self.fields[key] = {
            'type': 'text_input',
            'label': label,
            'value': value,
            'kwargs': kwargs
        }

    def add_number_input(self, key: str, label: str, value: int = 0, **kwargs):
        """添加数字输入框"""
        self.fields[key] = {
            'type': 'number_input',
            'label': label,
            'value': value,
            'kwargs': kwargs
        }

    def add_selectbox(self, key: str, label: str, options: List, **kwargs):
        """添加选择框"""
        self.fields[key] = {
            'type': 'selectbox',
            'label': label,
            'options': options,
            'kwargs': kwargs
        }

    def add_checkbox(self, key: str, label: str, value: bool = False, **kwargs):
        """添加复选框"""
        self.fields[key] = {
            'type': 'checkbox',
            'label': label,
            'value': value,
            'kwargs': kwargs
        }

    def render(self) -> Dict[str, Any]:
        """渲染表单并返回表单数据"""
        if self.title:
            st.subheader(self.title)

        form_data = {}

        for key, field_config in self.fields.items():
            field_type = field_config['type']

            if field_type == 'text_input':
                form_data[key] = st.text_input(
                    field_config['label'],
                    value=field_config['value'],
                    key=f"form_{key}",
                    **field_config.get('kwargs', {})
                )

            elif field_type == 'number_input':
                form_data[key] = st.number_input(
                    field_config['label'],
                    value=field_config['value'],
                    key=f"form_{key}",
                    **field_config.get('kwargs', {})
                )

            elif field_type == 'selectbox':
                form_data[key] = st.selectbox(
                    field_config['label'],
                    field_config['options'],
                    key=f"form_{key}",
                    **field_config.get('kwargs', {})
                )

            elif field_type == 'checkbox':
                form_data[key] = st.checkbox(
                    field_config['label'],
                    value=field_config['value'],
                    key=f"form_{key}",
                    **field_config.get('kwargs', {})
                )

        return form_data


class LoadingIndicator:
    """加载指示器组件"""

    @staticmethod
    def show(message: str = "加载中..."):
        """显示加载指示器"""
        return st.spinner(f"⏳ {message}")

    @staticmethod
    def show_progress(current: int, total: int, message: str = "处理中"):
        """显示进度条"""
        progress = min(current / total, 1.0) if total > 0 else 0
        st.progress(progress, text=f"{message}: {current}/{total}")


class EmptyState:
    """空状态组件"""

    @staticmethod
    def show(
            icon: str = "📭",
            title: str = "暂无数据",
            description: str = "",
            action_label: str = "",
            action_callback: Callable = None
    ):
        """显示空状态"""
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown(f"<h1 style='text-align: center;'>{icon}</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)

            if description:
                st.caption(description)

            if action_label and action_callback:
                st.button(action_label, on_click=action_callback, type="primary")


class ConfirmationDialog:
    """确认对话框组件"""

    @staticmethod
    def show(
            title: str,
            message: str,
            confirm_label: str = "确认",
            cancel_label: str = "取消",
            danger: bool = False
    ) -> bool:
        """显示确认对话框"""
        st.warning(f"⚠️ {title}")
        st.write(message)

        col1, col2 = st.columns(2)

        with col1:
            if st.button(cancel_label, type="secondary"):
                return False

        with col2:
            button_type = "primary"
            if danger:
                button_type = "secondary"  # Streamlit没有danger类型，使用secondary

            if st.button(confirm_label, type=button_type):
                return True

        return False
