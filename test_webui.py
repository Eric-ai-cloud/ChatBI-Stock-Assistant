"""测试 WebUI 模块导入"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("正在测试模块导入...")
    
    # 测试 gradio
    import gradio as gr
    print("✓ Gradio 导入成功")
    
    # 测试 nanobot
    from nanobot import Nanobot
    print("✓ NanoBot 导入成功")
    
    # 测试自定义工具
    from app.tools.exc_sql import ExcSQLTool
    print("✓ ExcSQLTool 导入成功")
    
    from app.tools.arima_stock import ArimaStockTool
    print("✓ ArimaStockTool 导入成功")
    
    from app.tools.boll_detection import BollDetectionTool
    print("✓ BollDetectionTool 导入成功")
    
    # 测试 webui 模块
    from webui import ChatBIWebUI, build_bot
    print("✓ WebUI 模块导入成功")
    
    print("\n✅ 所有模块导入成功！可以启动 WebUI 了。")
    print("\n运行命令: python webui.py")
    print("\nWebUI 特性:")
    print("  • 参考 qwen-agent WebUI 设计")
    print("  • 类封装架构，更清晰")
    print("  • 支持配置化定制")
    print("  • 推荐对话示例")
    print("  • 美观的界面设计")
    
except ImportError as e:
    print(f"\n❌ 导入失败: {e}")
    print("\n请安装缺失的依赖:")
    print("pip install -r requirements.txt")
    sys.exit(1)
