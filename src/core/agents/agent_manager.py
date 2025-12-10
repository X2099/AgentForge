# -*- coding: utf-8 -*-
"""
@File    : agent_manager.py
@Time    : 2025/12/9 12:28
@Desc    : 
"""
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import json
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from .langgraph_agent import LangGraphAgentBuilder
from ..orchestrator import GraphOrchestrator
from ...memory import MemoryManager, MemoryConfig
from ...memory import MemoryManager, MemoryConfig


class AgentManager:
    """智能体管理器"""

    def __init__(self,
                 db_path: str = "./data/agents/agents.db",
                 memory_config: Optional[MemoryConfig] = None):
        """
        初始化智能体管理器

        Args:
            db_path: 数据库路径
            memory_config: 记忆配置
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.memory_config = memory_config or MemoryConfig()
        # 如果配置中没有checkpointer，使用默认的MemorySaver
        if self.memory_config.checkpointer is None:
            from langgraph.checkpoint.memory import MemorySaver
            self.memory_config.checkpointer = MemorySaver()
        self.memory_manager = MemoryManager(self.memory_config)

        # 活跃智能体
        self.active_agents: Dict[str, Dict[str, Any]] = {}

        # 智能体模板
        self.agent_templates: Dict[str, Dict[str, Any]] = {
            "basic_chat": {
                "type": "basic",
                "description": "基础对话智能体",
                "llm_config": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo"
                },
                "tools_config": {
                    "transport": "stdio"
                }
            },
            "research_assistant": {
                "type": "research",
                "description": "研究分析智能体",
                "llm_config": {
                    "provider": "openai",
                    "model": "gpt-4"
                },
                "tools_config": {
                    "transport": "stdio",
                    "enabled_tools": ["web_search", "knowledge_base_search"]
                }
            },
            "coding_assistant": {
                "type": "coding",
                "description": "代码开发智能体",
                "llm_config": {
                    "provider": "openai",
                    "model": "gpt-4"
                },
                "tools_config": {
                    "transport": "stdio",
                    "enabled_tools": ["code_executor", "file_reader"]
                }
            }
        }

        # 初始化数据库
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建智能体配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                config TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        # 创建会话记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT,
                user_id TEXT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                total_messages INTEGER DEFAULT 0,
                metadata TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)

        conn.commit()
        conn.close()

    def create_agent(self,
                     name: str,
                     agent_type: str = "basic_chat",
                     config_overrides: Optional[Dict[str, Any]] = None) -> str:
        """创建智能体"""
        # 获取模板
        template = self.agent_templates.get(agent_type, self.agent_templates["basic_chat"])

        # 合并配置
        config = template.copy()
        if config_overrides:
            config.update(config_overrides)

        # 生成智能体ID
        agent_id = f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}"

        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agents (agent_id, name, type, config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            agent_id,
            name,
            agent_type,
            json.dumps(config, ensure_ascii=False),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return agent_id

    def build_agent(self, agent_id: str) -> LangGraphAgentBuilder:
        """构建智能体"""
        # 从数据库加载配置
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name, type, config FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Agent not found: {agent_id}")

        name, agent_type, config_str = row
        config = json.loads(config_str)

        conn.close()

        # 创建智能体构建器
        builder = LangGraphAgentBuilder(
            agent_name=name,
            llm_config=config.get("llm_config", {}),
            tools_config=config.get("tools_config", {})
        )

        # 根据类型构建不同的智能体
        if agent_type == "research":
            builder.build_research_agent()
        elif agent_type == "coding":
            builder.build_coding_agent()
        else:
            builder.build_basic_agent()

        return builder

    async def start_agent_session(self,
                                  agent_id: str,
                                  user_id: Optional[str] = None,
                                  initial_state: Optional[Dict[str, Any]] = None,
                                  thread_id: Optional[str] = None) -> str:
        """启动智能体会话"""
        from langchain_core.messages import HumanMessage
        
        # 构建智能体
        builder = self.build_agent(agent_id)

        # 创建检查点保存器（用于状态持久化）
        import os
        os.makedirs("./data/agents", exist_ok=True)
        conn = sqlite3.connect(f"./data/agents/{agent_id}_sessions.db")
        checkpointer = SqliteSaver.from_conn(conn, table_name="checkpoints")

        # 编译智能体（使用checkpointer）
        compiled_agent = builder.compile(checkpointer=checkpointer)

        # 生成会话ID和thread_id
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        thread_id = thread_id or session_id

        # 初始化状态（使用LangGraph标准格式）
        state = {
            "thread_id": thread_id,
            "session_id": session_id,
            "user_id": user_id,
            "messages": [],
            "current_step": "start",
            "next_node": None,
            "agent_type": "default",
            "agent_role": "assistant",
            "available_tools": [],
            "should_continue": True,
            "max_iterations": builder.max_iterations,
            "iteration_count": 0,
            "retry_count": 0,
            **(initial_state or {})
        }

        # 保存会话记录
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agent_sessions (session_id, agent_id, user_id, started_at, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            agent_id,
            user_id,
            datetime.now().isoformat(),
            json.dumps({"initial_state": initial_state or {}}, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

        # 存储活跃智能体
        self.active_agents[session_id] = {
            "agent_id": agent_id,
            "compiled_agent": compiled_agent,
            "checkpointer": checkpointer,
            "state": state,
            "started_at": datetime.now().isoformat(),
            "message_count": 0
        }

        return session_id

    async def process_message(self,
                              session_id: str,
                              message: str,
                              config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理消息"""
        if session_id not in self.active_agents:
            raise ValueError(f"Session not found: {session_id}")

        from langchain_core.messages import HumanMessage
        
        agent_info = self.active_agents[session_id]
        compiled_agent = agent_info["compiled_agent"]
        thread_id = agent_info["state"].get("thread_id", session_id)

        # 准备输入（使用LangGraph标准格式）
        input_state = {
            "messages": [HumanMessage(content=message)]
        }

        # 执行智能体（使用checkpointer，通过config传递thread_id）
        config = config or {"configurable": {"thread_id": thread_id}}

        try:
            result = await compiled_agent.ainvoke(
                input_state,
                config=config
            )

            # 更新状态
            agent_info["state"] = result
            agent_info["message_count"] += 1

            # 提取响应（从messages中提取最后一条AI消息）
            response = ""
            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    response = last_msg.content
                elif isinstance(last_msg, dict):
                    response = last_msg.get("content", "")
            
            # 如果没有响应，尝试从其他字段提取
            if not response:
                response = result.get("final_response", "") or result.get("answer", "") or result.get("response", "")

            return {
                "session_id": session_id,
                "response": response,
                "state": result,
                "success": True,
                "has_tool_calls": bool(result.get("tool_calls")),
                "tool_results": result.get("tool_results", [])
            }

        except Exception as e:
            return {
                "session_id": session_id,
                "response": f"处理失败: {str(e)}",
                "error": str(e),
                "success": False
            }

    async def end_session(self, session_id: str):
        """结束会话"""
        if session_id in self.active_agents:
            # 更新会话记录
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE agent_sessions 
                SET ended_at = ?, total_messages = ?
                WHERE session_id = ?
            """, (
                datetime.now().isoformat(),
                self.active_agents[session_id]["message_count"],
                session_id
            ))

            conn.commit()
            conn.close()

            # 移除活跃智能体
            del self.active_agents[session_id]

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """获取智能体状态"""
        # 统计会话信息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(CASE WHEN ended_at IS NULL THEN 1 END) as active_sessions,
                SUM(total_messages) as total_messages
            FROM agent_sessions 
            WHERE agent_id = ?
        """, (agent_id,))

        stats = cursor.fetchone()

        cursor.execute("SELECT name, type, created_at FROM agents WHERE agent_id = ?", (agent_id,))
        agent_info = cursor.fetchone()

        conn.close()

        if not agent_info:
            return {"status": "not_found"}

        name, agent_type, created_at = agent_info

        return {
            "agent_id": agent_id,
            "name": name,
            "type": agent_type,
            "created_at": created_at,
            "total_sessions": stats[0] if stats else 0,
            "active_sessions": stats[1] if stats else 0,
            "total_messages": stats[2] if stats else 0,
            "is_active": agent_id in [a["agent_id"] for a in self.active_agents.values()]
        }

    def list_agents(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """列出智能体"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        sql = "SELECT agent_id, name, type, created_at, is_active FROM agents"
        if not include_inactive:
            sql += " WHERE is_active = 1"

        cursor.execute(sql)
        rows = cursor.fetchall()

        agents = []
        for row in rows:
            agent_id, name, agent_type, created_at, is_active = row

            agents.append({
                "agent_id": agent_id,
                "name": name,
                "type": agent_type,
                "created_at": created_at,
                "is_active": bool(is_active),
                "status": self.get_agent_status(agent_id)
            })

        conn.close()
        return agents
