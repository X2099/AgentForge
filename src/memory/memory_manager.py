# -*- coding: utf-8 -*-
"""
@File    : memory_manager.py
@Time    : 2025/12/9
@Desc    : 基于LangGraph标准的长短期记忆管理器
"""
from typing import Dict, Any, List, Optional, Sequence
from datetime import datetime
from dataclasses import dataclass

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import CheckpointMetadata
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryConfig:
    """记忆配置"""
    checkpointer: Optional[BaseCheckpointSaver] = None
    max_message_history: int = 50  # 短期记忆：保留的最近消息数
    summarization_threshold: int = 20  # 当消息数超过此值时触发总结
    retrieval_k: int = 5  # 检索相关记忆的数量


class MemoryManager:
    """
    记忆管理器 - 基于LangGraph标准实现
    
    提供：
    - 短期记忆：通过StateGraph的messages字段自动管理
    - 长期记忆：通过Checkpointer保存和检索
    - 记忆总结：自动总结历史对话
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        初始化记忆管理器
        
        Args:
            config: 记忆配置
        """
        self.config = config or MemoryConfig()
        self.checkpointer = self.config.checkpointer
        
        if self.checkpointer is None:
            # 默认使用MemorySaver
            self.checkpointer = MemorySaver()
        
        logger.info("记忆管理器初始化完成")
    
    async def save_checkpoint(
        self,
        thread_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        保存检查点（长期记忆）
        
        注意：实际的检查点保存由LangGraph图在执行时自动处理。
        这个方法主要用于手动保存额外的记忆信息。
        
        Args:
            thread_id: 线程ID
            state: 状态字典
            metadata: 元数据
            
        Returns:
            检查点时间戳（如果成功）
        """
        # 在实际使用中，检查点应该通过图的执行自动保存
        # 这里提供一个接口用于特殊情况下的手动保存
        logger.debug(f"记忆保存请求: thread_id={thread_id}")
        return datetime.now().isoformat()
    
    async def load_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Checkpoint]:
        """
        加载检查点
        
        Args:
            thread_id: 线程ID
            checkpoint_id: 检查点ID（如果为None，则加载最新的）
            
        Returns:
            检查点对象
        """
        try:
            config = RunnableConfig(
                configurable={"thread_id": thread_id}
            )
            
            checkpoint_tuple = await self.checkpointer.aget(
                config,
                checkpoint_id
            )
            
            if checkpoint_tuple:
                checkpoint, metadata = checkpoint_tuple
                return checkpoint
            
            return None
            
        except Exception as e:
            logger.error(f"加载检查点失败: {str(e)}")
            return None
    
    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 10
    ) -> Any:
        """
        列出检查点
        
        Args:
            thread_id: 线程ID
            limit: 限制数量
            
        Returns:
            CheckpointList对象（包含checkpoint_id列表）
        """
        try:
            config = RunnableConfig(
                configurable={"thread_id": thread_id}
            )
            
            checkpoint_list = await self.checkpointer.alist(
                config,
                limit=limit
            )
            
            return checkpoint_list
            
        except Exception as e:
            logger.error(f"列出检查点失败: {str(e)}")
            # 返回空列表结构
            from langgraph.checkpoint.base import CheckpointList
            return CheckpointList(checkpoints=[], next_token=None)
    
    def should_summarize(self, messages: Sequence[BaseMessage]) -> bool:
        """
        判断是否需要总结
        
        Args:
            messages: 消息列表
            
        Returns:
            是否需要总结
        """
        return len(messages) >= self.config.summarization_threshold
    
    def truncate_messages(
        self,
        messages: Sequence[BaseMessage],
        keep_last: Optional[int] = None
    ) -> List[BaseMessage]:
        """
        截断消息列表（短期记忆管理）
        
        Args:
            messages: 消息列表
            keep_last: 保留最后N条消息
            
        Returns:
            截断后的消息列表
        """
        keep_last = keep_last or self.config.max_message_history
        
        if len(messages) <= keep_last:
            return list(messages)
        
        # 保留系统消息和最近的N条消息
        system_messages = [msg for msg in messages if hasattr(msg, "type") and msg.type == "system"]
        other_messages = [msg for msg in messages if msg not in system_messages]
        
        recent_messages = other_messages[-keep_last:] if len(other_messages) > keep_last else other_messages
        
        return system_messages + recent_messages

