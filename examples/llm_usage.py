# -*- coding: utf-8 -*-
"""
@File    : llm_usage.py
@Time    : 2025/12/9 10:49
@Desc    : 
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.llm.config.llm_config import LLMConfig
from src.llm.prompts.base_prompt import BasePrompt


async def main():
    print("=== LLM集成使用示例 ===\n")

    # 1. 创建配置管理器
    config = LLMConfig()

    # 2. 创建OpenAI客户端
    print("1. 创建OpenAI客户端...")
    openai_client = config.create_client(
        provider="openai",
        model="deepseek-chat"
    )

    # 3. 测试聊天
    print("\n2. 测试聊天功能...")
    messages = [
        {"role": "system", "content": "你是一个有帮助的AI助手。"},
        {"role": "user", "content": "你好，请简单介绍一下自己。"}
    ]

    response = openai_client.chat(messages)
    print(f"响应: {response.get_content()}")

    # 4. 测试流式聊天
    print("\n3. 测试流式聊天...")
    print("流式响应:", end=" ")

    stream_response = openai_client.chat(
        messages=[{"role": "user", "content": "请用一句话介绍Python。"}],
        stream=True
    )

    for chunk in stream_response:
        if chunk.choices and chunk.choices[0]["delta"]:
            content = chunk.choices[0]["delta"].get("content", "")
            print(content, end="", flush=True)
    print()

    # 5. 测试异步聊天
    print("\n4. 测试异步聊天...")

    async def test_async():
        response = await openai_client.achat(
            messages=[{"role": "user", "content": "异步测试：1+1等于多少？"}]
        )
        print(f"异步响应: {response.get_content()}")

    await test_async()

    # 6. 测试本地模型（如果可用）
    try:
        print("\n5. 测试本地模型...")
        local_client = config.create_client(
            provider="local",
            model="Qwen/Qwen2.5-7B-Instruct"
        )

        local_response = local_client.chat(
            messages=[{"role": "user", "content": "你好！"}]
        )
        print(f"本地模型响应: {local_response.get_content()[:100]}...")
    except Exception as e:
        print(f"本地模型测试失败（可能未安装）: {str(e)}")

    # 7. 查看统计信息
    print("\n6. 查看统计信息...")
    stats = openai_client.get_stats()
    print(f"总调用次数: {stats['total_calls']}")
    print(f"成功调用: {stats['successful_calls']}")
    print(f"失败调用: {stats['failed_calls']}")
    print(f"成功率: {stats['success_rate']:.2%}")
    print(f"总Token数: {stats['total_tokens']}")
    print(f"总成本: ${stats['total_cost']:.4f}")

    # 8. 测试Prompt模板
    print("\n7. 测试Prompt模板...")
    prompt = BasePrompt(
        name="translation_prompt",
        template="请将以下{language_from}文本翻译成{language_to}：\n\n{text}",
        description="翻译Prompt",
        variables={
            "language_from": {"type": "str", "required": True},
            "language_to": {"type": "str", "required": True},
            "text": {"type": "str", "required": True}
        },
        examples=[
            {
                "input": "language_from=英文, language_to=中文, text=Hello World",
                "output": "你好，世界"
            }
        ]
    )

    # 渲染Prompt
    rendered = prompt.render(
        language_from="英文",
        language_to="中文",
        text="Artificial Intelligence is changing the world."
    )
    print(f"渲染的Prompt:\n{rendered}")

    # 使用Prompt调用LLM
    response = openai_client.chat(
        messages=[{"role": "user", "content": rendered}]
    )
    print(f"翻译结果: {response.get_content()}")

    # 9. 测试工具调用
    print("\n8. 测试工具调用...")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "城市名称"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]

    tool_messages = [
        {"role": "user", "content": "今天北京的天气怎么样？"}
    ]

    try:
        tool_response = openai_client.chat(
            messages=tool_messages,
            tools=tools,
            tool_choice="auto"
        )

        tool_calls = tool_response.get_tool_calls()
        if tool_calls:
            print(f"工具调用请求: {tool_calls}")
            # 这里可以执行工具调用逻辑
    except Exception as e:
        print(f"工具调用测试失败（可能模型不支持）: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
