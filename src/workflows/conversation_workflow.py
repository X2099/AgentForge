# -*- coding: utf-8 -*-
"""
@File    : conversation_workflow.py
@Time    : 2025/12/9 14:39
@Desc    : 对话系统工作流
"""
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Dict, Any, List, Annotated


class ConversationState:
    """对话状态（兼容Langchain-Chatchat）"""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    query: str
    history: List[Dict[str, Any]] = None
    response: str = ""
    knowledge_base_enabled: bool = True


def create_conversation_workflow(llm, tools=None, knowledge_base=None):
    """创建对话工作流（对标Conversation Chain）"""

    workflow = StateGraph(ConversationState)

    # 1. 历史管理节点
    def history_manager(state: ConversationState):
        """管理对话历史"""
        # 类似Langchain-Chatchat的历史管理
        max_history = 10
        if len(state.messages) > max_history:
            # 保留系统消息和最近的对话
            system_msgs = [m for m in state.messages if m.get('role') == 'system']
            recent_msgs = state.messages[-max_history + len(system_msgs):]
            state.messages = system_msgs + recent_msgs

        return {"messages": state.messages}

    # 2. 知识库检索节点（如果启用）
    def knowledge_retriever(state: ConversationState):
        """知识库检索"""
        if not state.knowledge_base_enabled or not knowledge_base:
            return {"context": ""}

        # 从最近的消息中提取查询
        last_user_msg = next(
            (m for m in reversed(state.messages) if m.get('role') == 'user'),
            None
        )

        if not last_user_msg:
            return {"context": ""}

        query = last_user_msg.get('content', '')
        documents = knowledge_base.search(query, k=3)

        # 构建知识上下文
        context_parts = []
        for doc in documents:
            context_parts.append(f"相关文档：{doc.content[:200]}...")

        return {"context": "\n".join(context_parts) if context_parts else ""}

    # 3. LLM生成节点
    def llm_generator(state: ConversationState):
        """生成回复"""
        # 准备消息
        messages = []

        # 添加系统提示
        system_prompt = """你是一个有帮助的AI助手。"""
        if state.get('context'):
            system_prompt += f"\n\n相关背景信息：\n{state.context}"

        messages.append({"role": "system", "content": system_prompt})

        # 添加历史消息
        messages.extend(state.messages)

        # 调用LLM
        response = llm.chat(messages)

        return {
            "response": response.get_content(),
            "messages": state.messages + [
                {"role": "assistant", "content": response.get_content()}
            ]
        }

    # 4. 工具调用节点（如果启用）
    def tool_executor(state: ConversationState):
        """执行工具调用"""
        if not tools:
            return {}

        # 检查是否需要工具调用
        # 这里简化处理，实际应该解析LLM的tool_calls
        return {}

    # 添加节点
    workflow.add_node("history_manager", history_manager)
    workflow.add_node("knowledge_retriever", knowledge_retriever)
    workflow.add_node("llm_generator", llm_generator)

    if tools:
        workflow.add_node("tool_executor", tool_executor)

    # 构建流程
    workflow.set_entry_point("history_manager")
    workflow.add_edge("history_manager", "knowledge_retriever")
    workflow.add_edge("knowledge_retriever", "llm_generator")

    if tools:
        # 添加工具调用路由
        workflow.add_conditional_edges(
            "llm_generator",
            lambda state: "tools" if state.get('needs_tools') else "end",
            {"tools": "tool_executor", "end": END}
        )
        workflow.add_edge("tool_executor", "history_manager")
    else:
        workflow.add_edge("llm_generator", END)

    return workflow.compile()
