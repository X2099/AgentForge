# -*- coding: utf-8 -*-
"""
@File    : langgraph_nodes.py
@Time    : 2025/12/9 12:25
@Desc    : 
"""
from typing import Dict, Any, Callable, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.base import BaseCheckpointSaver
import operator

from .langgraph_memory import LangGraphMemoryStore
from .short_term.context_memory import ContextMemoryManager
from ..core.state.base_state import AgentState
from ..llm.llm_client import LLMClient


class MemoryState:
    """记忆状态扩展"""
    # 扩展基础AgentState
    retrieved_memories: list = []
    memory_context: str = ""
    should_remember: bool = True
    last_memory_update: Optional[str] = None


def create_memory_aware_state() -> StateGraph:
    """创建带记忆状态的State Graph"""

    # 定义状态类型
    class MemoryAwareState(AgentState):
        retrieved_memories: list = []
        memory_context: str = ""
        should_remember: bool = True
        last_memory_update: Optional[str] = None

    # 创建图
    workflow = StateGraph(MemoryAwareState)

    return workflow


class MemoryRetrievalNode:
    """记忆检索节点"""

    def __init__(self,
                 memory_store: LangGraphMemoryStore,
                 name: str = "memory_retrieval"):
        self.memory_store = memory_store
        self.name = name

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """检索相关记忆"""
        try:
            thread_id = state.get("session_id", "default")
            current_query = state.get("messages", [{}])[-1].get("content", "")

            # 从记忆存储中检索
            memories = self.memory_store.search_memories(
                thread_id=thread_id,
                query=current_query,
                limit=5
            )

            # 格式化记忆上下文
            memory_context = self._format_memories(memories)

            return {
                "retrieved_memories": memories,
                "memory_context": memory_context,
                "current_step": self.name
            }

        except Exception as e:
            return {
                "retrieved_memories": [],
                "memory_context": f"记忆检索错误: {str(e)}",
                "current_step": self.name
            }

    def _format_memories(self, memories: List[Dict[str, Any]]) -> str:
        """格式化记忆为上下文"""
        if not memories:
            return ""

        formatted = ["相关记忆："]
        for i, memory in enumerate(memories, 1):
            metadata = memory.get("metadata", {})
            summary = metadata.get("summary", "")
            memory_type = metadata.get("type", "unknown")

            if summary:
                formatted.append(f"{i}. [{memory_type}] {summary}")

        return "\n".join(formatted)


class MemoryUpdateNode:
    """记忆更新节点"""

    def __init__(self,
                 memory_store: LangGraphMemoryStore,
                 name: str = "memory_update"):
        self.memory_store = memory_store
        self.name = name

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """更新记忆"""
        try:
            if not state.get("should_remember", True):
                return {"current_step": self.name}

            thread_id = state.get("session_id", "default")
            messages = state.get("messages", [])

            if len(messages) < 2:
                return {"current_step": self.name}

            # 提取最近的交互
            recent_interaction = messages[-2:]  # 最后一条用户消息和AI回复

            # 生成记忆摘要
            memory_summary = await self._generate_memory_summary(recent_interaction)

            # 准备记忆元数据
            metadata = {
                "type": "conversation",
                "importance": self._calculate_importance(state),
                "summary": memory_summary,
                "tags": self._extract_tags(state)
            }

            # 保存记忆
            memory_id = await self.memory_store.save_memory(
                thread_id=thread_id,
                state={"interaction": recent_interaction},
                metadata=metadata
            )

            return {
                "last_memory_update": datetime.now().isoformat(),
                "memory_id": memory_id,
                "current_step": self.name
            }

        except Exception as e:
            return {
                "error": f"记忆更新失败: {str(e)}",
                "current_step": self.name
            }

    async def _generate_memory_summary(self, interaction: List[Dict[str, Any]]) -> str:
        """生成记忆摘要"""
        # 简化实现：提取关键信息
        user_msg = next((msg for msg in interaction if msg.get("role") == "user"), {})
        ai_msg = next((msg for msg in interaction if msg.get("role") == "assistant"), {})

        user_content = user_msg.get("content", "")[:100]
        ai_content = ai_msg.get("content", "")[:100]

        return f"用户: {user_content}... | 助手: {ai_content}..."

    def _calculate_importance(self, state: AgentState) -> int:
        """计算记忆重要性"""
        importance = 1

        # 包含工具调用的对话更重要
        if state.get("tool_calls"):
            importance += 2

        # 包含错误处理的对话更重要
        if state.get("error"):
            importance += 1

        # 长对话可能更重要
        messages_count = len(state.get("messages", []))
        if messages_count > 10:
            importance += 1

        return min(importance, 5)  # 限制在1-5范围内

    def _extract_tags(self, state: AgentState) -> List[str]:
        """提取记忆标签"""
        tags = []

        # 根据工具调用添加标签
        if state.get("tool_calls"):
            tags.append("tool_usage")

        # 根据错误添加标签
        if state.get("error"):
            tags.append("error_handling")

        # 根据主题添加标签（简化实现）
        last_message = state.get("messages", [{}])[-1].get("content", "").lower()

        if any(word in last_message for word in ["代码", "编程", "python"]):
            tags.append("programming")

        if any(word in last_message for word in ["数据", "分析", "统计"]):
            tags.append("data_analysis")

        if any(word in last_message for word in ["文件", "文档", "读取"]):
            tags.append("file_operation")

        return tags


class ContextManagementNode:
    """上下文管理节点"""

    def __init__(self,
                 context_manager: ContextMemoryManager,
                 name: str = "context_management"):
        self.context_manager = context_manager
        self.name = name

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """管理对话上下文"""
        try:
            messages = state.get("messages", [])

            # 将消息添加到上下文管理器
            for msg in messages[-2:]:  # 只处理最新消息
                role = msg.get("role", "user")
                content = msg.get("content", "")
                self.context_manager.add_message(role, content)

            # 获取优化后的上下文
            optimized_context = self.context_manager.get_context()

            return {
                "optimized_messages": optimized_context,
                "context_token_count": self._count_context_tokens(optimized_context),
                "current_step": self.name
            }

        except Exception as e:
            return {
                "error": f"上下文管理失败: {str(e)}",
                "current_step": self.name
            }

    def _count_context_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """计算上下文token数量"""
        total = 0
        for msg in messages:
            total += len(msg.get("content", "")) // 4  # 简单估算
        return total