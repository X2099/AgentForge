# -*- coding: utf-8 -*-
"""
@File    : checkpointer_demo.py
@Time    : 2025/12/18 10:00
@Desc    : 
"""
import asyncio
from pathlib import Path
from pprint import pprint

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

BASE_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT_DB = (BASE_DIR / "data" / "checkpoint.db").as_posix()


async def main():
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
        # 从checkpointer加载会话历史
        session_id = "6d5c8092-4cf3-4c1e-b2ae-79fb37ff6e9a"
        config = {"configurable": {"thread_id": session_id}}
        checkpoint = await checkpointer.aget(config)
        # print(checkpoint)
        channel_values = checkpoint["channel_values"]
        # pprint(channel_values)
        # pprint(channel_values['messages'])
        messages = channel_values["answers"]
        response_messages = []
        for i, msg in enumerate(messages[-50:]):  # 限制数量
            # print(msg.keys())
            message = msg.get("message", {})
            sources = msg.get("sources", [])
            print(message.type)
            # if hasattr(message, "type") and hasattr(message, "content"):
            #     response_messages.append({
            #         "message_id": f"msg_{i}",
            #         "session_id": session_id,
            #         "role": msg.type,
            #         "content": msg.content,
            #         "model_name": getattr(msg, "name", None),
            #         "created_at": getattr(msg, "timestamp", None),
            #         "sources": sources,
            #         "metadata": {}
            #     })


if __name__ == '__main__':
    asyncio.run(main())
