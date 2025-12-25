# -*- coding: utf-8 -*-
"""
@File    : memory_manager.py
@Time    : 2025/12/16
@Desc    : 基于LangGraph checkpointer的记忆管理器
"""
import traceback
from typing import Dict, Any, List, Optional, Sequence
from datetime import datetime, timedelta
from dataclasses import dataclass

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models.chat_models import BaseChatModel

import logging

logger = logging.getLogger(__name__)


@dataclass
class CheckpointMemoryConfig:
    """基于checkpointer的记忆配置"""
    # 短期记忆配置
    max_message_history: int = 50  # 保留的最近消息数
    # summarization_threshold: int = 30  # 触发总结的消息数阈值
    summarization_threshold: int = 5  # 触发总结的消息数阈值

    # 长期记忆配置
    max_sessions: int = 100  # 最大保存的会话数
    session_retention_days: int = 30  # 会话保留天数

    # 检索配置
    retrieval_k: int = 5  # 检索的相关会话数
    semantic_search: bool = False  # 是否启用语义搜索（需要LLM）


class CheckpointMemoryManager:
    """
    基于LangGraph checkpointer的记忆管理器

    核心思想：
    - 使用LangGraph的checkpointer作为主要存储机制
    - checkpointer自动保存每次对话的状态变化
    - 通过thread_id区分不同的对话会话
    - 在对话开始时加载相关历史，在过程中自动保存

    优势：
    - 无需额外的记忆存储层
    - 自动的状态持久化
    - 与LangGraph原生集成
    - 支持并发和多会话
    """

    def __init__(
            self,
            checkpointer: Optional[BaseCheckpointSaver] = None,
            config: Optional[CheckpointMemoryConfig] = None,
            llm_client: Optional[BaseChatModel] = None
    ):
        """
        初始化基于checkpointer的记忆管理器

        Args:
            checkpointer: LangGraph检查点保存器
            config: 记忆配置
            llm_client: LLM客户端（用于语义搜索和总结）
        """
        self.config = config or CheckpointMemoryConfig()
        self.checkpointer = checkpointer or InMemorySaver()
        self.llm_client = llm_client

        logger.info(f"CheckpointMemoryManager initialized with checkpointer: {type(self.checkpointer).__name__}")

    async def load_conversation_history(
            self,
            thread_id: Optional[str] = None,
            max_messages: Optional[int] = None
    ) -> List[BaseMessage]:
        """
        加载对话历史

        从checkpointer中加载指定thread_id的最新对话状态

        Args:
            thread_id: 会话ID
            max_messages: 最大消息数量限制

        Returns:
            消息历史列表
        """
        if not thread_id:
            raise ValueError("thread_id is required for loading conversation history")

        try:
            config = RunnableConfig(configurable={"thread_id": thread_id})

            # 获取最新的检查点
            try:
                checkpoint_tuple = await self.checkpointer.aget(config)
                if not checkpoint_tuple:
                    return []

                # 处理不同的返回值格式
                if len(checkpoint_tuple) == 2:
                    checkpoint, metadata = checkpoint_tuple
                elif len(checkpoint_tuple) == 1:
                    checkpoint = checkpoint_tuple[0]
                    metadata = {}
                else:
                    logger.warning(f"Unexpected checkpoint tuple length: {len(checkpoint_tuple)}")
                    return []
            except Exception as e:
                logger.debug(f"No checkpoint found for thread_id {thread_id}: {str(e)}")
                return []

            # 从检查点中提取消息
            channel_values = checkpoint.get("channel_values", {})
            messages = channel_values.get("messages", [])

            # 限制消息数量
            max_messages = max_messages or self.config.max_message_history
            if len(messages) > max_messages:
                messages = messages[-max_messages:]

            logger.debug(f"Loaded {len(messages)} messages for thread_id: {thread_id}")
            return messages

        except Exception as e:
            logger.error(f"Failed to load conversation history for thread_id {thread_id}: {str(e)}")
            return []

    async def save_conversation_state(
            self,
            thread_id: str,
            messages: List[BaseMessage],
            metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        保存对话状态

        注意：在LangGraph中，这个操作通常由图执行时自动完成。
        这个方法主要用于手动保存或特殊情况。

        Args:
            thread_id: 会话ID
            messages: 消息列表
            metadata: 元数据

        Returns:
            保存是否成功
        """
        try:
            # 在LangGraph中，状态保存通常是自动的
            # 这里我们只是记录日志
            logger.debug(f"Conversation state save requested for thread_id: {thread_id}, messages: {len(messages)}")
            return True

        except Exception as e:
            logger.error(f"Failed to save conversation state for thread_id {thread_id}: {str(e)}")
            return False

    async def search_relevant_memories(
            self,
            thread_id: Optional[str],
            query: str,
            limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相关记忆

        从当前会话和其他相关会话中搜索与查询相关的记忆

        Args:
            thread_id: 当前会话ID
            query: 查询内容
            limit: 最大返回数量

        Returns:
            相关记忆列表
        """
        if not thread_id:
            raise ValueError("thread_id is required for searching relevant memories")

        try:
            limit = limit or self.config.retrieval_k
            relevant_memories = []

            # 首先搜索当前会话的历史
            current_messages = await self.load_conversation_history(thread_id)
            if current_messages:
                relevant_in_current = self._find_relevant_messages(
                    current_messages, query, limit=min(limit // 2, len(current_messages))
                )
                relevant_memories.extend(relevant_in_current)

            # 如果启用了语义搜索，搜索其他会话
            if self.config.semantic_search and self.llm_client:
                other_sessions = await self._search_other_sessions(query, thread_id, limit=len(relevant_memories))
                relevant_memories.extend(other_sessions)

            # 限制总数量
            relevant_memories = relevant_memories[:limit]

            logger.debug(f"Found {len(relevant_memories)} relevant memories for query: {query[:50]}...")
            return relevant_memories

        except Exception as e:
            logger.error(f"Failed to search relevant memories: {str(e)}")
            return []

    def _find_relevant_messages(
            self,
            messages: List[BaseMessage],
            query: str,
            limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        在消息列表中查找相关消息

        使用简单的关键词匹配，可以扩展为语义相似度

        Args:
            messages: 消息列表
            query: 查询字符串
            limit: 最大返回数量

        Returns:
            相关消息字典列表
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        relevant_messages = []

        for i, msg in enumerate(messages):
            if hasattr(msg, 'content') and msg.content:
                content_lower = msg.content.lower()

                # 计算关键词匹配度
                matched_words = sum(1 for word in query_words if word in content_lower)
                if matched_words > 0:
                    relevance_score = matched_words / len(query_words)

                    relevant_messages.append({
                        "message": msg,
                        "index": i,
                        "relevance_score": relevance_score,
                        "thread_id": None  # 当前会话
                    })

        # 按相关度排序并限制数量
        relevant_messages.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_messages[:limit]

    async def _search_other_sessions(
            self,
            query: str,
            current_thread_id: str,
            limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        在其他会话中搜索相关内容

        Args:
            query: 查询内容
            current_thread_id: 当前会话ID
            limit: 最大返回数量

        Returns:
            相关会话记忆列表
        """
        try:
            # 获取所有会话列表
            config = RunnableConfig(configurable={"thread_id": current_thread_id})
            all_sessions = await self.checkpointer.alist(config)

            relevant_sessions = []

            for checkpoint_id, metadata in all_sessions:
                try:
                    # 加载检查点
                    checkpoint_tuple = await self.checkpointer.aget(
                        RunnableConfig(configurable={"thread_id": current_thread_id}),
                        checkpoint_id
                    )

                    if checkpoint_tuple:
                        checkpoint, _ = checkpoint_tuple
                        channel_values = checkpoint.get("channel_values", {})
                        messages = channel_values.get("messages", [])

                        # 在这个会话中查找相关消息
                        relevant_in_session = self._find_relevant_messages(messages, query, limit=2)

                        if relevant_in_session:
                            # 取最相关的消息
                            best_match = max(relevant_in_session, key=lambda x: x["relevance_score"])
                            relevant_sessions.append({
                                "session_id": checkpoint_id,
                                "message": best_match["message"],
                                "relevance_score": best_match["relevance_score"]
                            })

                except Exception as e:
                    logger.debug(f"Error processing session {checkpoint_id}: {str(e)}")
                    continue

            # 排序并限制数量
            relevant_sessions.sort(key=lambda x: x["relevance_score"], reverse=True)
            return relevant_sessions[:limit]

        except Exception as e:
            logger.error(f"Failed to search other sessions: {str(e)}")
            return []

    def should_summarize(self, messages: Sequence[BaseMessage]) -> bool:
        """
        判断是否需要总结

        Args:
            messages: 消息列表

        Returns:
            是否需要总结
        """
        return len(messages) >= self.config.summarization_threshold

    async def summarize_conversation(
            self,
            messages: List[BaseMessage],
            thread_id: str
    ) -> Optional[SystemMessage]:
        """
        生成对话总结

        Args:
            messages: 要总结的消息列表
            thread_id: 会话ID

        Returns:
            总结消息（如果生成成功）
        """
        if not self.llm_client or not messages:
            return None

        try:
            # 准备总结提示
            conversation_text = "\n".join([
                f"{msg.type if hasattr(msg, 'type') else 'unknown'}: {msg.content if hasattr(msg, 'content') else str(msg)}"
                for msg in messages
            ])

            summary_prompt = f"""请总结以下对话的主要内容，保留关键信息和决策点。总结应该简洁但包含重要细节：

            {conversation_text}
            
            总结（控制在200字以内）：
            """

            # 调用LLM生成总结
            from langchain_core.messages import HumanMessage
            response = await self.llm_client.ainvoke([HumanMessage(content=summary_prompt)])

            summary_text = response.content if hasattr(response, "content") else str(response)

            summary_message = SystemMessage(
                content=f"历史对话总结：{summary_text}"
            )

            logger.info(f"Generated summary for thread_id {thread_id}, original messages: {len(messages)}")
            return summary_message

        except Exception as e:
            logger.error(f"Failed to generate summary for thread_id {thread_id}: {e} -> {traceback.format_exc()}")
            return

    async def cleanup_old_sessions(self, days: Optional[int] = None) -> int:
        """
        清理旧的会话

        Args:
            days: 保留天数，默认使用配置值

        Returns:
            清理的会话数量
        """
        try:
            days = days or self.config.session_retention_days
            cutoff_date = datetime.now() - timedelta(days=days)

            # 注意：SqliteSaver没有直接的清理API
            # 这里只是记录日志，实际清理需要外部管理
            logger.info(f"Session cleanup requested: retain {days} days (cutoff: {cutoff_date.isoformat()})")

            # TODO: 实现具体的清理逻辑
            # 这可能需要直接操作SQLite数据库

            return 0

        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {str(e)}")
            return 0

    def get_memory_stats(self, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取记忆统计信息

        Args:
            thread_id: 会话ID

        Returns:
            统计信息字典
        """
        try:
            # 这里返回配置信息，实际的运行时统计需要异步获取
            return {
                "thread_id": thread_id,
                "config": {
                    "max_message_history": self.config.max_message_history,
                    "summarization_threshold": self.config.summarization_threshold,
                    "max_sessions": self.config.max_sessions,
                    "session_retention_days": self.config.session_retention_days,
                    "retrieval_k": self.config.retrieval_k,
                    "semantic_search": self.config.semantic_search
                },
                "checkpointer_type": type(self.checkpointer).__name__,
                "has_llm": self.llm_client is not None
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {str(e)}")
            return {"error": str(e)}
