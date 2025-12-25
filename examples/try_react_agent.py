# -*- coding: utf-8 -*-
import os
import sys
import asyncio
from pathlib import Path
import sqlite3

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.sqlite import SqliteStore, AsyncSqliteStore

# 允许从仓库根目录运行
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.config.system_config import SystemConfig
from src.tools.local_tools.calculator import calculator_tool
from src.graphs import create_react_graph

BASE_DIR = Path(__file__).resolve().parent.parent
STORE_DB = (BASE_DIR / "data" / "store.db").as_posix()


def create_mock_conversation() -> list[dict]:
    """返回可直接用于LangGraph测试的模拟对话消息列表"""

    return [
        # 用户首次询问
        {
            "role": "user",
            "content": "你好，我想设置一个智能家居自动化场景，让客厅灯光在日落时自动打开。"
        },
        # AI首次回复
        {
            "role": "assistant",
            "content": "好的，我可以帮您设置这个自动化场景。首先，请告诉我您使用的是哪个智能家居平台？比如小米米家、苹果HomeKit、还是Google Home？"
        },
        # 用户提供更多信息
        {
            "role": "user",
            "content": "我使用的是小米米家，客厅有两盏Yeelight吸顶灯，还有一个小米窗帘电机。"
        },
        # AI指导具体操作
        {
            "role": "assistant",
            "content": "明白了。在米家APP中，您可以这样设置：\n1. 进入「自动化」页面，点击右上角「+」\n2. 触发条件选择「日落时」\n3. 执行动作选择「打开客厅主灯」和「打开客厅辅灯」\n4. 保存场景为「日落开灯」\n您需要我详细说明每一步吗？"
        },
        # 用户遇到问题
        {
            "role": "user",
            "content": "我找不到「日落时」这个触发条件，只有具体时间选择。另外，窗帘怎么一起联动？"
        },
        # AI解决问题
        {
            "role": "assistant",
            "content": "如果找不到「日落时」，可能是因为您的米家APP版本或地区限制。替代方案：\n1. 使用「定时」功能，设置具体时间（需手动调整）\n2. 安装「米家极客版」APP，支持更复杂的自动化\n\n关于窗帘联动：在同一个自动化中，增加执行动作「打开窗帘」或设置到指定位置。"
        },
        # 用户进一步询问
        {
            "role": "user",
            "content": "米家极客版在哪里下载？苹果App Store有吗？另外，我想设置一个「影院模式」，能一键关闭所有灯光、拉上窗帘、打开投影仪，这个复杂吗？"
        },
        # AI深入指导
        {
            "role": "assistant",
            "content": "1. 米家极客版目前主要在安卓平台，iOS可能需要通过TestFlight测试\n\n2. 「影院模式」设置步骤：\n   a. 创建新自动化，触发条件选择「手动执行」\n   b. 添加动作：「关所有灯」、「窗帘关闭」、「打开投影仪」\n   c. 保存后可以在控制中心添加快捷按钮\n   d. 还可以设置「当投影仪打开时，自动执行影院模式」的联动\n\n需要我帮您写具体的配置步骤吗？"
        },
        # 用户确认需求
        {
            "role": "user",
            "content": "太好了！请给我「影院模式」的详细配置步骤。另外，窗帘关闭后如果我想留一条缝透气，能设置成只关闭90%吗？"
        },
        # AI提供最终方案
        {
            "role": "assistant",
            "content": "当然可以！以下是详细配置：\n\n**影院模式配置：**\n1. 打开米家APP → 自动化 → 创建手动自动化\n2. 添加动作：\n   - 客厅主灯：关闭\n   - 客厅辅灯：关闭\n   - 窗帘：关闭到90%位置\n   - 投影仪：打开（如果支持智能插座）\n3. 保存为「影院模式」\n\n**高级设置（极客版）：**\n您还可以设置延迟：先关灯，3秒后关窗帘，再2秒后开投影仪，营造剧院感。\n\n需要我继续解释其他智能场景吗？"
        }
    ]


async def main():
    with SqliteStore.from_conn_string(STORE_DB) as store:
        # 1) 构建模型（根据需要调整 provider/model 等配置）
        model = SystemConfig().create_client(
            model="deepseek-chat",  # 如需改用 openai/anthropic，请修改 provider
        )

        # 2) 可选：准备工具列表
        tools = [calculator_tool]

        # 3) 创建对话工作流（这里不接入知识库）
        # store = InMemorySaver()
        # store = SqliteStore(conn=sqlite3.connect(STORE_DB))
        # print(store)
        # return
        react_agent = create_react_graph(
            llm=model,
            tools=tools,
            system_prompt="你是一个乐于助人的助手，会在需要时调用可用的工具。",
            checkpointer=InMemorySaver(),
            store=store
        )

        png_bytes = react_agent.get_graph().draw_mermaid_png()
        with open("assets/langgraph_react_agent.png", "wb") as f:
            f.write(png_bytes)

        # 4) 组织初始状态并调用
        initial_state = {
            "messages": create_mock_conversation() + [{
                "role": "user",
                "content": "我们都聊了些什么？"
            }]
        }
        # initial_state = {
        #     "messages": [{
        #         "role": "user",
        #         "content": "你好，我是Kevin！"
        #     }]
        # }
        config = {"configurable": {"thread_id": "demo-thread"}}

        result = await react_agent.ainvoke(initial_state, config)

        # 5) 打印结果
        messages = result.get("messages", [])

        for m in messages:
            m.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
