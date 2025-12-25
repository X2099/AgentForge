# -*- coding: utf-8 -*-
"""
@File    : start_server.py
@Time    : 2025/12/9 14:47
@Desc    : AgentForge 启动脚本
"""
import uvicorn
import argparse
import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

def check_virtual_env():
    """检查是否在虚拟环境中运行"""
    in_venv = sys.prefix != sys.base_prefix

    # 检查是否在指定的虚拟环境中
    expected_venv_path = r"D:\Coding\ENVS\AgentForge"
    current_prefix = sys.prefix.lower().replace('\\', '/')
    expected_prefix = expected_venv_path.lower().replace('\\', '/')

    in_correct_venv = expected_prefix in current_prefix

    if not in_venv:
        print("⚠️  警告: 未检测到激活的虚拟环境")
        print(f"   建议激活虚拟环境: {expected_venv_path}\\Scripts\\activate.bat")
        print("-" * 50)
        return False
    elif not in_correct_venv:
        print("⚠️  警告: 当前不在项目的虚拟环境中")
        print(f"   当前环境: {sys.prefix}")
        print(f"   建议切换到: {expected_venv_path}")
        print("-" * 50)
        return False
    else:
        print("✅ 虚拟环境检查通过")
        return True

def check_dependencies():
    """检查关键依赖是否已安装"""
    required_packages = [
        'fastapi', 'uvicorn', 'streamlit',
        'langchain_core', 'langgraph', 'pydantic',
        'yaml', 'dotenv'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("❌ 缺少必要的依赖包:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("请运行: pip install -r requirements.txt")
        return False

    return True


def start_api_server(host="127.0.0.1", port=7861, reload=False):
    """启动API服务器"""
    print(f"启动 LangGraph-ChatChat API 服务器...")
    print(f"地址: http://{host}:{port}")
    print(f"API文档: http://{host}:{port}/docs")

    uvicorn.run(
        "src.api.api_compat:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug"
    )


def start_webui(host="127.0.0.1", port=8501):
    """启动Web界面"""
    import subprocess

    print(f"启动 LangGraph-ChatChat Web 界面...")
    print(f"地址: http://{host}:{port}")

    cmd = [
        "streamlit", "run",
        "src/webui/streamlit_app.py",
        "--server.address", host,
        "--server.port", str(port),
        "--theme.base", "light"
    ]

    subprocess.run(cmd)


def start_mcp_server(host="127.0.0.1", port=8000):
    """启动MCP工具服务器"""
    print(f"启动 MCP 工具服务器...")
    print(f"地址: http://{host}:{port}/mcp")

    try:
        # 导入MCP相关模块
        from src.tools.config.mcp_config import MCPToolConfig
        from src.tools.mcp_registry import MCPToolRegistry
        from src.tools.local_tools.calculator import CalculatorTool
        from src.tools.local_tools.web_search import WebSearchTool
        from src.tools.local_tools.knowledge_base import KnowledgeBaseTool
        from src.tools.transports import TransportType

        async def run_server():
            # 1. 加载配置
            config = MCPToolConfig()

            # 2. 创建工具注册中心
            registry = MCPToolRegistry(config.get_mcp_config())

            # 3. 注册内置工具
            enabled_tools = config.get_enabled_tools()

            # if "calculator" in enabled_tools:
            #     try:
            #         calculator = CalculatorTool()
            #         registry.register_builtin_tool(calculator)
            #         print("✅ 注册计算器工具")
            #     except Exception as e:
            #         print(f"⚠️  注册计算器工具失败: {e}")

            if "web_search" in enabled_tools:
                try:
                    web_search = WebSearchTool()
                    registry.register_builtin_tool(web_search)
                    print("✅ 注册网页搜索工具")
                except Exception as e:
                    print(f"⚠️  注册网页搜索工具失败: {e}")

            # if "knowledge_base_search" in enabled_tools:
            #     try:
            #         kb_search = KnowledgeBaseTool()
            #         registry.register_builtin_tool(kb_search)
            #         print("✅ 注册知识库搜索工具")
            #     except Exception as e:
            #         print(f"⚠️  注册知识库搜索工具失败: {e}")

            # 4. 获取服务器配置并更新端口
            server_config = config.get_server_config()
            transport_type = TransportType(server_config["transport_type"])
            transport_config = server_config["transport_config"]

            # 更新HTTP端口配置
            if transport_type == TransportType.HTTP:
                transport_config["port"] = port
                transport_config["host"] = host

            tool_names = registry.get_tool_names()
            print(f"注册工具: {', '.join(tool_names)}")
            print("按 Ctrl+C 停止服务器")

            # 5. 启动服务器
            await registry.start_server(transport_type, transport_config)

        # 运行异步服务器
        asyncio.run(run_server())

    except KeyboardInterrupt:
        print("\nMCP服务器已停止")
    except Exception as e:
        print(f"启动MCP服务器失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 AgentForge 启动脚本")
    print("=" * 50)

    # 检查环境
    venv_ok = check_virtual_env()
    deps_ok = check_dependencies()

    if not deps_ok:
        print("❌ 环境检查失败，请安装依赖后重试")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="AgentForge 启动脚本")
    parser.add_argument("--mode", choices=["api", "webui", "mcp", "all"], default="all",
                        help="启动模式: api, webui, mcp, all")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--api-port", type=int, default=7861, help="API端口")
    parser.add_argument("--webui-port", type=int, default=8501, help="Web界面端口")
    parser.add_argument("--mcp-port", type=int, default=8000, help="MCP服务器端口")
    parser.add_argument("--reload", action="store_true", help="热重载（仅API）")
    parser.add_argument("--skip-checks", action="store_true", help="跳过环境检查")

    args = parser.parse_args()

    if not args.skip_checks and not venv_ok:
        print("💡 提示: 虽然可以继续运行，但推荐使用虚拟环境")
        print("   创建虚拟环境: python -m venv venv")
        print("   激活环境: venv\\Scripts\\activate (Windows)")
        print("-" * 50)

    if args.mode in ["api", "all"]:
        print(f"🔧 启动API服务器 (端口: {args.api_port})...")
        # 启动API服务器
        start_api_server(args.host, args.api_port, args.reload)

    if args.mode in ["webui", "all"]:
        print(f"🌐 启动Web界面 (端口: {args.webui_port})...")
        # 启动Web界面（在单独的进程中）
        import threading

        webui_thread = threading.Thread(
            target=start_webui,
            args=(args.host, args.webui_port)
        )
        webui_thread.start()

        # 等待线程完成
        if args.mode == "webui":
            webui_thread.join()

    if args.mode in ["mcp", "all"]:
        print(f"🔨 启动MCP工具服务器 (端口: {args.mcp_port})...")
        # 启动MCP服务器
        start_mcp_server(args.host, args.mcp_port)
