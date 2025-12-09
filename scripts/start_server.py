# -*- coding: utf-8 -*-
"""
@File    : start_server.py
@Time    : 2025/12/9 14:47
@Desc    : 
"""
import uvicorn
import argparse
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))


def start_api_server(host="127.0.0.1", port=7861, reload=False):
    """启动API服务器"""
    print(f"启动 LangGraph-ChatChat API 服务器...")
    print(f"地址: http://{host}:{port}")
    print(f"API文档: http://{host}:{port}/docs")

    uvicorn.run(
        "src.api.langgraph_api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LangGraph-ChatChat 启动脚本")
    parser.add_argument("--mode", choices=["api", "webui", "all"], default="all",
                        help="启动模式: api, webui, all")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--api-port", type=int, default=7861, help="API端口")
    parser.add_argument("--webui-port", type=int, default=8501, help="Web界面端口")
    parser.add_argument("--reload", action="store_true", help="热重载（仅API）")

    args = parser.parse_args()

    if args.mode in ["api", "all"]:
        # 启动API服务器
        start_api_server(args.host, args.api_port, args.reload)

    if args.mode in ["webui", "all"]:
        # 启动Web界面（在单独的进程中）
        import threading

        webui_thread = threading.Thread(
            target=start_webui,
            args=(args.host, args.webui_port)
        )
        webui_thread.start()
