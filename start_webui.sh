#!/bin/bash

echo "========================================"
echo "  ChatBI 股票助手 - WebUI 启动器"
echo "========================================"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python3"
    exit 1
fi

# 检查 API Key
if [ -z "" ]; then
    echo "[警告] 未设置 DASHSCOPE_API_KEY 环境变量"
    echo ""
    read -p "请输入您的 DashScope API Key: " API_KEY
    
    if [ -z "" ]; then
        echo "[错误] API Key 不能为空"
        exit 1
    fi
    
    export DASHSCOPE_API_KEY=
    echo ""
fi

echo "[信息] 正在启动 WebUI..."
echo "[信息] 请在浏览器访问: http://localhost:7860"
echo ""

python3 webui.py
