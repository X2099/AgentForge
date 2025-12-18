# -*- coding: utf-8 -*-
"""
@File    : orchestrator.py
@Time    : 2025/12/9 10:19
@Desc    : 
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .graphs.base_graph import BaseGraph
from .state.base_state import AgentState
from .nodes.base_node import Node

logger = logging.getLogger(__name__)


class GraphOrchestrator:
    """图编排器"""

    def __init__(self):
        self.graphs: Dict[str, BaseGraph] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.node_registry: Dict[str, Node] = {}

    def register_graph(self, graph: BaseGraph):
        """注册图"""
        self.graphs[graph.name] = graph
        logger.info(f"Registered graph: {graph.name}")

    def register_node(self, node: Node):
        """注册节点"""
        self.node_registry[node.name] = node
        logger.info(f"Registered node: {node.name}")

    def create_session(self, graph_name: str, initial_state: Dict[str, Any] = None) -> str:
        """创建会话"""
        if graph_name not in self.graphs:
            raise ValueError(f"Graph not found: {graph_name}")

        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 初始化状态
        state: AgentState = {
            "messages": [],
            "should_continue": True,
            "max_iterations": 10,
            "iteration_count": 0,
            "available_tools": [],
            "tool_calls": [],
            "tool_results": [],
            "retrieved_documents": [],
            "memory_context": "",
            "summary": "",
            "error": None,
            "retry_count": 0,
            **(initial_state or {})
        }

        # 编译图
        compiled_graph = self.graphs[graph_name].compile()

        self.active_sessions[session_id] = {
            "graph": compiled_graph,
            "state": state,
            "graph_name": graph_name,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        logger.info(f"Created session: {session_id}")
        return session_id

    async def execute_session(self, session_id: str,
                              user_input: str = None) -> Dict[str, Any]:
        """执行会话"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")

        session = self.active_sessions[session_id]
        graph = session["graph"]
        state = session["state"]

        # 添加用户输入
        if user_input:
            state["messages"].append({
                "type": "human",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })

        try:
            # 执行图
            logger.info(f"Executing session: {session_id}")
            start_time = datetime.now()

            # 更新状态
            state["iteration_count"] += 1
            state["last_updated"] = datetime.now().isoformat()

            # 执行图
            new_state = await graph.ainvoke(state)

            # 更新会话状态
            session["state"] = new_state
            session["last_updated"] = datetime.now().isoformat()

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Session {session_id} executed in {execution_time:.2f}s")

            return {
                "session_id": session_id,
                "state": new_state,
                "execution_time": execution_time,
                "success": True,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error executing session {session_id}: {str(e)}")

            # 更新错误状态
            state["error"] = str(e)
            state["retry_count"] = state.get("retry_count", 0) + 1

            return {
                "session_id": session_id,
                "state": state,
                "execution_time": 0,
                "success": False,
                "error": str(e)
            }

    def get_session_state(self, session_id: str) -> Optional[AgentState]:
        """获取会话状态"""
        session = self.active_sessions.get(session_id)
        return session["state"] if session else None

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None

        state = session["state"]
        return {
            "session_id": session_id,
            "graph_name": session["graph_name"],
            "created_at": session["created_at"],
            "last_updated": session["last_updated"],
            "message_count": len(state.get("messages", [])),
            "iteration_count": state.get("iteration_count", 0),
            "tool_call_count": len(state.get("tool_call_history", [])),
            "error": state.get("error"),
            "current_step": state.get("current_step")
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        sessions = []
        for session_id, session in self.active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "graph_name": session["graph_name"],
                "created_at": session["created_at"],
                "last_updated": session["last_updated"],
                "state_summary": {
                    "message_count": len(session["state"].get("messages", [])),
                    "iteration_count": session["state"].get("iteration_count", 0)
                }
            })
        return sessions

    def close_session(self, session_id: str):
        """关闭会话"""
        if session_id in self.active_sessions:
            logger.info(f"Closing session: {session_id}")
            del self.active_sessions[session_id]

    def reset_session(self, session_id: str, new_state: Dict[str, Any] = None):
        """重置会话"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            graph_name = session["graph_name"]

            # 关闭并重新创建
            self.close_session(session_id)
            return self.create_session(graph_name, new_state)

        return None
