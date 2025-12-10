# -*- coding: utf-8 -*-
"""
@File    : mcp_server_example.py
@Time    : 2025/12/9 12:01
@Desc    :
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.tools.config.mcp_config import MCPToolConfig
from src.tools.mcp_registry import MCPToolRegistry
from src.tools.builtin_tools.calculator import CalculatorTool
from src.tools.builtin_tools.web_search import WebSearchTool
from src.tools.transports import TransportType


async def main():
    print("=== MCP工具服务器示例 ===\n")

    # 1. 加载配置
    config = MCPToolConfig()

    # 2. 创建工具注册中心
    registry = MCPToolRegistry(config.get_mcp_config())

    # 3. 注册内置工具
    calculator = CalculatorTool()
    registry.register_builtin_tool(calculator)

    web_search = WebSearchTool()
    registry.register_builtin_tool(web_search)

    # 4. 自定义工具示例
    def custom_greeting(arguments: dict) -> str:
        name = arguments.get("name", "World")
        return f"Hello, {name}!"

    registry.register_tool(
        name="greet",
        description="生成问候语",
        handler=custom_greeting,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "要问候的名字",
                    "default": "World"
                }
            },
            "required": []
        }
    )

    # 5. 获取服务器配置
    server_config = config.get_server_config()
    transport_type = TransportType(server_config["transport_type"])
    transport_config = server_config["transport_config"]

    print(f"启动MCP服务器...")
    print(f"传输类型: {transport_type.value}")
    print(f"注册工具: {', '.join(registry.get_tool_names())}")

    # 6. 启动服务器
    if transport_type == TransportType.STDIO:
        print("\n以STDIO模式运行，等待客户端连接...")
        await registry.start_server(transport_type, transport_config)
    elif transport_type == TransportType.HTTP:
        print(f"\n以HTTP模式运行，地址: http://localhost:{transport_config.get('port', 8000)}/mcp")
        print("按 Ctrl+C 停止服务器")
        await registry.start_server(transport_type, transport_config)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器已停止")
