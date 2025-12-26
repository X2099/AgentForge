# -*- coding: utf-8 -*-
"""
@File    : react.py
@Time    : 2025/12/9 14:39
@Desc    : 基于LangGraph构建的ReactAgent
"""
import traceback
from typing import Dict, Any, List, Optional
from langgraph.graph import START, END
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.base import BaseStore

from ..core.graphs.base_graph import BaseGraph
from ..core.state.base_state import GraphState
from ..core.nodes.tool_nodes import create_tool_executor_node
from ..memory.memory_manager import CheckpointMemoryManager, CheckpointMemoryConfig
from ..memory.memory_nodes import (
    create_memory_trim_node,
    create_memory_retrieval_node,
    create_memory_summary_node
)


class ReactGraphState(GraphState):
    """对话状态"""
    query: Optional[str]
    context: Optional[str]
    messages_summary: Optional[str]  # 记忆摘要


class ReactGraph(BaseGraph):
    """
    ReAct Agent工作流
    """

    def __init__(
            self,
            llm: BaseChatModel,
            tools: Optional[List[BaseTool]] = None,
            system_prompt: Optional[str] = None,
            checkpointer: Optional[BaseCheckpointSaver] = None
    ):
        """
        初始化对话工作流

        Args:
            llm: LLM客户端
            tools: 工具列表
            system_prompt: 系统提示词
            checkpointer: LangGraph检查点保存器
        """
        super().__init__(
            name="langgraph_react_agent",
            description="基于LangGraph构建的ReAct Agent",
            state_type=ReactGraphState
        )

        self.llm = llm
        self.tools = tools or []
        self.system_prompt = system_prompt or self._build_default_system_prompt()

        # 记忆相关 - 基于checkpointer
        self.checkpointer = checkpointer or InMemorySaver()  # 默认使用内存保存器
        self.memory_config = CheckpointMemoryConfig()
        self.memory_manager = CheckpointMemoryManager(
            checkpointer=self.checkpointer,
            config=self.memory_config,
            llm_client=llm
        )

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
            self.add_node("mcp", create_tool_executor_node(self.tools))

        # 添加记忆节点
        memory_summary = create_memory_summary_node(self.memory_manager)
        memory_trim = create_memory_trim_node(self.memory_manager)
        memory_retrieval = create_memory_retrieval_node(self.memory_manager)

        self.add_node("memory_summary", memory_summary)
        # self.add_node("memory_trim", memory_trim)
        # self.add_node("memory_retrieval", memory_retrieval)

        # 设置边
        self.add_edge(START, "memory_summary")
        # self.add_edge("memory_summary", "memory_trim")
        # self.add_edge("memory_trim", "memory_retrieval")
        # self.add_edge("memory_retrieval", "generate")
        self.add_edge("memory_summary", "generate")

        # 生成后的路由：如有工具调用，先执行工具再回到生成；否则结束
        if self.tools:
            self.add_conditional_edges(
                source="generate",
                path=self._should_use_tools,
                path_map={
                    "mcp": "mcp",
                    END: END
                }
            )
            # 工具执行后，把工具结果写回messages，再让LLM继续
            # 注意：记忆总结会在每次生成后自动触发（通过状态变化）
            self.add_edge("mcp", "generate")
        else:
            self.add_edge("generate", END)

    async def _generate_node(self, state: ReactGraphState) -> Dict[str, Any]:
        """LLM生成节点"""
        # 准备消息
        system_prompt = self.system_prompt

        # 添加知识库上下文
        if state.get("messages_summary"):
            system_prompt += f"\n\n## 这是当前对话的历史摘要，帮助你理解之前的讨论：：\n{state['messages_summary']}"

        print("messages_summary ==> ", state.get("messages_summary"))
        print("messages length ==> ", len(state.get("messages")))

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
            traceback.format_exc()
            error_content = f"抱歉，生成响应时出错：{e}"
            return {
                "messages": [AIMessage(content=error_content)],
                "response": error_content,
                "error": str(e)
            }

    def _should_use_tools(self, state: ReactGraphState) -> str:
        """
        判断当前回复是否包含工具调用
        """
        messages = state["messages"]
        if not messages:
            return END
        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
            tool_calls = last_msg.tool_calls
            if tool_calls:
                return "mcp"

        return END


def create_react_graph(
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        store: Optional[BaseStore] = None
) -> CompiledStateGraph:
    """
    创建对话智能体

    Args:
        llm: LLM客户端
        tools: 工具列表
        system_prompt: 系统提示词
        checkpointer: LangGraph检查点保存器，用于实现记忆功能
        store: LangGraph长期记忆保存器

    Returns:
        编译后的工作流图
    """
    graph = ReactGraph(
        llm=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer
    )

    # 编译时传入checkpointer, store
    return graph.compile(checkpointer=checkpointer, store=store)
