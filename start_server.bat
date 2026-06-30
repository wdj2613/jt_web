@echo off
chcp 65001 > nul
setlocal

echo.
echo ================================================
echo    每日囧图 启动脚本
echo ================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请确保已安装Python并将其添加到PATH环境变量中。
    pause
    exit /b 1
)

REM 检查虚拟环境是否存在
if exist ".venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call .venv\Scripts\activate.bat
) else (
    echo 警告: 未找到虚拟环境，使用系统Python环境
)

REM 检查依赖是否已安装
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo 安装项目依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖安装失败
        pause
        exit /b 1
    )
)

echo.
echo 正在启动服务器...
echo 按 Ctrl+C 可以优雅地关闭服务器
echo.

REM 启动服务器
python app.py %*

echo.
echo 服务器已关闭
pause
