# -*- coding: utf-8 -*-
"""
@File    : react.py
@Time    : 2025/12/9 14:39
@Desc    : 基于LangGraph构建的ReactAgent
"""
import json
import traceback
from typing import Dict, Any, List, Optional, Literal
from langgraph.graph import START, END
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.base import BaseStore
from langgraph.types import interrupt, Command

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

    # 最近一次模型提出的工具调用
    pending_tool_calls: list[dict[str, Any]] | None
    # [
    #     {
    #         "name": "search",
    #         "arguments": {...}
    #     },
    #     ...
    # ]

    # 人工确认结果
    human_decision: Literal["approve", "reject", "modify"] | None
    human_arguments: list[dict[str, Any]] | None


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
            self.add_node("review_tools_call", self._human_confirm_node)
            self.add_node("tools_call", self._call_tools_node)

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
                    "review_tools_call": "review_tools_call",
                    END: END
                }
            )
            # self.add_conditional_edges(
            #     source="tools_confirm",
            #     path=self._route_after_human,
            #     path_map={
            #         "tools_call": "tools_call",
            #         "generate": "generate"
            #     }
            # )
            self.add_edge("review_tools_call", "tools_call")
            # 工具执行后，把工具结果写回messages，再让LLM继续
            # 注意：记忆总结会在每次生成后自动触发（通过状态变化）
            self.add_edge("tools_call", "generate")
        else:
            self.add_edge("generate", END)

    async def _generate_node(self, state: ReactGraphState, resume: dict | None = None) -> Dict[str, Any]:
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
                "response": message.content,
                "pending_tool_calls": None,
                "human_decision": None,
                "human_arguments": None
            }

        except Exception as e:
            traceback.format_exc()
            error_content = f"抱歉，生成响应时出错：{e}"
            return {
                "messages": [AIMessage(content=error_content)],
                "response": error_content,
                "error": str(e),
                "pending_tool_calls": None,
                "human_decision": None,
                "human_arguments": None
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
                return "review_tools_call"

        return END

    async def _call_tools_node(self, state: ReactGraphState) -> dict:
        tools_map = {tool.name: tool for tool in self.tools}
        tool_messages = []
        human_decision = state.get("human_decision")
        if human_decision == "approve":
            tool_calls = state["pending_tool_calls"]
        elif human_decision == "modify":
            tool_calls = state["human_arguments"]
        else:
            tool_calls = state["pending_tool_calls"]
            tool_messages = [
                ToolMessage(content="用户在审核后拒绝了本次工具调用，请按要求和约束条件直接生成答案。",
                            tool_call_id=tool_call['id'])
                for tool_call in tool_calls
            ]
            return {"messages": tool_messages}
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_id = tool_call["id"]
            if tool_name not in tools_map:
                tool_message = ToolMessage(
                    content=f"工具 '{tool_name}' 未找到",
                    tool_call_id=tool_id
                )
                tool_messages.append(tool_message)
                continue

            tool = tools_map[tool_name]

            try:
                # 执行工具
                result = await tool.ainvoke(tool_call["arguments"])
                # 转换为字符串
                if isinstance(result, dict):
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)
                else:
                    result_str = str(result)
                # 创建工具消息
                tool_message = ToolMessage(
                    content=result_str,
                    tool_call_id=tool_id
                )
                tool_messages.append(tool_message)
            except Exception as e:
                tool_message = ToolMessage(
                    content=f"工具执行失败: {e}",
                    tool_call_id=tool_id
                )
                tool_messages.append(tool_message)

        return {"messages": tool_messages}

    # def _route_after_human(self, state: ReactGraphState) -> str:
    #     """
    #     人工确认后路由下一个节点
    #     """
    #     human_decision = state.get("human_decision")
    #     if human_decision in ("approve", "modify"):
    #         return "tools_call"
    #     return "generate"

    async def _human_confirm_node(self, state: ReactGraphState) -> dict:
        """
        调用工具前进行人工确认
        """
        last_msg = state["messages"][-1]
        pending_tool_calls = [
            {
                "name": tool_call["name"],
                "arguments": tool_call["args"],
                "id": tool_call["id"]
            }
            for tool_call in last_msg.tool_calls
        ]
        human_resume = interrupt({
            "type": "tool_confirm",
            "human_arguments": pending_tool_calls
        })

        return {
            "pending_tool_calls": pending_tool_calls,
            "human_decision": human_resume["decision"],
            "human_arguments": human_resume["human_arguments"]
        }


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
