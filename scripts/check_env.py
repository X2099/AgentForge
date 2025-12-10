#!/usr/bin/env python3
"""
环境检查脚本 - AgentForge
检查虚拟环境状态和依赖安装情况
"""
import sys
import os
from pathlib import Path

def check_virtual_env():
    """检查虚拟环境状态"""
    print("🔍 检查虚拟环境...")

    in_venv = sys.prefix != sys.base_prefix
    expected_venv = r"D:\Coding\ENVS\AgentForge"

    print(f"   系统Python路径: {sys.base_prefix}")
    print(f"   当前Python路径: {sys.prefix}")
    print(f"   是否在虚拟环境中: {'是' if in_venv else '否'}")

    if in_venv:
        current_prefix = sys.prefix.lower().replace('\\', '/')
        expected_prefix = expected_venv.lower().replace('\\', '/')
        if expected_prefix in current_prefix:
            print("   虚拟环境状态: ✅ 使用项目专用虚拟环境")
            return True
        else:
            print("   虚拟环境状态: ⚠️ 使用其他虚拟环境")
            print(f"   建议切换到: {expected_venv}")
            return False
    else:
        print("   虚拟环境状态: ❌ 未激活虚拟环境")
        print(f"   建议激活: {expected_venv}\\Scripts\\activate.bat")
        return False

def check_dependencies():
    """检查关键依赖"""
    print("\n🔍 检查依赖安装...")

    required_packages = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'Uvicorn'),
        ('streamlit', 'Streamlit'),
        ('langchain_core', 'LangChain Core'),
        ('pydantic', 'Pydantic'),
    ]

    missing_packages = []
    for package, display_name in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {display_name}")
        except ImportError:
            print(f"   ❌ {display_name}")
            missing_packages.append(package)

    if missing_packages:
        print("\n⚠️  缺少依赖包，请运行:")
        print("   pip install -r requirements.txt")
        return False

    print("\n✅ 所有依赖包已安装")
    return True

def check_paths():
    """检查重要路径"""
    print("\n🔍 检查路径配置...")

    paths_to_check = [
        ('项目根目录', Path(__file__).parent.parent),
        ('源代码目录', Path(__file__).parent.parent / 'src'),
        ('脚本目录', Path(__file__).parent),
        ('配置文件', Path(__file__).parent.parent / 'requirements.txt'),
    ]

    for name, path in paths_to_check:
        if path.exists():
            print(f"   ✅ {name}: {path}")
        else:
            print(f"   ❌ {name}: {path} (不存在)")

def main():
    """主函数"""
    print("🚀 AgentForge 环境检查脚本")
    print("=" * 50)

    # 检查虚拟环境
    venv_ok = check_virtual_env()

    # 检查依赖
    deps_ok = check_dependencies()

    # 检查路径
    check_paths()

    print("\n" + "=" * 50)

    if venv_ok and deps_ok:
        print("🎉 环境检查通过！可以正常启动服务")
        print("\n启动命令:")
        print("   python scripts/start_server.py --mode all")
        return True
    else:
        print("❌ 环境检查失败，请根据上述提示修复问题")
        return False

if __name__ == "__main__":
    success = main()
    input("\n按任意键退出...")
    sys.exit(0 if success else 1)
