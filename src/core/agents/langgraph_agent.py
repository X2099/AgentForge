# -*- coding: utf-8 -*-
"""
@File    : langgraph_agent.py
@Time    : 2025/12/9 12:27
@Desc    : 基于LangGraph标准的Agent构建器
"""
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from ..graphs.base_graph import AgentGraph
from ..state.base_state import AgentState
from ..nodes.tool_nodes import create_tool_executor_node
from ...llm.llm_client import LLMClient
from src.config.system_config import SystemConfig
from ...tools.tool_manager import ToolManager, get_tool_manager
from ...memory import MemoryManager, create_memory_retrieval_node, create_memory_truncation_node

import logging

logger = logging.getLogger(__name__)


class LangGraphAgentBuilder(AgentGraph):
    """
    LangGraph智能体构建器
    
    基于标准AgentGraph构建完整的Agent工作流
    """
    
    def __init__(
        self,
        agent_name: str,
        llm_client: Optional[LLMClient] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[BaseTool]] = None,
        tool_manager: Optional[ToolManager] = None,
        memory_manager: Optional[MemoryManager] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 15,
        enable_memory: bool = True
    ):
        """
        初始化智能体构建器
        
        Args:
            agent_name: 智能体名称
            llm_client: LLM客户端（如果提供，优先使用）
            llm_config: LLM配置（如果未提供llm_client）
            tools: 工具列表（直接提供）
            tool_manager: 工具管理器（如果不提供tools，则使用此管理器的工具）
            system_prompt: 系统提示词
            max_iterations: 最大迭代次数
        """
        super().__init__(name=agent_name, description=f"Agent: {agent_name}", max_iterations=max_iterations)
        
        self.agent_name = agent_name
        self.system_prompt = system_prompt or "你是一个有帮助的AI助手。"
        
        # 确定使用的工具
        if tools:
            self.tools = tools
        elif tool_manager:
            self.tools = tool_manager.get_tools_for_llm()
        else:
            # 使用全局工具管理器
            self.tools = get_tool_manager().get_tools_for_llm()
        
        self.tool_manager = tool_manager or get_tool_manager()
        
        # 初始化LLM客户端
        if llm_client:
            self.llm_client = llm_client
        else:
            config_manager = SystemConfig()
            self.llm_client = config_manager.create_client(**(llm_config or {}))
        
        # 记忆管理器
        self.memory_manager = memory_manager
        self.enable_memory = enable_memory and memory_manager is not None
        
        logger.info(f"Initialized agent builder: {agent_name} with {len(self.tools)} tools, memory={'enabled' if self.enable_memory else 'disabled'}")
    
    def build(self):
        """构建基础Agent图"""
        self.build_basic_agent()
    
    def build_basic_agent(self):
        """
        构建基础对话智能体
        
        流程（有记忆）: START -> memory_retrieval -> memory_truncation -> agent -> (tools) -> END
        流程（无记忆）: START -> agent -> (tools) -> END
        """
        # 添加agent节点（统一的LLM调用节点）- 异步节点
        # LangGraph会自动处理异步节点
        self.add_node("agent", self._agent_node)
        
        # 如果启用记忆，添加记忆节点
        if self.enable_memory and self.memory_manager:
            memory_retrieval = create_memory_retrieval_node(self.memory_manager, self.llm_client)
            memory_truncation = create_memory_truncation_node(self.memory_manager)
            
            self.add_node("memory_retrieval", memory_retrieval)
            self.add_node("memory_truncation", memory_truncation)
        
        # 如果有工具，添加工具执行节点
        if self.tools:
            tool_executor = create_tool_executor_node(self.tools)
            self.add_node("tools", tool_executor)
        
        # 构建流程
        self.set_entry_point(START)
        
        # 设置入口流程
        if self.enable_memory and self.memory_manager:
            # 有记忆：先检索记忆，再截断消息，然后执行agent
            self.add_edge(START, "memory_retrieval")
            self.add_edge("memory_retrieval", "memory_truncation")
            self.add_edge("memory_truncation", "agent")
        else:
            # 无记忆：直接执行agent
            self.add_edge(START, "agent")
        
        # Agent后的条件路由
        if self.tools:
            # 检查是否有工具调用
            self.add_conditional_edges(
                source="agent",
                condition=self._should_use_tools,
                path_map={
                    "tools": "tools",
                    "end": END
                }
            )
            # 工具执行后返回agent（继续循环）
            self.add_edge("tools", "agent")
        else:
            # 没有工具，检查是否继续
            self.add_conditional_edges(
                source="agent",
                condition=self.should_continue,
                path_map={
                    "continue": "agent",
                    "end": END
                }
            )
        
        logger.info(f"Built basic agent graph (memory={'enabled' if self.enable_memory else 'disabled'})")
    
    def _should_use_tools(self, state: AgentState) -> str:
        """判断是否需要使用工具"""
        messages = state.get("messages", [])
        if not messages:
            return "end"
        
        last_message = messages[-1]
        
        # 检查是否是AI消息并包含工具调用
        if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls"):
            tool_calls = last_message.tool_calls
            if tool_calls:
                return "tools"
        
        return "end"
    
    async def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Agent核心节点
        
        执行LLM调用和工具执行
        """
        # 准备消息
        messages = list(state.get("messages", []))
        
        # 添加系统提示词（如果第一条消息不是系统消息）
        formatted_messages = []
        if self.system_prompt:
            from langchain_core.messages import SystemMessage
            formatted_messages.append(SystemMessage(content=self.system_prompt))
        
        # 添加现有消息（已经是LangChain消息格式）
        formatted_messages.extend(messages)
        
        # 调用LLM（异步）
        try:
            response = await self.llm_client.achat(
                messages=formatted_messages,
                tools=self.tools if self.tools else None
            )
            
            # response现在是AIMessage类型
            ai_message = response
            
            # 获取工具调用
            tool_calls = []
            if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
                for tc in ai_message.tool_calls:
                    # tool_calls可能是字典或对象
                    if isinstance(tc, dict):
                        tool_calls.append({
                            "id": tc.get("id", ""),
                            "name": tc.get("name", ""),
                            "arguments": tc.get("args", {})
                        })
                    else:
                        # LangChain ToolCall对象
                        tool_calls.append({
                            "id": getattr(tc, "id", ""),
                            "name": getattr(tc, "name", ""),
                            "arguments": getattr(tc, "args", {}) if hasattr(tc, "args") else {}
                        })
            
            # 更新状态
            new_messages = [ai_message]
            
            # 如果有工具调用，执行工具
            if tool_calls:
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("arguments", {})
                    
                    # 查找对应的工具
                    tool = next((t for t in self.tools if t.name == tool_name), None)
                    if tool:
                        try:
                            import asyncio
                            # 执行工具（支持同步和异步）
                            if asyncio.iscoroutinefunction(tool.invoke):
                                result = await tool.ainvoke(tool_args)
                            else:
                                result = tool.invoke(tool_args)
                            
                            tool_message = ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call.get("id", "")
                            )
                            new_messages.append(tool_message)
                            tool_results.append({
                                "tool_name": tool_name,
                                "arguments": tool_args,
                                "result": result,
                                "success": True
                            })
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            tool_message = ToolMessage(
                                content=f"Error: {str(e)}",
                                tool_call_id=tool_call.get("id", "")
                            )
                            new_messages.append(tool_message)
                            tool_results.append({
                                "tool_name": tool_name,
                                "arguments": tool_args,
                                "error": str(e),
                                "success": False
                            })
                
                return {
                    "messages": new_messages,
                    "tool_calls": tool_calls,
                    "tool_results": tool_results,
                    "iteration_count": state.get("iteration_count", 0) + 1,
                    "should_continue": True
                }
            else:
                # 没有工具调用，结束
                return {
                    "messages": new_messages,
                    "iteration_count": state.get("iteration_count", 0) + 1,
                    "should_continue": False
                }
                
        except Exception as e:
            logger.error(f"Agent node error: {e}")
            error_message = AIMessage(content=f"抱歉，我遇到了一个错误：{str(e)}")
            return {
                "messages": [error_message],
                "error": str(e),
                "should_continue": False
            }
    
    def _format_messages_for_llm(self, messages: List[Any]) -> List[Dict[str, Any]]:
        """
        格式化消息为LLM客户端需要的格式
        
        Args:
            messages: 原始消息列表
            
        Returns:
            格式化后的消息列表
        """
        formatted = []
        
        # 添加系统提示
        formatted.append({"role": "system", "content": self.system_prompt})
        
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", msg.get("type", "user"))
                content = msg.get("content", "")
                formatted.append({"role": role, "content": content})
            elif isinstance(msg, BaseMessage):
                # LangChain消息类型
                if isinstance(msg, HumanMessage):
                    formatted.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    formatted.append({"role": "assistant", "content": msg.content})
                elif isinstance(msg, ToolMessage):
                    formatted.append({"role": "tool", "content": msg.content})
            else:
                # 其他类型，尝试转换
                formatted.append({"role": "user", "content": str(msg)})
        
        return formatted
    
    def compile(
        self,
        checkpointer: Optional[SqliteSaver] = None,
        **kwargs
    ) -> StateGraph:
        """
        编译Agent图
        
        Args:
            checkpointer: 检查点保存器
            **kwargs: 其他编译参数
            
        Returns:
            编译后的图
        """
        return super().compile(checkpointer=checkpointer, **kwargs)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "name": self.agent_name,
            "nodes": list(self.nodes.keys()),
            "tools": [t.name for t in self.tools] if self.tools else [],
            "max_iterations": self.max_iterations,
            "has_checkpointer": self.checkpointer is not None
        }
