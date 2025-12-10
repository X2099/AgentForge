# -*- coding: utf-8 -*-
"""
@File    : conversation_workflow.py
@Time    : 2025/12/9 14:39
@Desc    : 基于LangGraph标准的对话工作流
"""
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool

from ..core.graphs.base_graph import BaseGraph
from ..core.state.base_state import GraphState
from ..llm.llm_client import LLMClient


class ConversationState(GraphState):
    """对话状态"""
    # 从GraphState继承messages等基础字段
    query: Optional[str]
    response: Optional[str]
    knowledge_base_enabled: bool
    retrieved_context: Optional[str]


class ConversationWorkflow(BaseGraph):
    """
    对话工作流
    
    标准的对话流程：检索 -> LLM生成 -> 响应
    """

    def __init__(
            self,
            llm_client: LLMClient,
            tools: Optional[List[BaseTool]] = None,
            knowledge_base: Optional[Any] = None,
            system_prompt: Optional[str] = None
    ):
        """
        初始化对话工作流
        
        Args:
            llm_client: LLM客户端
            tools: 工具列表
            knowledge_base: 知识库（可选）
            system_prompt: 系统提示词
        """
        super().__init__(
            name="conversation_workflow",
            description="标准对话工作流",
            state_type=ConversationState
        )

        self.llm_client = llm_client
        self.tools = tools or []
        self.knowledge_base = knowledge_base
        self.system_prompt = system_prompt or "你是一个有帮助的AI助手。"

    def build(self):
        """构建对话工作流"""
        # 添加节点
        self.add_node("retrieve", self._retrieve_node)
        self.add_node("generate", self._generate_node)

        # 构建流程
        # 如果启用知识库，先检索
        if self.knowledge_base:
            self.add_edge(START, "retrieve")
            self.add_edge("retrieve", "generate")
        else:
            self.add_edge(START, "generate")

        # 生成后结束
        self.add_edge("generate", END)

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
        messages = list(state.get("messages", []))

        # 添加系统提示词
        system_prompt = self.system_prompt
        if state.get("retrieved_context"):
            system_prompt += f"\n\n相关背景信息：\n{state['retrieved_context']}"

        formatted_messages = [{"role": "system", "content": system_prompt}]

        # 添加历史消息
        for msg in messages:
            if isinstance(msg, dict):
                formatted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            elif isinstance(msg, BaseMessage):
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                formatted_messages.append({"role": role, "content": msg.content})

        # 调用LLM
        try:
            response = await self.llm_client.achat(
                messages=formatted_messages,
                tools=self.tools if self.tools else None
            )

            # response是AIMessage类型
            content = response.content if hasattr(response, "content") else str(response)

            # 创建AI消息
            ai_message = AIMessage(content=content)

            return {
                "messages": [ai_message],
                "response": content
            }

        except Exception as e:
            error_content = f"抱歉，生成响应时出错：{str(e)}"
            return {
                "messages": [AIMessage(content=error_content)],
                "response": error_content,
                "error": str(e)
            }


def create_conversation_workflow(
        llm_client: LLMClient,
        tools: Optional[List[BaseTool]] = None,
        knowledge_base: Optional[Any] = None,
        system_prompt: Optional[str] = None
) -> StateGraph:
    """
    创建对话工作流（便捷函数）
    
    Args:
        llm_client: LLM客户端
        tools: 工具列表
        knowledge_base: 知识库
        system_prompt: 系统提示词
        
    Returns:
        编译后的工作流图
    """
    workflow = ConversationWorkflow(
        llm_client=llm_client,
        tools=tools,
        knowledge_base=knowledge_base,
        system_prompt=system_prompt
    )

    return workflow.compile()
