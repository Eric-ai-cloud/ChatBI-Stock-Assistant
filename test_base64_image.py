"""测试 base64 图片嵌入"""
import base64
from pathlib import Path

# 测试图片路径
img_path = Path("data/image_show/stock_chart_1777262703060.png")

if img_path.exists():
    print(f"✅ 图片文件存在: {img_path}")
    print(f"📊 文件大小: {img_path.stat().st_size} bytes")
    
    # 读取并转换为 base64
    with open(img_path, 'rb') as f:
        img_data = f.read()
        img_base64 = base64.b64encode(img_data).decode('utf-8')
    
    print(f"✅ Base64 编码成功")
    print(f"📏 Base64 长度: {len(img_base64)} 字符")
    print(f"📏 Base64 大小: {len(img_base64) / 1024:.2f} KB")
    
    # 创建 data URI
    data_uri = f"data:image/png;base64,{img_base64[:50]}..."
    print(f"\nData URI 预览:")
    print(data_uri)
    
    # 创建 HTML
    html = f'''
    <div style="margin: 15px 0; text-align: center;">
        <img src="data:image/png;base64,{img_base64}" 
             alt="股票走势图"
             style="max-width: 100%; max-height: 500px; border-radius: 8px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);"/>
        <p style="font-size: 12px; color: #666; margin-top: 5px;">股票走势图</p>
    </div>
    '''
    
    print(f"\n✅ HTML 生成成功")
    print(f"📏 HTML 总长度: {len(html)} 字符")
    
    # 保存为 HTML 文件用于测试
    test_html = Path("test_image.html")
    with open(test_html, 'w', encoding='utf-8') as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>图片测试</title>
        </head>
        <body>
            <h1>Gradio Chatbot 图片显示测试</h1>
            {html}
        </body>
        </html>
        """)
    
    print(f"\n✅ 测试 HTML 已保存: {test_html.resolve()}")
    print(f"💡 请在浏览器中打开此文件验证图片是否正常显示")
    
else:
    print(f"❌ 图片文件不存在: {img_path}")
    print("请先运行一次查询以生成图表")
