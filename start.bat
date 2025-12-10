@echo off
REM AgentForge 启动脚本 (Windows)
echo 🚀 启动 AgentForge
echo.

REM 设置虚拟环境路径
set VENV_PATH=D:\Coding\ENVS\AgentForge

REM 检查虚拟环境是否存在
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo ❌ 未找到虚拟环境: %VENV_PATH%
    echo 💡 请确保虚拟环境已正确创建
    pause
    exit /b 1
)

REM 激活虚拟环境
echo 🔧 激活虚拟环境...
call "%VENV_PATH%\Scripts\activate.bat"

REM 检查Python是否来自虚拟环境
python -c "import sys; print('Python路径:', sys.executable)" | findstr "%VENV_PATH%" >nul
if errorlevel 1 (
    echo ❌ 虚拟环境激活失败
    pause
    exit /b 1
)

REM 检查依赖是否已安装
echo 🔍 检查依赖...
python -c "import fastapi, streamlit, langchain_core" >nul 2>&1
if errorlevel 1 (
    echo ❌ 依赖未安装，请运行: pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ 环境检查通过
echo.

REM 启动服务
echo 🔧 启动服务...
python scripts/start_server.py --mode all

pause
