# -*- coding: utf-8 -*-
"""
错误处理和用户反馈工具
"""
import streamlit as st
from typing import Optional, Any, Dict
import traceback
import logging
from contextlib import contextmanager


class ErrorHandler:
    """统一错误处理器"""

    @staticmethod
    def handle_api_error(error: Exception, context: str = "") -> None:
        """处理API相关错误"""
        error_msg = f"API调用失败: {str(error)}"
        if context:
            error_msg = f"{context} - {error_msg}"

        st.error(f"❌ {error_msg}")

        # 记录详细错误日志
        logging.error(f"API Error in {context}: {str(error)}")
        logging.error(traceback.format_exc())

    @staticmethod
    def handle_ui_error(error: Exception, context: str = "") -> None:
        """处理UI相关错误"""
        error_msg = f"界面操作失败: {str(error)}"
        if context:
            error_msg = f"{context} - {error_msg}"

        st.error(f"⚠️ {error_msg}")

        # 对于UI错误，通常不需要显示完整堆栈跟踪
        logging.warning(f"UI Error in {context}: {str(error)}")

    @staticmethod
    def handle_validation_error(message: str) -> None:
        """处理验证错误"""
        st.warning(f"⚠️ {message}")

    @staticmethod
    def show_success(message: str) -> None:
        """显示成功消息"""
        st.success(f"✅ {message}")

    @staticmethod
    def show_info(message: str) -> None:
        """显示信息消息"""
        st.info(f"ℹ️ {message}")

    @staticmethod
    def show_warning(message: str) -> None:
        """显示警告消息"""
        st.warning(f"⚠️ {message}")

    @staticmethod
    def confirm_action(message: str, action_name: str = "确认") -> bool:
        """显示确认对话框"""
        return st.checkbox(f"**{action_name}**: {message}")


class FeedbackManager:
    """用户反馈管理器"""

    @staticmethod
    def show_loading_spinner(message: str = "处理中..."):
        """显示加载提示"""
        return st.spinner(f"⏳ {message}")

    @staticmethod
    def show_progress_bar(total: int, current: int, text: str = "进度"):
        """显示进度条"""
        progress = min(current / total, 1.0) if total > 0 else 0
        st.progress(progress, text=f"{text}: {current}/{total}")

    @staticmethod
    def show_result_summary(success_count: int, error_count: int, total_count: int):
        """显示结果摘要"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("总数", total_count)
        with col2:
            st.metric("成功", success_count, delta=success_count if success_count > 0 else None)
        with col3:
            st.metric("失败", error_count, delta=-error_count if error_count > 0 else None)
        with col4:
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            st.metric("成功率", f"{success_rate:.1f}%")


@contextmanager
def error_boundary(context: str = "", show_traceback: bool = False):
    """错误边界上下文管理器"""
    try:
        yield
    except Exception as e:
        ErrorHandler.handle_api_error(e, context)
        if show_traceback:
            with st.expander("详细错误信息"):
                st.code(traceback.format_exc())


def safe_api_call(func, *args, context: str = "", **kwargs):
    """安全的API调用包装器"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        ErrorHandler.handle_api_error(e, context)
        return None


class ValidationResult:
    """验证结果类"""

    def __init__(self, is_valid: bool, message: str = ""):
        self.is_valid = is_valid
        self.message = message

    def show_feedback(self):
        """显示验证反馈"""
        if not self.is_valid:
            ErrorHandler.handle_validation_error(self.message)
        return self.is_valid


def validate_required(value: Any, field_name: str) -> ValidationResult:
    """验证必填字段"""
    if not value or (isinstance(value, str) and not value.strip()):
        return ValidationResult(False, f"{field_name}不能为空")
    return ValidationResult(True)


def validate_file_type(filename: str, allowed_extensions: list) -> ValidationResult:
    """验证文件类型"""
    if not filename:
        return ValidationResult(False, "文件名不能为空")

    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext not in allowed_extensions:
        return ValidationResult(False, f"不支持的文件类型 .{ext}，允许的类型: {', '.join(allowed_extensions)}")
    return ValidationResult(True)


def validate_api_response(response: Dict, required_fields: list = None) -> ValidationResult:
    """验证API响应"""
    if not response:
        return ValidationResult(False, "API响应为空")

    if required_fields:
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            return ValidationResult(False, f"API响应缺少必要字段: {', '.join(missing_fields)}")

    return ValidationResult(True)
