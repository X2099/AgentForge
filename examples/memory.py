# -*- coding: utf-8 -*-
"""
@File    : memory.py
@Time    : 2025/12/25 9:23
@Desc    : 
"""
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

config = {"configurable": {"thread_id": "demo-thread"}}
thread_id = config["configurable"]["thread_id"]
namespace = ("memories", thread_id)
key = "summary"
store.put(namespace, key, {
    "messages_summary": "用户与客服机器人“小智”就“智能家居设备联动”问题进行了深入讨论。用户的核心诉求是解决客厅的灯光与窗帘无法根据日落时间自动同步的问题。在交流中，用户透露了自己是科技爱好者，偏好自动化场景，并曾自行尝试设置但未成功。"})
memory_summary = store.get(namespace, key)
print(memory_summary.value.get("messages_summary"))
