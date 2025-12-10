#!/usr/bin/env python3
"""
环境设置脚本 - AgentForge
自动创建虚拟环境并安装依赖
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示状态"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败")
        print(f"   错误信息: {e.stderr}")
        return False

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print("   需要 Python 3.8+")
        return False

def check_existing_venv():
    """检查现有的虚拟环境"""
    venv_paths = [
        r"D:\Coding\ENVS\AgentForge",  # 项目专用虚拟环境
        "venv",  # 本地虚拟环境
    ]

    for venv_path in venv_paths:
        if os.path.exists(venv_path):
            scripts_path = os.path.join(venv_path, "Scripts" if os.name == 'nt' else "bin")
            python_exe = os.path.join(scripts_path, "python.exe" if os.name == 'nt' else "python")

            if os.path.exists(python_exe):
                print(f"✅ 发现虚拟环境: {venv_path}")
                return venv_path

    return None

def create_venv():
    """创建虚拟环境"""
    existing_venv = check_existing_venv()
    if existing_venv:
        print(f"⚠️  虚拟环境已存在: {existing_venv}，跳过创建")
        return existing_venv

    venv_path = "venv"
    if run_command(f"python -m venv {venv_path}", "创建虚拟环境"):
        return venv_path
    return None

def activate_venv(venv_path=None):
    """激活虚拟环境"""
    if venv_path is None:
        venv_path = check_existing_venv() or "venv"

    if os.name == 'nt':  # Windows
        scripts_dir = "Scripts"
        activate_script = f"{venv_path}\\{scripts_dir}\\activate.bat"
        python_exe = f"{venv_path}\\{scripts_dir}\\python.exe"
        pip_exe = f"{venv_path}\\{scripts_dir}\\pip.exe"
    else:  # Unix/Linux/macOS
        scripts_dir = "bin"
        activate_script = f"source {venv_path}/{scripts_dir}/activate"
        python_exe = f"{venv_path}/{scripts_dir}/python"
        pip_exe = f"{venv_path}/{scripts_dir}/pip"

    print(f"🔧 激活虚拟环境: {venv_path}")
    print(f"   在新终端中运行: {activate_script}")
    print(f"   或直接使用: {python_exe} 和 {pip_exe}")

    return python_exe, pip_exe

def upgrade_pip(pip_exe):
    """升级pip"""
    return run_command(f'"{pip_exe}" install --upgrade pip', "升级pip")

def install_requirements(pip_exe):
    """安装项目依赖"""
    if not os.path.exists("requirements.txt"):
        print("❌ 未找到 requirements.txt 文件")
        return False

    return run_command(f'"{pip_exe}" install -r requirements.txt', "安装项目依赖")

def create_env_file():
    """创建环境变量文件"""
    if os.path.exists(".env"):
        print("⚠️  .env 文件已存在，跳过创建")
        return True

    env_template = """# AgentForge 环境配置
# 复制此文件为 .env 并填写相应的配置

# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic API 配置 (可选)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 本地模型配置 (可选)
LOCAL_MODEL_PATH=/path/to/your/local/model

# 向量数据库配置
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIR=./data/chroma_db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/agentforge.log

# 服务器配置
API_HOST=127.0.0.1
API_PORT=7861
WEBUI_HOST=127.0.0.1
WEBUI_PORT=8501
"""

    try:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_template)
        print("✅ 创建 .env 配置文件")
        return True
    except Exception as e:
        print(f"❌ 创建 .env 文件失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 AgentForge 环境设置脚本")
    print("=" * 50)

    # 检查Python版本
    if not check_python_version():
        return False

    # 检查或创建虚拟环境
    venv_path = check_existing_venv()
    if venv_path:
        print(f"✅ 使用现有虚拟环境: {venv_path}")
    else:
        print("🔧 创建新的虚拟环境...")
        venv_path = create_venv()
        if not venv_path:
            return False

    # 获取虚拟环境可执行文件路径
    python_exe, pip_exe = activate_venv(venv_path)

    # 检查是否需要安装依赖
    try:
        import subprocess
        result = subprocess.run([python_exe, "-c", "import fastapi, streamlit, langchain_core"],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ 依赖已安装，跳过安装步骤")
            deps_installed = True
        else:
            deps_installed = False
    except:
        deps_installed = False

    if not deps_installed:
        # 升级pip
        if not upgrade_pip(pip_exe):
            print("⚠️  pip升级失败，继续安装依赖...")

        # 安装依赖
        if not install_requirements(pip_exe):
            return False

    # 创建环境配置文件
    create_env_file()

    print("\n" + "=" * 50)
    print("🎉 环境设置完成！")
    print("\n📋 下一步:")

    if venv_path == r"D:\Coding\ENVS\AgentForge":
        if os.name == 'nt':
            print("   1. 激活环境: D:\\Coding\\ENVS\\AgentForge\\Scripts\\activate.bat")
        else:
            print("   1. 激活环境: source D:/Coding/ENVS/AgentForge/Scripts/activate")
    else:
        if os.name == 'nt':
            print(f"   1. 激活环境: {venv_path}\\Scripts\\activate.bat")
        else:
            print(f"   1. 激活环境: source {venv_path}/bin/activate")

    print("   2. 配置环境变量: 编辑 .env 文件")
    print("   3. 启动服务: python scripts/start_server.py --mode all")
    print("   4. 或直接运行: start.bat (Windows)")
    print("\n🌐 访问地址:")
    print("   - Web界面: http://localhost:8501")
    print("   - API文档: http://localhost:7861/docs")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
