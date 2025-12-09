# -*- coding: utf-8 -*-
"""
@File    : simple_agent_demo.py
@Time    : 2025/12/9 10:24
@Desc    : 
"""
# examples/simple_agent_demo.py
import asyncio
import math
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.orchestrator import GraphOrchestrator
from src.core.graphs.agent_graph import AgentGraph
from src.core.nodes.llm_nodes import LLMNode
from src.core.nodes.tool_nodes import ToolExecutorNode
from src.core.nodes.control_nodes import RouterNode
from src.llm.llm_client import LLMClient
from src.tools.base_tool import BaseTool


# 1. 定义简单的工具
class CalculatorTool(BaseTool):
    """计算器工具"""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '2 + 2' 或 'sqrt(16)'"
                    }
                },
                "required": ["expression"]
            }
        )

    def execute(self, expression: str) -> str:
        """执行计算"""
        try:
            # 简单的安全计算（实际应用中应该使用更安全的eval）
            allowed_names = {
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'pi': math.pi,
                'e': math.e
            }

            # 安全检查
            for char in expression:
                if char not in '0123456789+-*/.() sqrtcosten':
                    return f"无效字符: {char}"

            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"


# 2. 创建LLM客户端
class MockLLMClient:
    """模拟LLM客户端（用于测试）"""

    def __init__(self):
        self.model_name = "mock-llm"

    def generate(self, messages, tools=None):
        """模拟LLM响应"""
        last_message = messages[-1]["content"]

        # 简单的响应逻辑
        if "计算" in last_message or "算" in last_message:
            return {
                "choices": [{
                    "message": {
                        "content": "我需要使用计算器工具",
                        "tool_calls": [{
                            "id": "call_123",
                            "function": {
                                "name": "calculator",
                                "arguments": '{"expression": "2 + 2"}'
                            }
                        }]
                    }
                }]
            }
        else:
            return {
                "choices": [{
                    "message": {
                        "content": f"你好！你刚才说：{last_message}",
                        "tool_calls": []
                    }
                }]
            }


# 3. 构建自定义Agent图
class SimpleChatAgent(AgentGraph):
    """简单聊天Agent"""

    def __init__(self, llm_client, tools):
        super().__init__("simple_chat_agent", "简单的聊天对话Agent")
        self.llm_client = llm_client
        self.tools = tools

        # 构建图
        self.build()

    def build(self):
        """构建图结构"""
        # 创建节点
        llm_node = LLMNode("llm", self.llm_client)
        tool_node = ToolExecutorNode("tool_executor", self.tools)
        router_node = RouterNode("router")

        # 添加节点
        self.add_node("receive_input", self._receive_input)
        self.add_node("llm", llm_node)
        self.add_node("tool_executor", tool_node)
        self.add_node("router", router_node)
        self.add_node("format_response", self._format_response)

        # 构建流程
        self.add_edge("receive_input", "router")

        # 路由条件
        self.add_conditional_edge(
            "router",
            self._route_decision,
            {
                "to_llm": "llm",
                "to_tool": "tool_executor",
                "to_response": "format_response"
            }
        )

        self.add_edge("llm", "router")  # LLM处理后返回路由
        self.add_edge("tool_executor", "llm")  # 工具执行后返回LLM
        self.add_edge("format_response", END)  # 最终响应

    def _receive_input(self, state):
        """接收输入"""
        return {
            "current_step": "receive_input",
            "should_continue": True
        }

    def _route_decision(self, state):
        """路由决策"""
        if state.get("tool_calls"):
            return "to_tool"
        elif state.get("llm_response"):
            return "to_response"
        else:
            return "to_llm"

    def _format_response(self, state):
        """格式化响应"""
        return {
            "final_response": state.get("llm_response", {}).get("content", ""),
            "should_continue": False
        }


# 4. 运行示例
async def main():
    print("=== 简单Agent演示 ===\n")

    # 初始化编排器
    orchestrator = GraphOrchestrator()

    # 创建工具
    calculator = CalculatorTool()
    tools = {"calculator": calculator}

    # 创建LLM客户端
    llm_client = MockLLMClient()

    # 创建Agent图
    agent_graph = SimpleChatAgent(llm_client, tools)

    # 注册图
    orchestrator.register_graph(agent_graph)

    # 创建会话
    session_id = orchestrator.create_session("simple_chat_agent")
    print(f"创建会话: {session_id}")

    # 执行对话
    test_inputs = [
        "你好！",
        "请帮我计算2加2等于多少",
        "再计算一下圆的面积，半径是5"
    ]

    for user_input in test_inputs:
        print(f"\n用户: {user_input}")

        # 执行会话
        result = await orchestrator.execute_session(session_id, user_input)

        # 提取响应
        state = result["state"]
        if "final_response" in state:
            print(f"Agent: {state['final_response']}")
        elif "llm_response" in state:
            response = state.get("llm_response", {})
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"Agent: {content}")

        # 显示状态
        print(f"当前步骤: {state.get('current_step')}")
        print(f"迭代次数: {state.get('iteration_count')}")

    # 获取会话信息
    print("\n=== 会话信息 ===")
    session_info = orchestrator.get_session_info(session_id)
    print(json.dumps(session_info, indent=2, ensure_ascii=False))

    # 列出所有会话
    print("\n=== 所有会话 ===")
    sessions = orchestrator.list_sessions()
    for session in sessions:
        print(f"会话ID: {session['session_id']}")
        print(f"  图名称: {session['graph_name']}")
        print(f"  消息数量: {session['state_summary']['message_count']}")


if __name__ == "__main__":
    asyncio.run(main())
