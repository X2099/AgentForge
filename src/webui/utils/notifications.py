# -*- coding: utf-8 -*-
"""
通知系统
"""
import streamlit as st
from typing import Optional
import time


class NotificationManager:
    """通知管理器"""

    @staticmethod
    def success(message: str, duration: int = 3):
        """成功通知"""
        st.success(f"✅ {message}")
        time.sleep(duration)

    @staticmethod
    def error(message: str, duration: Optional[int] = None):
        """错误通知"""
        st.error(f"❌ {message}")
        if duration:
            time.sleep(duration)

    @staticmethod
    def warning(message: str, duration: int = 4):
        """警告通知"""
        st.warning(f"⚠️ {message}")
        time.sleep(duration)

    @staticmethod
    def info(message: str, duration: int = 3):
        """信息通知"""
        st.info(f"ℹ️ {message}")
        time.sleep(duration)

    @staticmethod
    def show_toast(message: str, type: str = "info"):
        """显示Toast通知"""
        if type == "success":
            NotificationManager.success(message)
        elif type == "error":
            NotificationManager.error(message)
        elif type == "warning":
            NotificationManager.warning(message)
        else:
            NotificationManager.info(message)


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, total_steps: int, description: str = "处理中"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.progress_bar = st.progress(0, text=f"{description}: 0/{total_steps}")

    def update(self, step_name: str = None, increment: int = 1):
        """更新进度"""
        self.current_step += increment
        progress = min(self.current_step / self.total_steps, 1.0)

        display_text = f"{self.description}: {self.current_step}/{self.total_steps}"
        if step_name:
            display_text += f" - {step_name}"

        self.progress_bar.progress(progress, text=display_text)

    def complete(self, message: str = "完成"):
        """完成进度"""
        self.progress_bar.progress(1.0, text=f"✅ {message}")
        self.progress_bar.empty()


class StatusIndicator:
    """状态指示器"""

    @staticmethod
    def api_status(healthy: bool) -> str:
        """API状态指示器"""
        return "🟢 正常" if healthy else "🔴 离线"

    @staticmethod
    def operation_status(success: bool) -> str:
        """操作状态指示器"""
        return "✅ 成功" if success else "❌ 失败"

    @staticmethod
    def loading_status() -> str:
        """加载状态指示器"""
        return "⏳ 处理中..."

    @staticmethod
    def file_status(uploaded: bool, processed: bool) -> str:
        """文件状态指示器"""
        if processed:
            return "✅ 已处理"
        elif uploaded:
            return "⏳ 处理中"
        else:
            return "❌ 未上传"
