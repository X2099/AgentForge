# -*- coding: utf-8 -*-
"""
测试checkpointer功能
验证LangGraph的checkpointer能够正确保存和恢复对话状态
"""
import asyncio
import tempfile
import os
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.core.state.base_state import GraphState
from src.graphs.react import ConversationState


class MockLLM:
    """模拟LLM，用于测试"""

    async def ainvoke(self, messages):
        """模拟响应"""
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            content = f"这是对 '{last_message.content}' 的模拟回复"
            return AIMessage(content=content)


async def test_checkpointer_basic():
    """测试checkpointer的基本功能"""
    print("=== 测试checkpointer基本功能 ===")

    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
            # 测试保存状态
            session_id = "test_session_001"
            config = {"configurable": {"thread_id": session_id}}

            # 初始状态
            initial_state = ConversationState(
                messages=[HumanMessage(content="你好")],
                query="你好"
            )

            # 保存初始状态
            checkpoint_id = await checkpointer.aput(config, initial_state, {})
            print(f"✓ 保存初始状态，checkpoint_id: {checkpoint_id}")

            # 添加更多消息并更新状态
            updated_state = ConversationState(
                messages=[
                    HumanMessage(content="你好"),
                    AIMessage(content="你好！我是AI助手，有什么可以帮助你的吗？")
                ],
                query="你好",
                response="你好！我是AI助手，有什么可以帮助你的吗？"
            )

            checkpoint_id2 = await checkpointer.aput(config, updated_state, {})
            print(f"✓ 更新状态，checkpoint_id: {checkpoint_id2}")

            # 加载状态
            loaded_checkpoint = await checkpointer.aget(config)
            if loaded_checkpoint:
                loaded_state, metadata = loaded_checkpoint
                print("✓ 成功加载状态")
                print(f"  - 消息数量: {len(loaded_state.get('messages', []))}")
                print(f"  - 最后一条消息: {loaded_state['messages'][-1].content[:50]}...")
            else:
                print("✗ 加载状态失败")

    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)
            print("✓ 清理临时数据库文件")


async def test_multiple_sessions():
    """测试多个会话的管理"""
    print("\n=== 测试多个会话管理 ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
            sessions = ["session_001", "session_002", "session_003"]

            # 为每个会话保存状态
            for i, session_id in enumerate(sessions):
                config = {"configurable": {"thread_id": session_id}}

                state = ConversationState(
                    messages=[
                        HumanMessage(content=f"这是会话{session_id}的第一条消息"),
                        AIMessage(content=f"这是对会话{session_id}的回复")
                    ],
                    query=f"这是会话{session_id}的第一条消息",
                    response=f"这是对会话{session_id}的回复"
                )

                await checkpointer.aput(config, state, {})
                print(f"✓ 保存会话 {session_id}")

            # 验证每个会话都能正确加载
            for session_id in sessions:
                config = {"configurable": {"thread_id": session_id}}
                checkpoint = await checkpointer.aget(config)

                if checkpoint:
                    state, metadata = checkpoint
                    first_message = state["messages"][0].content
                    expected_content = f"这是会话{session_id}的第一条消息"

                    if first_message == expected_content:
                        print(f"✓ 会话 {session_id} 验证通过")
                    else:
                        print(f"✗ 会话 {session_id} 内容不匹配")
                        print(f"  期望: {expected_content}")
                        print(f"  实际: {first_message}")
                else:
                    print(f"✗ 会话 {session_id} 加载失败")

            # 验证会话隔离
            config1 = {"configurable": {"thread_id": "session_001"}}
            config2 = {"configurable": {"thread_id": "session_002"}}

            checkpoint1 = await checkpointer.aget(config1)
            checkpoint2 = await checkpointer.aget(config2)

            if checkpoint1 and checkpoint2:
                state1, _ = checkpoint1
                state2, _ = checkpoint2

                msg1 = state1["messages"][0].content
                msg2 = state2["messages"][0].content

                if msg1 != msg2 and "session_001" in msg1 and "session_002" in msg2:
                    print("✓ 会话隔离验证通过")
                else:
                    print("✗ 会话隔离验证失败")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
            print("✓ 清理临时数据库文件")


async def test_message_persistence():
    """测试消息持久化"""
    print("\n=== 测试消息持久化 ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
            session_id = "persistence_test"
            config = {"configurable": {"thread_id": session_id}}

            # 创建多轮对话
            conversation = [
                ("用户", "你好"),
                ("助手", "你好！很高兴见到你"),
                ("用户", "今天天气怎么样？"),
                ("助手", "我无法获取实时天气信息，但我可以帮你查找相关信息"),
                ("用户", "谢谢你的帮助"),
                ("助手", "不客气！如果还有其他问题，随时问我")
            ]

            # 逐步构建对话状态
            messages = []
            for i, (role, content) in enumerate(conversation):
                if role == "用户":
                    messages.append(HumanMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))

                # 保存当前状态
                state = ConversationState(
                    messages=messages.copy(),
                    query=content if role == "用户" else "",
                    response=content if role == "助手" else ""
                )

                await checkpointer.aput(config, state, {})

            # 验证最终状态
            final_checkpoint = await checkpointer.aget(config)
            if final_checkpoint:
                final_state, metadata = final_checkpoint
                final_messages = final_state.get("messages", [])

                if len(final_messages) == len(conversation):
                    print(f"✓ 消息持久化成功，共 {len(final_messages)} 条消息")

                    # 验证消息内容
                    all_correct = True
                    for i, (expected_role, expected_content) in enumerate(conversation):
                        actual_message = final_messages[i]
                        actual_content = actual_message.content

                        if actual_content != expected_content:
                            print(f"✗ 消息 {i+1} 内容不匹配")
                            print(f"  期望: {expected_content}")
                            print(f"  实际: {actual_content}")
                            all_correct = False

                    if all_correct:
                        print("✓ 所有消息内容验证通过")
                else:
                    print(f"✗ 消息数量不匹配，期望 {len(conversation)}，实际 {len(final_messages)}")
            else:
                print("✗ 无法加载最终状态")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
            print("✓ 清理临时数据库文件")


async def test_checkpoint_history():
    """测试检查点历史"""
    print("\n=== 测试检查点历史 ===")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
            session_id = "history_test"
            config = {"configurable": {"thread_id": session_id}}

            checkpoints = []

            # 创建多个检查点
            for i in range(3):
                state = ConversationState(
                    messages=[HumanMessage(content=f"消息 {i+1}")],
                    query=f"消息 {i+1}"
                )

                checkpoint_id = await checkpointer.aput(config, state, {})
                checkpoints.append(checkpoint_id)
                print(f"✓ 创建检查点 {i+1}: {checkpoint_id}")

            # 验证最新的检查点
            latest = await checkpointer.aget(config)
            if latest:
                latest_state, metadata = latest
                latest_message = latest_state["messages"][0].content

                if latest_message == "消息 3":
                    print("✓ 最新检查点验证通过")
                else:
                    print(f"✗ 最新检查点内容错误: {latest_message}")
            else:
                print("✗ 无法获取最新检查点")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
            print("✓ 清理临时数据库文件")


async def run_all_tests():
    """运行所有测试"""
    print("开始checkpointer功能测试\n")

    try:
        await test_checkpointer_basic()
        await test_multiple_sessions()
        await test_message_persistence()
        await test_checkpoint_history()

        print("\n🎉 所有测试完成！")

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(run_all_tests())
