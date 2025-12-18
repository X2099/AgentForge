# -*- coding: utf-8 -*-
"""
@File    : example_async_sqlite.py
@Time    : 2025/12/16 17:09
@Desc    : 
"""
import asyncio
from pathlib import Path

from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

BASE_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT_DB_PATH = BASE_DIR / "data" / "checkpoint.db"
print(CHECKPOINT_DB_PATH)


async def main():
    # 1) 构建 StateGraph
    builder = StateGraph(int)
    builder.add_node("add_one", lambda x: x + 1)
    builder.set_entry_point("add_one")
    builder.set_finish_point("add_one")

    # 2) 使用 AsyncSqliteSaver 持久化检查点
    # from_conn_string 会创建一个异步上下文管理器
    async with AsyncSqliteSaver.from_conn_string(f"{CHECKPOINT_DB_PATH}") as saver:
        # 编译图，把 saver 传入
        graph = builder.compile(checkpointer=saver)

        # 运行图（异步）—— 传入参数与线程相关配置
        # thread_id 用于区分不同会话或任务
        config = {"configurable": {"thread_id": "session-1"}}

        # 调用 ainvoke 获取结果
        result = await graph.ainvoke(1, config)
        print("First result:", result)

        # 再次运行，检查点会被保存，可以复用
        result_again = await graph.ainvoke(5, config)
        print("Second result:", result_again)

    # 连接关闭后进程可以正常 exit


# 执行主函数
asyncio.run(main())
