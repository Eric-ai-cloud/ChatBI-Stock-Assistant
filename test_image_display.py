"""测试图片显示修复"""
import re
from pathlib import Path

# 模拟 LLM 响应
test_response = """
**数据概览**: 共 22 行, 6 列

### 📈 整体趋势
- 起始日期：2026-03-25
- 最新日期：2026-04-24

![股票走势图](data/image_show/stock_chart_1777262703060.png)

以上就是分析结果。
"""

def _separate_images_from_text(response: str):
    """从响应中分离图片和文本"""
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = list(re.finditer(img_pattern, response))
    
    if not matches:
        return response
    
    parts = []
    last_end = 0
    
    for match in matches:
        if match.start() > last_end:
            text_before = response[last_end:match.start()].strip()
            if text_before:
                parts.append({"type": "text", "text": text_before})
        
        alt_text = match.group(1)
        img_path = match.group(2)
        abs_path = Path(img_path).resolve()
        
        if abs_path.exists():
            parts.append({
                "type": "image",
                "image": str(abs_path),
                "alt_text": alt_text
            })
        
        last_end = match.end()
    
    if last_end < len(response):
        text_after = response[last_end:].strip()
        if text_after:
            parts.append({"type": "text", "text": text_after})
    
    if len(parts) == 1 and parts[0]["type"] == "text":
        return parts[0]["text"]
    
    return _convert_parts_to_html(parts)

def _convert_parts_to_html(parts: list) -> str:
    """将多媒体部分转换为 HTML 字符串"""
    html_parts = []
    
    for part in parts:
        if part["type"] == "text":
            text = part["text"].replace("\n", "<br>")
            html_parts.append(f'<div style="margin: 10px 0;">{text}</div>')
        elif part["type"] == "image":
            img_path = part["image"]
            alt_text = part.get("alt_text", "图表")
            html_parts.append(
                f'<div style="margin: 15px 0; text-align: center;">'
                f'<img src="{img_path}" alt="{alt_text}" '
                f'style="max-width: 100%; max-height: 500px; border-radius: 8px; '
                f'box-shadow: 0 2px 8px rgba(0,0,0,0.1);"/>'
                f'</div>'
            )
    
    return "\n".join(html_parts)

# 执行测试
print("="*70)
print("测试图片显示修复")
print("="*70)

print("\n原始响应:")
print(test_response)

print("\n" + "="*70)
print("处理后的响应 (HTML):")
print("="*70)

processed = _separate_images_from_text(test_response)
print(processed)

print("\n" + "="*70)
print("验证结果:")
print("="*70)

if "<img" in processed:
    print("✅ 图片已转换为 HTML img 标签")
    # 提取图片路径
    img_match = re.search(r'src="([^"]+)"', processed)
    if img_match:
        img_path = img_match.group(1)
        print(f"📷 图片路径: {img_path}")
        if Path(img_path).exists():
            print(f"✅ 图片文件存在: {Path(img_path).stat().st_size} bytes")
        else:
            print(f"❌ 图片文件不存在")
else:
    print("❌ 图片未正确转换")

print("\n测试完成！")
