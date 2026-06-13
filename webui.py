"""ChatBI 股票助手 - Gradio WebUI 版本（参考 qwen-agent WebUI）"""
import os
import sys
import asyncio
from pathlib import Path
from typing import List, Optional

import gradio as gr
from nanobot import Nanobot
from nanobot.agent.hook import AgentHook, AgentHookContext
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.loader import load_config
from nanobot.nanobot import _make_provider

# 导入自定义工具
from app.tools.exc_sql import ExcSQLTool
from app.tools.arima_stock import ArimaStockTool
from app.tools.boll_detection import BollDetectionTool


class ChatBIWebUI:
    """ChatBI WebUI 界面类，参考 qwen-agent 的 WebUI 设计"""
    
    def __init__(self, bot: Nanobot, chatbot_config: Optional[dict] = None):
        """
        初始化聊天机器人界面
        
        Args:
            bot: NanoBot 实例
            chatbot_config: 聊天机器人配置
                支持配置: {'user.name': '', 'user.avatar': '', 'agent.avatar': '', 
                          'input.placeholder': '', 'prompt.suggestions': []}
        """
        self.bot = bot
        chatbot_config = chatbot_config or {}
        
        # 用户配置
        user_name = chatbot_config.get('user.name', '用户')
        self.user_config = {
            'name': user_name,
            'avatar': chatbot_config.get('user.avatar', ''),
        }
        
        # Agent 配置
        self.agent_config = {
            'name': 'ChatBI股票助手',
            'avatar': chatbot_config.get('agent.avatar', ''),
            'description': '智能股票查询助手，支持自然语言交互、数据查询、预测分析和技术指标检测',
        }
        
        # 输入配置
        self.input_placeholder = chatbot_config.get('input.placeholder', '请输入您的问题...')
        self.prompt_suggestions = chatbot_config.get('prompt.suggestions', [
            '贵州茅台最近一个月的股价走势',
            '对比五粮液和中芯国际2024年的涨跌幅',
            '预测贵州茅台未来7天的股价',
            '检测贵州茅台的布林带超买超卖点',
            '查询广发证券最近一周的交易数据',
        ])
        
        # 会话管理
        self.session_counter = 0
    
    def create_interface(self):
        """创建 Gradio 界面"""
        
        # 自定义 CSS
        custom_css = """
        .gradio-container {
            max-width: 1200px !important;
            margin: auto;
        }
        .chat-message {
            padding: 15px;
            border-radius: 10px;
            margin: 8px 0;
        }
        .user-message {
            background-color: #e3f2fd;
            text-align: right;
        }
        .bot-message {
            background-color: #f5f5f5;
            text-align: left;
        }
        """
        
        with gr.Blocks(
            title="ChatBI 股票助手",
            theme=gr.themes.Soft(
                primary_hue=gr.themes.utils.colors.blue,
                radius_size=gr.themes.utils.sizes.radius_none,
            ),
            css=custom_css
        ) as demo:
            # 标题和描述
            gr.Markdown("""
            # 📊 ChatBI 股票助手
            
            基于 NanoBot 框架的智能股票查询助手，支持自然语言交互、数据查询、预测分析和技术指标检测。
            
            ### ✨ 功能特性
            - **数据查询**: 查询股票历史价格走势和交易数据
            - **预测分析**: ARIMA 模型预测未来股价走势
            - **技术分析**: 布林带指标检测超买超卖点
            - **可视化**: 自动生成图表展示分析结果
            """)
            
            # 主要布局
            with gr.Row():
                with gr.Column(scale=4):
                    # 🔧 聊天历史记录（支持内嵌图片的稳定方式）
                    chatbot = gr.Chatbot(
                        label="对话历史",
                        height=500,
                        show_copy_button=True,
                        avatar_images=(
                            self.user_config.get('avatar') or None,
                            self.agent_config.get('avatar') or None
                        ),
                        bubble_full_width=False,  # 允许内容超出气泡宽度
                        render_markdown=True      # 渲染 Markdown，包括图片
                    )
                    
                    # 输入区域
                    with gr.Row():
                        question_input = gr.Textbox(
                            placeholder=self.input_placeholder,
                            label="您的问题",
                            lines=2,
                            scale=8,
                            container=False
                        )
                        submit_btn = gr.Button("🚀 发送", variant="primary", scale=1)
                    
                    # 操作按钮
                    with gr.Row():
                        clear_btn = gr.Button("🗑️ 清空历史", variant="secondary")
                        stop_btn = gr.Button("⏹️ 停止", variant="stop")
                
                with gr.Column(scale=1):
                    # 示例问题
                    if self.prompt_suggestions:
                        gr.Markdown("### 💡 推荐对话")
                        gr.Examples(
                            label="点击快速提问",
                            examples=[[suggestion] for suggestion in self.prompt_suggestions],
                            inputs=[question_input],
                        )
                    
                    gr.Markdown(f"""
                    ### 📝 使用提示
                    
                    **数据查询**
                    - 贵州茅台最近一个月的股价走势
                    - 对比五粮液和中芯国际2024年的涨跌幅
                    
                    **预测分析**
                    - 预测贵州茅台未来7天的股价
                    
                    **技术分析**
                    - 检测贵州茅台的布林带超买超卖点
                    
                    ### ℹ️ 关于助手
                    **名称**: {self.agent_config['name']}
                    
                    **描述**: {self.agent_config['description']}
                    
                    ### ⚙️ 技术栈
                    - **框架**: NanoBot + Gradio
                    - **LLM**: 通义千问 (DashScope)
                    - **数据库**: SQLite
                    - **可视化**: Matplotlib
                    """)
            
            # 事件绑定
            submit_event = submit_btn.click(
                fn=self.process_question_with_chart,
                inputs=[question_input, chatbot],
                outputs=[question_input, chatbot],  # 🔧 只返回聊天历史
                queue=True
            )
            
            question_input.submit(
                fn=self.process_question_with_chart,
                inputs=[question_input, chatbot],
                outputs=[question_input, chatbot],  # 🔧 只返回聊天历史
                queue=True
            )
            
            clear_btn.click(
                fn=self.clear_history,
                inputs=[],
                outputs=[chatbot],
                queue=False
            )
            
            # 页脚
            gr.Markdown("""
            ---
            **注意**: 本系统仅供参考，不构成投资建议。投资有风险，入市需谨慎。
            """)
        
        return demo
    
    async def process_question_with_chart(self, question: str, history: List):
        """
        处理用户问题并返回回答（图片内嵌在聊天消息中）
        
        Returns:
            Tuple of (question_input, chatbot_history)
        """
        if not question or not question.strip():
            return "", history
        
        # 增加会话计数
        self.session_counter += 1
        session_key = f"chatbi:webui:{self.session_counter}"
        
        # 添加用户问题到历史记录
        history = history + [[question, None]]
        
        try:
            print(f"\n{'='*70}")
            print(f"🔍 处理问题: {question}")
            print(f"{'='*70}")
            
            # 🔧 记录查询前的最新图表时间戳
            from pathlib import Path
            image_dir = Path("data/image_show")
            charts_before = set()
            if image_dir.exists():
                charts_before = {f.stat().st_mtime for f in image_dir.glob("*.png")}
            
            # 运行 bot
            result = await self.bot.run(question, session_key=session_key)
            
            # 获取回答
            answer = result.content
            
            print(f"\n📝 LLM 原始响应 (前500字符):")
            print(answer[:500])
            print(f"...")
            
            # 🔧 检测并提取图片路径（优先从LLM响应中提取）
            chart_path = self._extract_chart_path(answer)
            
            # 🔧 如果LLM没有保留图片标记，尝试查找最新生成的图表并附加
            if not chart_path:
                print(f"\n⚠️ LLM未保留图片标记，尝试查找最新生成的图表...")
                chart_path = self._find_latest_chart(charts_before)
                if chart_path:
                    print(f"✅ 找到最新生成的图表: {chart_path}")
                else:
                    print(f"❌ 未找到新生成的图表")
            else:
                print(f"\n🖼️ 从LLM响应中提取的图表路径: {chart_path}")
            
            # 🔧 关键改进：将图片转换为 base64 并嵌入 HTML img 标签
            if chart_path:
                answer = self._embed_image_as_base64(answer, chart_path)
            
            # 更新最后一条历史记录（包含内嵌图片的完整文本）
            history[-1] = [question, answer]
            
            # 返回：清空输入框、更新历史
            print(f"{'='*70}\n")
            return "", history
            
        except Exception as e:
            import traceback
            error_msg = f"❌ 发生错误: {str(e)}\n\n请检查：\n1. API Key 是否正确\n2. 网络连接是否正常\n3. 数据库文件是否存在"
            print(f"\n❌ 错误详情:")
            print(traceback.format_exc())
            history[-1] = [question, error_msg]
            return "", history
    
    def _extract_chart_path(self, response: str) -> str:
        """
        从响应中提取图表路径
        
        Args:
            response: LLM 的响应文本
            
        Returns:
            图片文件路径，如果没有则返回空字符串
        """
        import re
        from pathlib import Path
        
        print(f"\n🔎 正在搜索图片标记...")
        
        # 匹配 Markdown 图片语法: ![alt](path)
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = list(re.finditer(img_pattern, response))
        
        if matches:
            print(f"✅ 找到 {len(matches)} 个图片标记")
            for i, match in enumerate(matches):
                alt_text = match.group(1)
                img_path = match.group(2)
                print(f"   [{i+1}] Alt: {alt_text}")
                print(f"       路径: {img_path}")
                
                abs_path = Path(img_path).resolve()
                print(f"       绝对路径: {abs_path}")
                print(f"       文件存在: {abs_path.exists()}")
            
            # 返回第一个找到的图片路径
            img_path = matches[0].group(2)
            abs_path = Path(img_path).resolve()
            
            if abs_path.exists():
                return str(abs_path)
            else:
                print(f"⚠️ 图片文件不存在: {abs_path}")
                return ""
        else:
            print(f"❌ 未找到任何图片标记")
            # 尝试查找其他可能的图片引用格式
            if 'image_show' in response or '.png' in response:
                print(f"💡 响应中包含图片相关关键词，但未使用标准 Markdown 格式")
        
        return ""
    
    def _embed_image_as_base64(self, response: str, chart_path: str) -> str:
        """
        将图片转换为 base64 并嵌入为 HTML img 标签
        
        Args:
            response: LLM 的响应文本
            chart_path: 图片文件路径
            
        Returns:
            包含 base64 图片的 HTML 文本
        """
        import base64
        import re
        from pathlib import Path
        
        abs_path = Path(chart_path).resolve()
        
        if not abs_path.exists():
            print(f"⚠️ 图片文件不存在: {abs_path}")
            return response
        
        try:
            # 读取图片并转换为 base64
            with open(abs_path, 'rb') as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # 检测图片格式
            img_ext = abs_path.suffix.lower()
            mime_type = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }.get(img_ext, 'image/png')
            
            # 创建 HTML img 标签（使用 data URI）
            html_img = (
                f'\n\n<img src="data:{mime_type};base64,{img_base64}" '
                f'alt="股票走势图" '
                f'style="max-width: 100%; max-height: 400px; border-radius: 8px; '
                f'box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 10px 0;" />\n\n'
            )
            
            # 替换原有的 Markdown 图片标记为 HTML img 标签
            img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
            processed_response = re.sub(img_pattern, html_img, response)
            
            print(f"✅ 图片已转换为 base64 HTML 格式")
            print(f"📊 Base64 大小: {len(img_base64) / 1024:.2f} KB")
            
            return processed_response
            
        except Exception as e:
            print(f"⚠️ 图片转换失败: {e}")
            # 失败时保留原 Markdown 标记
            return response

    def _find_latest_chart(self, charts_before: set) -> str:
        """
        查找最新生成的图表文件
        
        Args:
            charts_before: 查询前已存在的图表时间戳集合
            
        Returns:
            最新图表的路径，如果没有则返回空字符串
        """
        from pathlib import Path
        
        image_dir = Path("data/image_show")
        if not image_dir.exists():
            return ""
        
        # 查找所有PNG文件
        chart_files = list(image_dir.glob("*.png"))
        
        if not chart_files:
            return ""
        
        # 过滤出新生成的文件（不在charts_before中的）
        new_charts = [
            f for f in chart_files 
            if f.stat().st_mtime not in charts_before
        ]
        
        if not new_charts:
            # 如果没有新文件，返回最新的文件
            latest_chart = max(chart_files, key=lambda f: f.stat().st_mtime)
            return str(latest_chart.resolve())
        
        # 返回最新生成的文件
        latest_new = max(new_charts, key=lambda f: f.stat().st_mtime)
        return str(latest_new.resolve())
    
    def clear_history(self):
        """清空聊天历史"""
        self.session_counter = 0
        return []
    
    def run(self, share: bool = False, server_name: str = None, server_port: int = None, **kwargs):
        """
        运行 WebUI
        
        Args:
            share: 是否生成公开分享链接
            server_name: 服务器名称，默认 "0.0.0.0"
            server_port: 服务器端口，默认 7860
            **kwargs: 其他传递给 launch 的参数
        """
        print("\n" + "="*70)
        print("ChatBI 股票助手 - WebUI")
        print("="*70)
        print("正在启动 Web 界面...")
        print(f"请在浏览器访问: http://localhost:{server_port or 7860}")
        if share:
            print("正在生成公开分享链接...")
        print("="*70 + "\n")
        
        demo = self.create_interface()
        demo.queue(default_concurrency_limit=10).launch(
            share=share,
            server_name=server_name or "0.0.0.0",
            server_port=server_port or 7860,
            inbrowser=True,
            **kwargs
        )


def build_bot() -> Nanobot:
    """构建 NanoBot 实例"""
    # 从环境变量获取 API Key
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        raise ValueError("未设置 DASHSCOPE_API_KEY 环境变量")

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


def main():
    """主函数"""
    # 检查 API Key
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("[错误] 未设置 DASHSCOPE_API_KEY 环境变量")
        print("请设置环境变量: export DASHSCOPE_API_KEY='your-api-key' (Linux/Mac)")
        print("或: $env:DASHSCOPE_API_KEY='your-api-key' (Windows PowerShell)")
        sys.exit(1)
    
    try:
        # 初始化 bot
        print("正在初始化 ChatBI 助手...")
        bot = build_bot()
        print("✓ ChatBI 助手初始化成功！")
        
        # 配置聊天界面
        chatbot_config = {
            'user.name': '用户',
            'input.placeholder': '请输入您的股票查询问题...',
            'prompt.suggestions': [
                '查询2024年全年贵州茅台的收盘价走势',
                '统计2024年1月广发证券的日均成交量',
                '对比2024年中芯国际和贵州茅台的涨跌幅',
                '查询2024年的贵州茅台的布林带超买超卖点',
            ]
        }
        
        # 创建并运行 WebUI
        webui = ChatBIWebUI(bot, chatbot_config=chatbot_config)
        webui.run()
        
    except Exception as e:
        print(f"✗ 启动失败: {str(e)}")
        print("请检查网络连接和 DASHSCOPE_API_KEY 配置")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
