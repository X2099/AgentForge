# -*- coding: utf-8 -*-
"""
演示 create_conversation_workflow 的最小用例：
- 使用 SystemConfig 创建 LangChain ChatModel
- 绑定一个内置计算器工具（可选）
- 调用 workflow.ainvoke 运行一次对话
"""
import os
import sys
import asyncio
from langchain_core.messages import HumanMessage

# 允许从仓库根目录运行
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.config.system_config import SystemConfig
from src.tools.builtin_tools.calculator import calculator_tool
from src.graphs.react import create_react_agent


async def main():
    # 1) 构建模型（根据需要调整 provider/model 等配置）
    model = SystemConfig().create_client(
        model="deepseek-chat",  # 如需改用 openai/anthropic，请修改 provider
    )

    # # 2) 可选：准备工具列表
    # tools = [calculator_tool]
    #
    # # 3) 创建对话工作流（这里不接入知识库）
    # workflow = create_react_agent(
    #     llm=model,
    #     tools=tools,
    #     knowledge_base=None,
    #     system_prompt="你是一个乐于助人的助手，会在需要时调用可用的工具。"
    # )
    #
    # # 4) 组织初始状态并调用
    # initial_state = {
    #     "messages":[HumanMessage(content="帮我算一下 12.5 * 3.2。")],
    #     "query": "帮我算一下 12.5 * 3.2。",
    #     "thread_id": "demo-thread",
    #     "session_id": "demo-session",
    # }
    #
    # result = await workflow.ainvoke(initial_state)
    #
    # # 5) 打印结果
    # messages = result.get("messages", [])
    #
    # for m in messages:
    #     m.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
