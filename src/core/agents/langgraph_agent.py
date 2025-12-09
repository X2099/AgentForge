# -*- coding: utf-8 -*-
"""
@File    : langgraph_agent.py
@Time    : 2025/12/9 12:27
@Desc    : 
"""
from typing import Dict, Any, List, Optional, Callable
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
import operator

from ..state.base_state import AgentState
from ..nodes.llm_nodes import LLMNode
from ..nodes.tool_nodes import ToolExecutorNode
from ..nodes.control_nodes import RouterNode
from ..nodes.mcp_tool_node import MCPToolExecutorNode
from ...memory.langgraph_nodes import (
    MemoryRetrievalNode,
    MemoryUpdateNode,
    ContextManagementNode
)
from ...tools.mcp_client import MCPClient
from ...llm.config.llm_config import LLMConfig


class LangGraphAgentBuilder:
    """LangGraph智能体构建器"""

    def __init__(self,
                 agent_name: str,
                 llm_config: Optional[Dict[str, Any]] = None,
                 tools_config: Optional[Dict[str, Any]] = None):
        """
        初始化智能体构建器

        Args:
            agent_name: 智能体名称
            llm_config: LLM配置
            tools_config: 工具配置
        """
        self.agent_name = agent_name
        self.llm_config = llm_config or {}
        self.tools_config = tools_config or {}

        # 创建状态图
        self.workflow = StateGraph(AgentState)

        # 存储节点引用
        self.nodes: Dict[str, Callable] = {}

        # 初始化组件
        self._initialize_components()

    def _initialize_components(self):
        """初始化组件"""
        # LLM配置
        llm_config_manager = LLMConfig()
        self.llm_client = llm_config_manager.create_client(
            **self.llm_config
        )

        # MCP客户端（用于工具调用）
        self.mcp_client = MCPClient(
            transport_type=self.tools_config.get("transport", "stdio"),
            transport_config=self.tools_config.get("transport_config", {})
        )

    def build_basic_agent(self) -> StateGraph:
        """构建基础对话智能体"""
        # 添加节点
        self._add_memory_retrieval_node()
        self._add_context_management_node()
        self._add_llm_node()
        self._add_tool_executor_node()
        self._add_response_formatter_node()
        self._add_memory_update_node()

        # 构建流程
        self.workflow.set_entry_point("memory_retrieval")
        self.workflow.add_edge("memory_retrieval", "context_management")
        self.workflow.add_edge("context_management", "llm")

        # LLM后的条件路由
        self.workflow.add_conditional_edges(
            "llm",
            self._route_after_llm,
            {
                "tools": "tool_executor",
                "response": "response_formatter"
            }
        )

        self.workflow.add_edge("tool_executor", "llm")
        self.workflow.add_edge("response_formatter", "memory_update")
        self.workflow.add_edge("memory_update", END)

        return self.workflow

    def build_research_agent(self) -> StateGraph:
        """构建研究分析智能体"""
        # 添加研究专用节点
        self._add_planning_node()
        self._add_web_search_node()
        self._add_analysis_node()
        self._add_report_generation_node()

        # 构建研究流程
        self.workflow.set_entry_point("planning")
        self.workflow.add_edge("planning", "web_search")
        self.workflow.add_edge("web_search", "analysis")
        self.workflow.add_edge("analysis", "report_generation")
        self.workflow.add_edge("report_generation", END)

        return self.workflow

    def build_coding_agent(self) -> StateGraph:
        """构建代码开发智能体"""
        # 添加编程专用节点
        self._add_requirements_analysis_node()
        self._add_architecture_design_node()
        self._add_code_generation_node()
        self._add_code_testing_node()
        self._add_documentation_node()

        # 构建编程流程
        self.workflow.set_entry_point("requirements_analysis")
        self.workflow.add_edge("requirements_analysis", "architecture_design")
        self.workflow.add_edge("architecture_design", "code_generation")

        # 代码生成后的条件路由
        self.workflow.add_conditional_edges(
            "code_generation",
            self._route_after_code_generation,
            {
                "needs_testing": "code_testing",
                "needs_docs": "documentation",
                "complete": END
            }
        )

        self.workflow.add_edge("code_testing", "code_generation")  # 测试失败返回修改
        self.workflow.add_edge("documentation", END)

        return self.workflow

    def _add_memory_retrieval_node(self):
        """添加记忆检索节点"""
        from ...memory.langgraph_memory import LangGraphMemoryStore
        from ...memory.langgraph_nodes import MemoryRetrievalNode

        memory_store = LangGraphMemoryStore()
        memory_node = MemoryRetrievalNode(memory_store)

        self.workflow.add_node("memory_retrieval", memory_node)
        self.nodes["memory_retrieval"] = memory_node

    def _add_context_management_node(self):
        """添加上下文管理节点"""
        from ...memory.short_term.context_memory import ContextMemoryManager
        from ...memory.langgraph_nodes import ContextManagementNode

        context_manager = ContextMemoryManager(llm_client=self.llm_client)
        context_node = ContextManagementNode(context_manager)

        self.workflow.add_node("context_management", context_node)
        self.nodes["context_management"] = context_node

    def _add_llm_node(self):
        """添加LLM节点"""
        from ..nodes.llm_nodes import LLMNode

        llm_node = LLMNode(
            name="llm",
            llm_client=self.llm_client,
            system_prompt="你是一个有帮助的AI助手。"
        )

        self.workflow.add_node("llm", llm_node)
        self.nodes["llm"] = llm_node

    def _add_tool_executor_node(self):
        """添加工具执行节点"""
        from ..nodes.mcp_tool_node import MCPToolExecutorNode

        tool_node = MCPToolExecutorNode(
            name="tool_executor",
            mcp_client=self.mcp_client
        )

        self.workflow.add_node("tool_executor", tool_node)
        self.nodes["tool_executor"] = tool_node

    def _add_response_formatter_node(self):
        """添加响应格式化节点"""

        def response_formatter(state: AgentState) -> Dict[str, Any]:
            """格式化最终响应"""
            response = {
                "final_response": state.get("llm_response", {}).get("content", ""),
                "tool_results": state.get("tool_results", []),
                "current_step": "response_formatter",
                "should_continue": False
            }
            return response

        self.workflow.add_node("response_formatter", response_formatter)
        self.nodes["response_formatter"] = response_formatter

    def _add_memory_update_node(self):
        """添加记忆更新节点"""
        from ...memory.langgraph_memory import LangGraphMemoryStore
        from ...memory.langgraph_nodes import MemoryUpdateNode

        memory_store = LangGraphMemoryStore()
        memory_update_node = MemoryUpdateNode(memory_store)

        # 包装为同步函数
        async def memory_update_wrapper(state: AgentState):
            return await memory_update_node(state)

        self.workflow.add_node("memory_update", memory_update_wrapper)
        self.nodes["memory_update"] = memory_update_wrapper

    def _add_planning_node(self):
        """添加规划节点"""

        def planning_node(state: AgentState) -> Dict[str, Any]:
            """任务规划"""
            query = state.get("messages", [{}])[-1].get("content", "")

            # 生成研究计划
            plan = {
                "research_topic": query,
                "steps": [
                    "1. 收集背景信息",
                    "2. 搜索相关资料",
                    "3. 分析信息",
                    "4. 撰写报告"
                ],
                "tools_needed": ["web_search", "knowledge_base_search"]
            }

            return {
                "plan": plan,
                "current_step": "planning"
            }

        self.workflow.add_node("planning", planning_node)
        self.nodes["planning"] = planning_node

    def _add_web_search_node(self):
        """添加网页搜索节点"""

        async def web_search_node(state: AgentState) -> Dict[str, Any]:
            """网页搜索"""
            plan = state.get("plan", {})
            topic = plan.get("research_topic", "")

            # 使用MCP工具进行搜索
            search_result = await self.mcp_client.call_tool_simple(
                "web_search",
                {"query": topic, "max_results": 5}
            )

            return {
                "search_results": search_result,
                "current_step": "web_search"
            }

        self.workflow.add_node("web_search", web_search_node)
        self.nodes["web_search"] = web_search_node

    def _add_analysis_node(self):
        """添加分析节点"""

        async def analysis_node(state: AgentState) -> Dict[str, Any]:
            """分析搜索结果"""
            search_results = state.get("search_results", "")

            # 使用LLM进行分析
            analysis_prompt = f"""
            请分析以下搜索结果，提取关键信息：

            {search_results}

            请总结：
            1. 主要发现
            2. 关键数据
            3. 重要观点
            4. 结论
            """

            response = self.llm_client.chat([
                {"role": "user", "content": analysis_prompt}
            ])

            return {
                "analysis": response.get_content(),
                "current_step": "analysis"
            }

        self.workflow.add_node("analysis", analysis_node)
        self.nodes["analysis"] = analysis_node

    def _add_report_generation_node(self):
        """添加报告生成节点"""

        async def report_generation_node(state: AgentState) -> Dict[str, Any]:
            """生成研究报告"""
            plan = state.get("plan", {})
            analysis = state.get("analysis", "")

            report_prompt = f"""
            基于以下分析生成研究报告：

            研究主题：{plan.get('research_topic', '')}

            分析结果：
            {analysis}

            请生成结构化的研究报告，包含：
            1. 引言
            2. 研究方法
            3. 研究发现
            4. 结论
            5. 参考文献
            """

            response = self.llm_client.chat([
                {"role": "user", "content": report_prompt}
            ])

            return {
                "report": response.get_content(),
                "current_step": "report_generation",
                "should_continue": False
            }

        self.workflow.add_node("report_generation", report_generation_node)
        self.nodes["report_generation"] = report_generation_node

    def _route_after_llm(self, state: AgentState) -> str:
        """LLM后的路由逻辑"""
        if state.get("tool_calls"):
            return "tools"
        return "response"

    def _route_after_code_generation(self, state: AgentState) -> str:
        """代码生成后的路由逻辑"""
        code_quality = state.get("code_quality", "good")

        if code_quality == "needs_testing":
            return "needs_testing"
        elif code_quality == "needs_docs":
            return "needs_docs"
        else:
            return "complete"

    def compile(self, checkpointer: Optional[SqliteSaver] = None) -> StateGraph:
        """编译智能体"""
        if checkpointer:
            return self.workflow.compile(checkpointer=checkpointer)
        return self.workflow.compile()

    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "name": self.agent_name,
            "nodes": list(self.nodes.keys()),
            "llm_config": self.llm_config,
            "tools_config": self.tools_config
        }
