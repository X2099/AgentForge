# -*- coding: utf-8 -*-
"""
@File    : checkpoint_memory_nodes.py
@Time    : 2025/12/16
@Desc    : 基于LangGraph checkpointer的记忆节点
"""
from typing import Dict, Any, List, Optional, Sequence, Annotated, Tuple
from datetime import datetime

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from ..core.state.base_state import AgentState
from .checkpoint_memory_manager import CheckpointMemoryManager

import logging

logger = logging.getLogger(__name__)


def create_checkpoint_memory_loader_node(
    memory_manager: CheckpointMemoryManager
):
    """
    创建基于checkpointer的记忆加载节点

    这个节点在对话开始时加载之前的对话历史

    Args:
        memory_manager: 记忆管理器

    Returns:
        节点函数
    """
    async def checkpoint_memory_loader_node(state: AgentState) -> Dict[str, Any]:
        """
        记忆加载节点

        从checkpointer中加载对话历史并合并到当前状态
        注意：这个节点直接使用checkpointer，不需要从state中获取thread_id
        """
        try:
            # 获取最新的检查点（自动使用当前工作流的thread_id）
            # 注意：checkpointer.aget(None) 会获取当前配置的最新检查点
            try:
                checkpoint_tuple = await memory_manager.checkpointer.aget(None)
                if not checkpoint_tuple:
                    return {"memory_context": ""}

                checkpoint, metadata = checkpoint_tuple
                historical_messages = checkpoint.get("messages", [])
            except Exception:
                # 如果获取失败，返回空结果
                return {"memory_context": ""}

            # 只保留最近的消息
            max_messages = memory_manager.config.max_message_history
            if len(historical_messages) > max_messages:
                historical_messages = historical_messages[-max_messages:]

            # 获取当前消息
            current_messages = state.get("messages", [])

            # 合并消息（历史消息 + 当前消息）
            # 注意：避免重复添加相同的消息
            if historical_messages and current_messages:
                # 检查最后一个历史消息和第一个当前消息是否重复
                if (len(historical_messages) > 0 and len(current_messages) > 0 and
                    str(historical_messages[-1]) == str(current_messages[0])):
                    # 如果重复，只保留历史消息
                    all_messages = historical_messages
                else:
                    all_messages = historical_messages + current_messages
            elif historical_messages:
                all_messages = historical_messages
            else:
                all_messages = current_messages

            logger.debug(f"Loaded {len(historical_messages)} historical messages, total: {len(all_messages)}")

            return {
                "messages": all_messages,
                "memory_loaded": True,
                "historical_message_count": len(historical_messages)
            }

        except Exception as e:
            logger.error(f"记忆加载失败: {str(e)}")
            return {
                "memory_loaded": False,
                "error": str(e)
            }

    return checkpoint_memory_loader_node


def create_checkpoint_memory_retrieval_node(
    memory_manager: CheckpointMemoryManager
):
    """
    创建基于checkpointer的记忆检索节点

    从对话历史中检索与当前查询相关的记忆

    Args:
        memory_manager: 记忆管理器

    Returns:
        节点函数
    """
    async def checkpoint_memory_retrieval_node(state: AgentState) -> Dict[str, Any]:
        """
        记忆检索节点

        检索与当前查询相关的历史记忆
        """
        try:
            messages = state.get("messages", [])

            if not messages:
                return {"memory_context": ""}

            # 获取当前查询（最后一条用户消息）
            last_user_msg = None
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
                    last_user_msg = msg
                    break

            if not last_user_msg:
                return {"memory_context": ""}

            query = last_user_msg.content if hasattr(last_user_msg, "content") else str(last_user_msg)

            # 直接从checkpointer获取历史消息进行检索
            try:
                checkpoint_tuple = await memory_manager.checkpointer.aget(None)
                if checkpoint_tuple:
                    checkpoint, metadata = checkpoint_tuple
                    historical_messages = checkpoint.get("messages", [])

                    # 从历史消息中查找相关内容
                    relevant_memories = []
                    query_lower = query.lower()
                    for msg in historical_messages[-20:]:  # 只检查最近20条消息
                        if hasattr(msg, 'content') and query_lower in msg.content.lower():
                            relevant_memories.append({
                                "content": msg.content,
                                "type": "historical_message",
                                "timestamp": getattr(msg, 'timestamp', None)
                            })
                        if len(relevant_memories) >= memory_manager.config.retrieval_k:
                            break
                else:
                    relevant_memories = []
            except Exception:
                relevant_memories = []

            # 构建记忆上下文
            memory_context_parts = []
            if relevant_memories:
                memory_context_parts.append("相关历史对话：")

                for i, memory in enumerate(relevant_memories, 1):
                    if "message" in memory:
                        msg = memory["message"]
                        msg_type = msg.type if hasattr(msg, "type") else "unknown"
                        msg_content = msg.content if hasattr(msg, "content") else str(msg)

                        memory_context_parts.append(f"{i}. {msg_type}: {msg_content}")

                        # 如果是其他会话的记忆，添加会话标识
                        if memory.get("session_id"):
                            memory_context_parts[-1] += f" (会话: {memory['session_id'][:8]}...)"

            memory_context = "\n\n".join(memory_context_parts) if memory_context_parts else ""

            return {
                "retrieved_memories": relevant_memories,
                "memory_context": memory_context,
                "retrieval_count": len(relevant_memories)
            }

        except Exception as e:
            logger.error(f"记忆检索失败: {str(e)}")
            return {
                "retrieved_memories": [],
                "memory_context": "",
                "error": str(e)
            }

    return checkpoint_memory_retrieval_node


def create_checkpoint_memory_summarization_node(
    memory_manager: CheckpointMemoryManager
):
    """
    创建基于checkpointer的记忆总结节点

    当对话过长时自动生成总结

    Args:
        memory_manager: 记忆管理器

    Returns:
        节点函数
    """
    async def checkpoint_memory_summarization_node(state: AgentState) -> Dict[str, Any]:
        """
        记忆总结节点

        检查是否需要总结，如果需要则生成总结并压缩消息历史
        """
        try:
            messages = state.get("messages", [])

            if not memory_manager.should_summarize(messages):
                return {"summarized": False}

            # 提取需要总结的消息（保留最近的一些消息）
            keep_recent = 10
            messages_to_summarize = messages[:-keep_recent] if len(messages) > keep_recent else []
            messages_to_keep = messages[-keep_recent:] if len(messages) >= keep_recent else messages

            if not messages_to_summarize:
                return {"summarized": False}

            # 生成总结
            summary_message = await memory_manager.summarize_conversation(
                messages_to_summarize,
                thread_id
            )

            if summary_message:
                # 合并总结和保留的消息
                new_messages = [summary_message] + messages_to_keep

                logger.info(f"对话总结完成: 原始消息 {len(messages_to_summarize)} -> 总结消息 1 + 保留消息 {len(messages_to_keep)}")

                return {
                    "messages": new_messages,
                    "summarized": True,
                    "original_message_count": len(messages_to_summarize),
                    "summary_length": len(summary_message.content)
                }
            else:
                # 如果总结失败，使用简单的截断
                logger.warning("总结生成失败，使用消息截断")
                return {
                    "messages": messages_to_keep,
                    "summarized": False,
                    "truncated": True
                }

        except Exception as e:
            logger.error(f"记忆总结失败: {str(e)}")
            # 出错时保留所有消息
            return {
                "summarized": False,
                "error": str(e)
            }

    return checkpoint_memory_summarization_node


def create_checkpoint_memory_cleanup_node(
    memory_manager: CheckpointMemoryManager
):
    """
    创建记忆清理节点

    定期清理旧的会话数据

    Args:
        memory_manager: 记忆管理器

    Returns:
        节点函数
    """
    async def checkpoint_memory_cleanup_node(state: AgentState) -> Dict[str, Any]:
        """
        记忆清理节点

        清理过期的会话数据（通常在会话开始时执行）
        """
        try:
            # 执行清理操作
            cleaned_count = await memory_manager.cleanup_old_sessions()

            return {
                "cleanup_performed": True,
                "cleaned_sessions": cleaned_count
            }

        except Exception as e:
            logger.error(f"记忆清理失败: {str(e)}")
            return {
                "cleanup_performed": False,
                "error": str(e)
            }

    return checkpoint_memory_cleanup_node


def create_checkpoint_memory_stats_node(
    memory_manager: CheckpointMemoryManager
):
    """
    创建记忆统计节点

    获取记忆系统的统计信息

    Args:
        memory_manager: 记忆管理器

    Returns:
        节点函数
    """
    def checkpoint_memory_stats_node(state: AgentState) -> Dict[str, Any]:
        """
        记忆统计节点

        返回记忆系统的统计信息
        """
        try:
            # 返回基本的配置统计信息
            stats = {
                "config": {
                    "max_message_history": memory_manager.config.max_message_history,
                    "summarization_threshold": memory_manager.config.summarization_threshold,
                    "retrieval_k": memory_manager.config.retrieval_k,
                }
            }

            return {
                "memory_stats": stats,
                "stats_generated": True
            }

        except Exception as e:
            logger.error(f"获取记忆统计失败: {str(e)}")
            return {
                "memory_stats": {"error": str(e)},
                "stats_generated": False
            }

    return checkpoint_memory_stats_node
