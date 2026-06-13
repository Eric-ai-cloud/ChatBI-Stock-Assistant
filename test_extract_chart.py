"""测试图表路径提取功能"""
import re
from pathlib import Path

# 模拟 LLM 可能返回的不同格式
test_responses = [
    # 格式1: 标准 Markdown
    """
贵州茅台最近一个月的股价走势分析：

### 数据概览
共 22 行数据

![股票走势图](data/image_show/stock_chart_1777262703060.png)

以上就是分析结果。
    """,
    
    # 格式2: 绝对路径
    """
分析结果如下：

![图表](D:/AI-LLM-P/25-项目实战：ChatBI开发实战/CASE-ChatBI助手-nanobot-newgui/data/image_show/stock_chart_1777262703060.png)

完毕。
    """,
    
    # 格式3: 没有图片
    """
贵州茅台的股价分析：

起始日期：2026-03-25
最新日期：2026-04-24

没有生成图表。
    """,
    
    # 格式4: HTML 格式（可能的情况）
    """
分析结果：

<img src="data/image_show/stock_chart_1777262703060.png" alt="图表"/>

结束。
    """
]

def extract_chart_path(response: str) -> str:
    """从响应中提取图表路径"""
    print(f"\n{'='*70}")
    print(f"测试响应:")
    print(response[:200])
    print("...")
    
    # 匹配 Markdown 图片语法
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = list(re.finditer(img_pattern, response))
    
    if matches:
        print(f"✅ 找到 {len(matches)} 个 Markdown 图片标记")
        for i, match in enumerate(matches):
            alt_text = match.group(1)
            img_path = match.group(2)
            print(f"   [{i+1}] {alt_text}: {img_path}")
            
            abs_path = Path(img_path).resolve()
            if abs_path.exists():
                print(f"       ✅ 文件存在: {abs_path}")
                return str(abs_path)
            else:
                print(f"       ❌ 文件不存在: {abs_path}")
    else:
        print(f"❌ 未找到 Markdown 图片标记")
        
        # 尝试查找 HTML img 标签
        html_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        html_matches = list(re.finditer(html_pattern, response))
        if html_matches:
            print(f"✅ 找到 {len(html_matches)} 个 HTML img 标签")
            for match in html_matches:
                img_path = match.group(1)
                print(f"   路径: {img_path}")
                
                abs_path = Path(img_path).resolve()
                if abs_path.exists():
                    print(f"       ✅ 文件存在: {abs_path}")
                    return str(abs_path)
    
    return ""

# 执行测试
print("="*70)
print("测试图表路径提取功能")
print("="*70)

for i, response in enumerate(test_responses, 1):
    print(f"\n\n{'#'*70}")
    print(f"测试用例 {i}")
    print(f"{'#'*70}")
    
    result = extract_chart_path(response)
    print(f"\n最终结果: {result if result else '未提取到路径'}")

print("\n" + "="*70)
print("测试完成")
print("="*70)
