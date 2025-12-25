# -*- coding: utf-8 -*-
"""
@File    : memory_nodes.py
@Time    : 2025/12/16
@Desc    : 基于LangGraph checkpointer的记忆节点
"""
import traceback
from typing import Dict, Any
from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from ..core.state.base_state import GraphState
from .memory_manager import CheckpointMemoryManager

import logging

logger = logging.getLogger(__name__)


def create_memory_summary_node(
        memory_manager: CheckpointMemoryManager
):
    """
    创建基记忆总结节点
    """

    async def memory_summary_node(state: GraphState, config: RunnableConfig, store: BaseStore) -> Dict[str, Any]:
        """
        记忆总结节点
        检查是否需要总结，如果需要则生成总结并压缩消息历史
        """
        print(f"memory_summary_node()...{store}")
        messages = state.get("messages", [])
        try:
            thread_id = config["configurable"]["thread_id"]
            namespace = ("user_id", "memories")
            memories = store.get(namespace, thread_id)
            # 获取上一次的记忆摘要
            last_summary = ""
            if memories:
                last_summary = memories.value.get("messages_summary", "")
            if not memory_manager.should_summarize(messages):
                return {
                    "messages_summary": last_summary
                }

            # 提取需要总结的消息（保留最近的一些消息）
            # keep_recent = 10
            keep_recent = 5
            messages_to_summarize = messages[:-keep_recent] if len(messages) > keep_recent else []
            messages_to_keep = messages[-keep_recent:] if len(messages) >= keep_recent else messages

            if not messages_to_summarize:
                return {
                    "messages_summary": last_summary
                }

            # 合并总结和保留的消息
            if last_summary:
                last_summary_message = SystemMessage(content=last_summary)
                messages_to_summarize = [last_summary_message] + messages_to_summarize
            # 生成新的摘要
            new_summary_message = await memory_manager.summarize_conversation(
                messages_to_summarize,
                config["configurable"]["thread_id"]
            )

            if new_summary_message:
                new_summary = new_summary_message.content
                store.put(namespace, thread_id, {"messages_summary": new_summary})
                logger.info(
                    f"对话总结完成: 原始消息 {len(messages_to_summarize)} -> 总结消息 1 + 保留消息 {len(messages_to_keep)}")
                return {
                    "messages": [RemoveMessage(id=m.id) for m in messages_to_summarize],  # 移除被总结过的消息列表
                    "messages_summary": new_summary
                }
            else:
                # 如果总结失败，使用简单的截断
                logger.warning("总结记忆生成失败")
                return {
                    "messages_summary": last_summary
                }

        except Exception as e:
            logger.error(f"记忆总结失败: {e} -> {traceback.format_exc()}")
            # 出错时保留所有消息
            return {
                "error": str(e)
            }

    return memory_summary_node


def create_memory_trim_node(
        memory_manager: CheckpointMemoryManager
):
    """
    创建记忆裁剪节点
    """

    async def memory_trim_node(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
        print("memory_trim_node()...")
        try:
            try:
                checkpoint_tuple = await memory_manager.checkpointer.aget(config)
                if not checkpoint_tuple:
                    return {}

                checkpoint, metadata = checkpoint_tuple
                historical_messages = checkpoint.get("messages", [])
            except Exception as e:
                logger.error(f"获取最新的检查点异常：{e} -> {traceback.format_exc()}")
                return {"error": str(e)}

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

            return {
                "messages": all_messages,
                "historical_message_count": len(historical_messages)
            }

        except Exception as e:
            logger.error(f"记忆加载失败: {e} -> {traceback.format_exc()}")
            return {"error": str(e)}

    return memory_trim_node


def create_memory_retrieval_node(
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

    async def memory_retrieval_node(state: GraphState, config: RunnableConfig, store: BaseStore) -> Dict[str, Any]:
        """
        记忆检索节点

        检索与当前查询相关的历史记忆
        """
        print("memory_retrieval_node()...")
        try:
            messages = state.get("messages", [])

            if not messages:
                return {"messages": messages}

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

    return memory_retrieval_node


def create_memory_cleanup_node(
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

    async def memory_cleanup_node(state: GraphState) -> Dict[str, Any]:
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

    return memory_cleanup_node


def create_memory_stats_node(
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

    def memory_stats_node(state: GraphState) -> Dict[str, Any]:
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

    return memory_stats_node
