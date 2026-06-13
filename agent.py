"""ChatBI 股票助手 - NanoBot 版本"""
import asyncio
import os
import sys
from pathlib import Path

from nanobot import Nanobot, RunResult
from nanobot.agent.hook import AgentHook, AgentHookContext
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.loader import load_config
from nanobot.nanobot import _make_provider

# 导入自定义工具
from app.tools.exc_sql import ExcSQLTool
from app.tools.arima_stock import ArimaStockTool
from app.tools.boll_detection import BollDetectionTool


class PrintHook(AgentHook):
    """打印钩子，用于显示工具调用信息"""
    
    async def before_execute_tools(self, ctx: AgentHookContext) -> None:
        """在工具执行前打印信息"""
        for tc in ctx.tool_calls:
            print(f"\n🔧 调用工具: {tc.name}")
            if tc.arguments:
                print(f"   参数: {tc.arguments}")

    async def on_stream(self, ctx: AgentHookContext, delta: str) -> None:
        """流式输出时打印内容"""
        print(delta, end='', flush=True)


def build_bot() -> Nanobot:
    """构建 NanoBot 实例"""
    # 从环境变量获取 API Key
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        print("[错误] 未设置 DASHSCOPE_API_KEY 环境变量")
        print("请设置环境变量: export DASHSCOPE_API_KEY='your-api-key' (Linux/Mac)")
        print("或: $env:DASHSCOPE_API_KEY='your-api-key' (Windows PowerShell)")
        sys.exit(1)

    # 获取配置文件路径
    config_path = Path(__file__).parent / "config.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    # 加载配置
    config = load_config(config_path)
    config.providers.dashscope.api_key = dashscope_key
    config.agents.defaults.workspace = str(Path(__file__).parent)

    # 创建 Provider
    provider = _make_provider(config)
    defaults = config.agents.defaults

    # 创建工作区目录
    workspace = Path(__file__).parent

    # 创建 Agent Loop
    loop = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=workspace,
        model=defaults.model,
        max_iterations=defaults.max_tool_iterations,
        context_window_tokens=defaults.context_window_tokens,
        max_tool_result_chars=getattr(defaults, 'max_tool_result_chars', 10000),
        web_config=config.tools.web,
        exec_config=config.tools.exec,
        restrict_to_workspace=False,
        timezone=defaults.timezone,
    )

    # 注册自定义工具
    loop.tools.register(ExcSQLTool())
    loop.tools.register(ArimaStockTool())
    loop.tools.register(BollDetectionTool())

    return Nanobot(loop)


async def main():
    """主函数"""
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 命令行模式
        question = " ".join(sys.argv[1:])
        print(f"\n{'='*70}")
        print(f"ChatBI 股票助手 (NanoBot 版本)")
        print(f"{'='*70}")
        print(f"问题: {question}\n")

        bot = build_bot()
        result = await bot.run(question, session_key="chatbi:run", hooks=[PrintHook()])

        print(f"\n{'='*70}")
        print(f"回答:\n{result.content}")
        print(f"{'='*70}\n")
    else:
        # 交互模式
        await interactive_mode()


async def interactive_mode():
    """交互式对话模式"""
    print(f"\n{'='*70}")
    print(f"ChatBI 股票助手 (NanoBot 版本) - 交互模式")
    print(f"{'='*70}")
    print(f"欢迎使用 ChatBI 股票助手！")
    print(f"您可以输入以下类型的问题：")
    print(f"  • 查询股价走势：贵州茅台最近一个月的股价走势")
    print(f"  • 对比分析：对比五粮液和中芯国际2024年的涨跌幅")
    print(f"  • 预测分析：预测贵州茅台未来7天的股价")
    print(f"  • 技术分析：检测贵州茅台的布林带超买超卖点")
    print(f"\n输入 'quit' 或 'exit' 退出，输入 'help' 查看帮助")
    print(f"{'='*70}\n")

    bot = build_bot()
    session_counter = 0

    while True:
        try:
            # 获取用户输入
            question = input("\n📊 您想查询什么？> ").strip()
            
            if not question:
                continue
            
            # 检查退出命令
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n感谢使用 ChatBI 股票助手，再见！👋\n")
                break
            
            # 显示帮助信息
            if question.lower() in ['help', 'h', '?']:
                print_help()
                continue
            
            # 执行查询
            session_counter += 1
            session_key = f"chatbi:session:{session_counter}"
            
            print(f"\n⏳ 正在处理您的查询...")
            result = await bot.run(question, session_key=session_key, hooks=[PrintHook()])
            
            print(f"\n{'─'*70}")
            print(f"💡 回答:")
            print(f"{result.content}")
            print(f"{'─'*70}")
            
        except KeyboardInterrupt:
            print("\n\n检测到中断信号，退出程序...")
            break
        except EOFError:
            print("\n\n输入结束，退出程序...")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")
            print("请重试或输入 'help' 查看帮助")


def print_help():
    """打印帮助信息"""
    help_text = """
╔═══════════════════════════════════════════════════════════╗
║                   ChatBI 使用帮助                         ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  📈 数据查询功能：                                        ║
║  • 查询某股票近期走势                                      ║
║    例：贵州茅台最近一个月的股价走势                        ║
║                                                           ║
║  • 对比多只股票表现                                       ║
║    例：对比五粮液和中芯国际2024年的涨跌幅                  ║
║                                                           ║
║  🔮 预测分析功能：                                        ║
║  • ARIMA 股价预测                                         ║
║    例：预测贵州茅台未来7天的股价                           ║
║                                                           ║
║  📊 技术分析功能：                                        ║
║  • 布林带异常点检测                                       ║
║    例：检测贵州茅台的布林带超买超卖点                      ║
║                                                           ║
║  💡 提示：                                                ║
║  • 可以使用自然语言描述您的需求                            ║
║  • 系统会自动生成 SQL 并执行查询                          ║
║  • 结果会以文字和图表形式展示                             ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(help_text)


if __name__ == "__main__":
    """程序入口点"""
    asyncio.run(main())
