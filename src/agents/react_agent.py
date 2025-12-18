# -*- coding: utf-8 -*-
"""
@File    : react_agent.py
@Time    : 2025/12/9 14:39
@Desc    : 基于LangGraph标准的对话Agent
"""
import operator
from typing import Dict, Any, List, Optional, Annotated
from langgraph.graph import START, END
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from ..core.graphs.base_graph import BaseGraph
from ..core.state.base_state import GraphState, DisplayMessage
from ..core.nodes.tool_nodes import create_tool_executor_node
from ..memory.checkpoint_memory_manager import CheckpointMemoryManager, CheckpointMemoryConfig
from ..memory.checkpoint_memory_nodes import (
    create_checkpoint_memory_loader_node,
    create_checkpoint_memory_retrieval_node,
    create_checkpoint_memory_summarization_node
)


class ConversationState(GraphState):
    """对话状态"""
    query: Optional[str]
    context: Optional[str]


class ConversationGraph(BaseGraph):
    """
    对话工作流
    
    标准的对话流程：检索 -> LLM生成 -> 响应
    """

    def __init__(
            self,
            llm: BaseChatModel,
            tools: Optional[List[BaseTool]] = None,
            knowledge_base: Optional[Any] = None,
            system_prompt: Optional[str] = None,
            checkpointer: Optional[BaseCheckpointSaver] = None
    ):
        """
        初始化对话工作流

        Args:
            llm: LLM客户端
            tools: 工具列表
            knowledge_base: 知识库（可选）
            system_prompt: 系统提示词
            checkpointer: LangGraph检查点保存器
        """
        super().__init__(
            name="conversation_workflow",
            description="标准对话工作流",
            state_type=ConversationState
        )

        self.llm = llm
        self.tools = tools or []
        self.knowledge_base = knowledge_base
        self.system_prompt = system_prompt or self._build_default_system_prompt()

        # 记忆相关 - 基于checkpointer
        self.checkpointer = checkpointer or InMemorySaver()  # 默认使用内存保存器
        self.memory_config = CheckpointMemoryConfig()
        self.memory_manager = CheckpointMemoryManager(
            checkpointer=self.checkpointer,
            config=self.memory_config,
            llm_client=llm
        )
        self.enable_memory = True
        self.max_message_history = 100

    @staticmethod
    def _build_default_system_prompt() -> str:
        """构建默认系统提示词"""

        default_system_prompt = "你是一个智能AI助手，能够帮助用户解答问题、提供信息和执行各种任务。"

        return default_system_prompt

    def build(self):
        """构建对话工作流"""
        # 添加核心节点
        self.add_node("generate", self._generate_node)

        if self.tools:
            # 工具执行节点，执行LLM返回的tool_calls
            self.add_node("tools", create_tool_executor_node(self.tools))

        # 如果启用记忆，添加记忆节点
        if self.enable_memory:
            memory_loader = create_checkpoint_memory_loader_node(self.memory_manager)
            memory_retrieval = create_checkpoint_memory_retrieval_node(self.memory_manager)
            memory_summarization = create_checkpoint_memory_summarization_node(self.memory_manager)

            self.add_node("memory_loader", memory_loader)
            self.add_node("memory_retrieval", memory_retrieval)
            self.add_node("memory_summarization", memory_summarization)

        # 如果启用知识库，添加检索节点
        if self.knowledge_base:
            self.add_node("retrieve", self._retrieve_node)

        # 如果启用记忆，先加载历史记忆
        if self.enable_memory:
            self.add_edge(START, "memory_loader")
            self.add_edge("memory_loader", "memory_retrieval")
            current_start = "memory_retrieval"

        # 然后进行知识库检索（如果启用）
        if self.knowledge_base:
            self.add_edge(START, "retrieve")
            current_start = "retrieve"

        # 从最后一个准备节点连接到生成节点
        self.add_edge(START, "generate")

        # 生成后的路由：如有工具调用，先执行工具再回到生成；否则结束
        if self.tools:
            self.add_conditional_edges(
                source="generate",
                path=self._should_use_tools,
                path_map={
                    "tools": "tools",
                    "end": END
                }
            )
            # 工具执行后，把工具结果写回messages，再让LLM继续
            # 注意：记忆总结会在每次生成后自动触发（通过状态变化）
            self.add_edge("tools", "generate")
        else:
            self.add_edge("generate", END)

    def _truncate_messages_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        消息截断节点

        管理短期记忆，确保消息数量在合理范围内。
        LangGraph的checkpointer会自动处理长期记忆。
        """
        messages = state.get("messages", [])

        if not messages:
            return {}

        if len(messages) <= self.max_message_history:
            return {}

        # 保留系统消息和最近的消息
        system_messages = []
        other_messages = []

        for msg in messages:
            if hasattr(msg, "type") and msg.type == "system":
                system_messages.append(msg)
            else:
                other_messages.append(msg)

        # 保留最近的消息
        keep_count = self.max_message_history - len(system_messages)
        if keep_count > 0:
            recent_messages = other_messages[-keep_count:]
        else:
            recent_messages = []

        new_messages = system_messages + recent_messages

        return {"messages": new_messages}

    def _retrieve_node(self, state: ConversationState) -> Dict[str, Any]:
        """知识库检索节点"""
        if not self.knowledge_base or not state.get("query"):
            return {"retrieved_context": ""}

        try:
            # 从知识库检索
            query = state["query"]
            documents = self.knowledge_base.search(query, k=3)

            # 构建上下文
            context_parts = []
            for i, doc in enumerate(documents, 1):
                content = doc.content[:200] if hasattr(doc, "content") else str(doc)[:200]
                context_parts.append(f"[文档{i}] {content}")

            context = "\n\n".join(context_parts)
            return {"retrieved_context": context}

        except Exception as e:
            return {"retrieved_context": f"检索错误: {str(e)}"}

    async def _generate_node(self, state: ConversationState) -> Dict[str, Any]:
        """LLM生成节点"""
        # 准备消息
        system_prompt = self.system_prompt

        # 添加知识库上下文
        if state.get("context"):
            system_prompt += f"\n\n## 当前查询的相关知识库检索结果：\n{state['context']}" \
                             f"\n\n请基于以上检索结果来回答用户的问题。如果检索结果不足以回答问题，请说明情况。"

        input_messages = [SystemMessage(content=system_prompt)] + state.get("messages", [])

        # 调用LLM
        try:
            if self.tools:
                message = await self.llm.bind_tools(self.tools).ainvoke(input_messages)
            else:
                message = await self.llm.ainvoke(input_messages)

            return {
                "messages": [message],
                "response": message.content
            }

        except Exception as e:
            error_content = f"抱歉，生成响应时出错：{str(e)}"
            return {
                "messages": [AIMessage(content=error_content)],
                "response": error_content,
                "error": str(e)
            }

    def _should_use_tools(self, state: ConversationState) -> str:
        """
        判断当前回复是否包含工具调用
        """
        messages = state["messages"]
        if not messages:
            return "end"
        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
            tool_calls = last_msg.tool_calls
            if tool_calls:
                return "tools"

        return "end"


def create_react_agent(
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        knowledge_base: Optional[Any] = None,
        system_prompt: Optional[str] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None
) -> CompiledStateGraph:
    """
    创建对话智能体

    Args:
        llm: LLM客户端
        tools: 工具列表
        knowledge_base: 知识库
        system_prompt: 系统提示词
        checkpointer: LangGraph检查点保存器，用于实现记忆功能

    Returns:
        编译后的工作流图
    """
    graph = ConversationGraph(
        llm=llm,
        tools=tools,
        knowledge_base=knowledge_base,
        system_prompt=system_prompt,
        checkpointer=checkpointer
    )

    # 编译时传入checkpointer
    return graph.compile(checkpointer=checkpointer)
