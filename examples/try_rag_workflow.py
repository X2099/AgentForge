# -*- coding: utf-8 -*-
"""
@File    : try_rag_workflow.py
@Time    : 2025/12/25 13:58
@Desc    : 
"""
import sys
from pathlib import Path
import asyncio

from langgraph.checkpoint.memory import InMemorySaver

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.config import SystemConfig
from src.graphs import create_rag_graph
from src.knowledge.knowledge_manager import KnowledgeBaseManager


async def main():
    # 1) 构建模型（根据需要调整 provider/model 等配置）
    model = SystemConfig().create_client(
        model="deepseek-chat"
    )

    # 2) 获取知识库
    kb_manager = KnowledgeBaseManager()
    kb = kb_manager.get_knowledge_base("AncientChineseLiterature")

    # 3) 创建RAG工作流
    rag_graph = create_rag_graph(
        llm=model,
        knowledge_base=kb,
        checkpointer=InMemorySaver()
    )

    png_bytes = rag_graph.get_graph().draw_mermaid_png()
    with open("assets/langgraph_rag_workflow.png", "wb") as f:
        f.write(png_bytes)

    # 4) 组织初始状态并调用
    initial_state = {
        # "messages": [{"role": "user", "content": "纣王是谁？"}],
        "query": "纣王是谁？"
    }
    config = {"configurable": {"thread_id": "demo-thread"}}

    result = await rag_graph.ainvoke(initial_state, config)

    # 5) 打印结果
    messages = result.get("messages", [])

    for m in messages:
        m.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
