# -*- coding: utf-8 -*-
"""
@File    : memory_nodes.py
@Time    : 2025/12/9
@Desc    : 基于LangGraph标准的记忆节点
"""
from typing import Dict, Any, List, Optional, Sequence, Annotated, Tuple
from datetime import datetime

from langgraph.graph.message import add_messages
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..core.state.base_state import AgentState
from .memory_manager import MemoryManager
from ..llm.llm_client import LLMClient

import logging

logger = logging.getLogger(__name__)


def create_memory_retrieval_node(
    memory_manager: MemoryManager,
    llm_client: Optional[LLMClient] = None
):
    """
    创建记忆检索节点
    
    从长期记忆中检索相关记忆
    
    Args:
        memory_manager: 记忆管理器
        llm_client: LLM客户端（可选，用于语义检索）
        
    Returns:
        节点函数
    """
    async def memory_retrieval_node(state: AgentState) -> Dict[str, Any]:
        """
        记忆检索节点
        
        从检查点中检索相关的历史记忆
        """
        try:
            thread_id = state.get("thread_id", "default")
            messages = state.get("messages", [])
            
            if not messages:
                return {}
            
            # 获取当前查询（最后一条用户消息）
            last_user_msg = None
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
                    last_user_msg = msg
                    break
            
            if not last_user_msg:
                return {}
            
            query = last_user_msg.content if hasattr(last_user_msg, "content") else str(last_user_msg)
            
            # 从检查点列表中检索相关记忆
            from langchain_core.runnables import RunnableConfig
            
            # alist返回CheckpointList，包含checkpoint_id列表
            checkpoint_list = await memory_manager.checkpointer.alist(
                RunnableConfig(configurable={"thread_id": thread_id}),
                limit=memory_manager.config.retrieval_k
            )
            
            retrieved_memories = []
            
            # 遍历检查点ID，加载每个检查点
            # checkpoint_list.checkpoints是包含checkpoint_id的列表
            checkpoint_ids = checkpoint_list.checkpoints if hasattr(checkpoint_list, 'checkpoints') else []
            for checkpoint_id in checkpoint_ids[:memory_manager.config.retrieval_k]:
                try:
                    checkpoint_tuple = await memory_manager.checkpointer.aget(
                        RunnableConfig(configurable={"thread_id": thread_id}),
                        checkpoint_id
                    )
                    
                    if checkpoint_tuple:
                        checkpoint, _ = checkpoint_tuple

                        # 从检查点中提取消息
                        checkpoint_state = checkpoint.get("channel_values", {})
                        checkpoint_messages = checkpoint_state.get("messages", [])

                        if checkpoint_messages:
                            # 简单的关键词匹配（可以扩展为语义检索）
                            relevant = False
                            for msg in checkpoint_messages:
                                if hasattr(msg, "content"):
                                    content = msg.content.lower()
                                    if any(keyword in content for keyword in query.lower().split()[:3]):
                                        relevant = True
                                        break

                            if relevant:
                                retrieved_memories.append({
                                    "checkpoint_id": checkpoint.get("ts", ""),
                                    "messages": checkpoint_messages[-2:] if checkpoint_messages else []  # 保留最后两条消息
                                })
                except Exception as e:
                    logger.debug(f"加载检查点失败: {checkpoint_id}, {str(e)}")
                    continue
            
            # 构建记忆上下文
            memory_context = ""
            if retrieved_memories:
                memory_context_parts = ["相关历史对话："]
                for i, mem in enumerate(retrieved_memories, 1):
                    mem_messages = mem["messages"]
                    if mem_messages:
                        mem_text = "\n".join([
                            f"{msg.type if hasattr(msg, 'type') else 'user'}: {msg.content if hasattr(msg, 'content') else str(msg)}"
                            for msg in mem_messages
                        ])
                        memory_context_parts.append(f"{i}. {mem_text}")
                
                memory_context = "\n\n".join(memory_context_parts)
            
            return {
                "retrieved_memories": retrieved_memories,
                "memory_context": memory_context
            }
            
        except Exception as e:
            logger.error(f"记忆检索失败: {str(e)}")
            return {
                "retrieved_memories": [],
                "memory_context": ""
            }
    
    return memory_retrieval_node


def create_memory_summarization_node(
    memory_manager: MemoryManager,
    llm_client: LLMClient
):
    """
    创建记忆总结节点
    
    当消息历史过长时，自动总结并压缩
    
    Args:
        memory_manager: 记忆管理器
        llm_client: LLM客户端
        
    Returns:
        节点函数
    """
    async def memory_summarization_node(state: AgentState) -> Dict[str, Any]:
        """
        记忆总结节点
        
        总结历史对话，减少消息数量
        """
        try:
            messages = state.get("messages", [])
            
            if not memory_manager.should_summarize(messages):
                return {}
            
            # 提取需要总结的消息（保留最近的）
            recent_count = 10  # 保留最近10条消息
            messages_to_summarize = list(messages[:-recent_count])
            messages_to_keep = list(messages[-recent_count:])
            
            if not messages_to_summarize:
                return {}
            
            # 生成总结
            conversation_text = "\n".join([
                f"{msg.type if hasattr(msg, 'type') else 'user'}: {msg.content if hasattr(msg, 'content') else str(msg)}"
                for msg in messages_to_summarize
            ])
            
            summary_prompt = f"""请总结以下对话的主要内容，保留关键信息和决策点：

{conversation_text}

总结（简洁，保留关键信息）："""
            
            # 调用LLM生成总结
            summary_response = await llm_client.achat([HumanMessage(content=summary_prompt)])
            summary_text = summary_response.content if hasattr(summary_response, "content") else str(summary_response)
            
            # 创建总结消息
            summary_message = SystemMessage(
                content=f"历史对话总结：{summary_text}"
            )
            
            # 合并总结和保留的消息
            new_messages = [summary_message] + messages_to_keep
            
            # 保存总结到长期记忆（实际保存由图的checkpointer自动处理）
            thread_id = state.get("thread_id", "default")
            # 这里只是记录日志，实际的检查点保存由LangGraph图执行时自动处理
            logger.info(f"生成总结: thread_id={thread_id}, 原始消息数={len(messages_to_summarize)}")
            
            return {
                "messages": new_messages
            }
            
        except Exception as e:
            logger.error(f"记忆总结失败: {str(e)}")
            # 如果总结失败，使用简单截断
            messages = state.get("messages", [])
            truncated = memory_manager.truncate_messages(messages)
            return {
                "messages": truncated
            }
    
    return memory_summarization_node


def create_memory_update_node(
    memory_manager: MemoryManager
):
    """
    创建记忆更新节点
    
    在对话结束后保存重要信息到长期记忆
    
    Args:
        memory_manager: 记忆管理器
        
    Returns:
        节点函数
    """
    async def memory_update_node(state: AgentState) -> Dict[str, Any]:
        """
        记忆更新节点
        
        保存当前状态到长期记忆
        """
        try:
            thread_id = state.get("thread_id", "default")
            messages = state.get("messages", [])
            
            if not messages:
                return {}
            
            # 只保存最近的交互（用户消息+AI回复）
            recent_messages = messages[-2:] if len(messages) >= 2 else messages
            
            # 判断是否值得保存（包含工具调用、重要信息等）
            should_save = False
            
            # 如果包含工具调用，值得保存
            last_message = messages[-1] if messages else None
            if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
                should_save = True
            
            # 如果对话较长，值得保存
            if len(messages) >= 5:
                should_save = True
            
            if should_save:
                # 实际的检查点保存由LangGraph图执行时通过checkpointer自动处理
                # 这里只是记录日志
                logger.debug(f"标记记忆保存: thread_id={thread_id}, 消息数={len(recent_messages)}")
            
            return {}
            
        except Exception as e:
            logger.error(f"记忆更新失败: {str(e)}")
            return {}
    
    return memory_update_node


def create_memory_truncation_node(
    memory_manager: MemoryManager
):
    """
    创建消息截断节点
    
    管理短期记忆，确保消息数量在合理范围内
    
    Args:
        memory_manager: 记忆管理器
        
    Returns:
        节点函数
    """
    def memory_truncation_node(state: AgentState) -> Dict[str, Any]:
        """
        消息截断节点
        
        截断消息历史，保留最近的N条消息
        """
        try:
            messages = state.get("messages", [])
            
            if not messages:
                return {}
            
            # 如果消息数量超过阈值，截断
            truncated = memory_manager.truncate_messages(messages)
            
            if len(truncated) < len(messages):
                logger.debug(f"截断消息: {len(messages)} -> {len(truncated)}")
                return {
                    "messages": truncated
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"消息截断失败: {str(e)}")
            return {}
    
    return memory_truncation_node

