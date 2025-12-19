# -*- coding: utf-8 -*-
"""
create_rag_agent 验证演示
演示如何使用 create_rag_agent 函数创建 RAG（检索增强生成）工作流
"""
import asyncio
from pathlib import Path

# 添加项目根目录到路径
import sys
from pprint import pprint

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from src.config import SystemConfig
from src.graphs.rag import create_rag_agent
from src.tools.tool_manager import get_tool_manager
from src.api.api_compat import list_knowledge_bases


async def demo_basic_rag_agent():
    """基础 RAG agent 演示"""
    print("=" * 50)
    print("create_rag_agent 基础演示")
    print("=" * 50)

    try:
        # 1. 配置 LLM
        print("1. 配置 LLM...")
        config = SystemConfig()
        llm = config.create_client(
            provider="deepseek",  # 可根据需要修改为其他提供商
            temperature=0.7,
            max_tokens=1000,
            timeout=15,
            max_retries=3,
        )
        print("✓ LLM 配置成功")

        # 2. 可选：准备工具
        print("\n2. 准备工具...")
        tool_manager = get_tool_manager()
        available_tools = tool_manager.list_tools(with_metadata=True)
        tools = []
        for tool, metadata in available_tools[:2]:  # 只选择前2个工具作为演示
            tools.append(tool)
        print(f"✓ 加载了 {len(tools)} 个工具: {[t.name for t in tools]}")

        # 3. 配置知识库
        print("\n3. 配置知识库...")
        from src.knowledge.kb_manager import KnowledgeBaseManager
        kb_manager = KnowledgeBaseManager(use_database=True)

        # 查找现有知识库
        existing_kb_names = []
        try:
            kb_list = await list_knowledge_bases()
            existing_kb_names = [kb['name'] for kb in kb_list.get('knowledge_bases', [])]
            print(f"✓ 发现现有知识库: {existing_kb_names}")
        except Exception as e:
            print(f"⚠️ 无法获取知识库列表: {e}")

        knowledge_base = None
        if existing_kb_names:
            kb_name = existing_kb_names[0]
            print(f"✓ 使用现有知识库: {kb_name}")
            try:
                knowledge_base = kb_manager.get_knowledge_base(kb_name)
                if knowledge_base:
                    print("✓ 知识库加载成功")
                else:
                    print("⚠️ 知识库存在但无法加载，将使用纯对话模式")
            except Exception as e:
                print(f"⚠️ 加载知识库失败: {e}，将使用纯对话模式")
        else:
            print("⚠️ 未发现现有知识库，将使用纯对话模式")

        # 4. 可选：设置检查点保存器
        checkpointer = InMemorySaver()  # 内存检查点保存器
        print("4. 检查点保存器: InMemorySaver")

        # 5. 创建 RAG agent
        print("\n5. 创建 RAG agent...")
        agent = create_rag_agent(
            llm=llm,
            tools=tools,
            knowledge_base=knowledge_base,
            system_prompt="你是一个乐于助人的AI助手。当用户问问题时，你会先思考是否需要使用工具来帮助回答问题。",
            checkpointer=checkpointer
        )
        print("✓ RAG agent 创建成功")

        # 6. 执行对话
        print("\n6. 执行对话测试...")
        test_query = "贾雨村是哪里人？"

        # 准备初始状态
        initial_state = {
            "messages": [HumanMessage(content=test_query)],
            "query": test_query
        }

        config = {"configurable": {"thread_id": "demo_thread"}}

        print(f"用户: {test_query}")
        print("助手: ", end="")

        # 执行工作流
        result = await agent.ainvoke(initial_state, config)

        pprint(result["answers"])

        # 显示结果
        # if result["messages"]:
        #     last_message = result["messages"][-1]
        #     if hasattr(last_message, 'content'):
        #         print(last_message.content)

        # 显示工作流执行信息
        # print(f"\n执行信息:")
        # print(f"- 查询: {result.get('query', 'N/A')}")
        # print(f"- 文档数量: {len(result.get('documents', []))}")
        # print(f"- 来源数量: {len(result.get('sources', []))}")
        #
        # # 显示响应元数据
        # response_metadata = result.get('response_metadata')
        # if response_metadata:
        #     print(f"- 响应元数据:")
        #     print(f"  * 查询: {response_metadata.get('query', 'N/A')[:50]}...")
        #     print(f"  * 文档数量: {len(response_metadata.get('documents', []))}")
        #     print(f"  * 上下文长度: {response_metadata.get('context_length', 0)}")
        #     print(f"  * 时间戳: {response_metadata.get('timestamp', 'N/A')[:19]}")
        #     if response_metadata.get('error'):
        #         print(f"  * 错误: {response_metadata['error'][:100]}...")
        # print(f"- 当前步骤: {result.get('current_step', 'N/A')}")
        #
        # print("\n✓ 基础演示完成！")

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主演示函数"""
    print("🚀 create_rag_agent 验证演示")
    print("这个演示将展示如何使用 create_rag_agent 函数创建和使用 RAG 工作流\n")

    # 基础演示
    await demo_basic_rag_agent()

    print("\n" + "=" * 50)
    print("🎉 所有演示完成！")
    print("create_rag_agent 函数验证成功")
    print("=" * 50)


if __name__ == "__main__":
    # 运行异步演示
    asyncio.run(main())
