# -*- coding: utf-8 -*-
"""
自定义工具使用示例：
- 定义一个简单的加法工具
- 直接将工具绑定到 LangChain 模型
- 运行一次对话，查看工具调用与结果
"""
import os
import sys
import asyncio
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.config.system_config import SystemConfig
from src.tools.builtin_tools.calculator import calculator_tool


async def main():
    # 1) 构建模型（需确保相关 API Key 已在环境变量中设置）
    model = SystemConfig().create_client(
        provider="deepseek",
        temperature=0,
        max_tokens=2000,
        timeout=15,
        max_retries=3
    )

    # 2) 绑定工具，得到具备 tool-calling 能力的模型
    model_with_tools = model.bind_tools([calculator_tool])

    # 3) 组织对话消息并直接调用模型
    messages = [
        SystemMessage(content="你是一个乐于助人的助手，擅长调用可用的工具。"),
        HumanMessage(content="请帮我计算 3 和 5 的和。"),
    ]

    response = await model_with_tools.ainvoke(messages)

    # 4) 输出结果
    print("Assistant reply:", getattr(response, "content", response))
    print("Tool calls:", getattr(response, "tool_calls", None))


if __name__ == "__main__":
    asyncio.run(main())
