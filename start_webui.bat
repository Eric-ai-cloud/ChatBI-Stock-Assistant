@echo off
chcp 65001 >nul
echo ========================================
echo   ChatBI 股票助手 - WebUI 启动器
echo ========================================
echo.

REM 检查 Python 是否安装
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 检查 API Key
if not defined DASHSCOPE_API_KEY (
    echo [警告] 未设置 DASHSCOPE_API_KEY 环境变量
    echo.
    set /p API_KEY="请输入您的 DashScope API Key: "
    if not defined API_KEY (
        echo [错误] API Key 不能为空
        pause
        exit /b 1
    )
    set DASHSCOPE_API_KEY=%API_KEY%
    echo.
)

echo [信息] 正在启动 WebUI...
echo [信息] 请在浏览器访问: http://localhost:7860
echo.

python webui.py

pause
