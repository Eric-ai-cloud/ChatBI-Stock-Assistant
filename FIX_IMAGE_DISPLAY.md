# 图表显示问题修复说明

## 🐛 问题描述

用户在 WebUI 中查询股票数据时，虽然系统生成了图表文件，但界面上没有显示折线图。

**症状：**
- SQL 查询正常执行（返回 22 行数据）
- 图表文件成功生成（`data/image_show/stock_chart_xxx.png`，75KB）
- 但 WebUI 界面中没有显示图片

## 🔍 问题分析

### 根本原因

Gradio 的 `Chatbot` 组件**不支持直接渲染 Markdown 格式的图片语法** `![alt](path)`。

原始代码在 `exc_sql.py` 中返回：
```python
img_md = f'![股票走势图]({img_path})'
return f"{md}\n\n{img_md}"
```

这种 Markdown 格式在普通 Markdown 阅读器中可以正常显示，但 Gradio Chatbot 不会将其渲染为图片。

### 技术细节

1. **图表生成流程**：
   ```
   SQL查询 → DataFrame → ChartGenerator → PNG文件 → Markdown路径 → LLM响应
   ```

2. **问题环节**：
   - ✅ 图表生成：正常（文件已创建）
   - ✅ 路径返回：正常（相对路径 `data/image_show/xxx.png`）
   - ❌ 前端渲染：失败（Gradio 不支持 Markdown 图片语法）

## ✅ 解决方案

### 方案选择

采用 **HTML `<img>` 标签**方式，因为：
1. Gradio Chatbot 支持有限的 HTML 渲染
2. 实现简单，无需修改太多代码
3. 兼容性好，适用于各种场景

### 实施步骤

#### 1. 修改 `exc_sql.py` - 使用绝对路径

```python
# 生成图表
img_path = self.chart_generator.generate_smart_chart(df)

# 转换为绝对路径
from pathlib import Path
abs_img_path = Path(img_path).resolve()

# 使用绝对路径
img_md = f'![股票走势图]({abs_img_path})'
```

**原因**：确保图片路径在任何工作目录下都能正确解析。

#### 2. 修改 `webui.py` - 添加图片处理逻辑

新增两个方法：

##### `_separate_images_from_text()` - 分离图片和文本

```python
def _separate_images_from_text(self, response: str):
    """从响应中分离图片和文本，转换为 Gradio 多媒体格式"""
    # 使用正则表达式匹配 Markdown 图片语法
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = list(re.finditer(img_pattern, response))
    
    if not matches:
        return response  # 没有图片，直接返回
    
    # 构建多媒体消息结构
    parts = []
    # ... 解析文本和图片部分
    
    return self._convert_parts_to_html(parts)
```

##### `_convert_parts_to_html()` - 转换为 HTML

```python
def _convert_parts_to_html(self, parts: list) -> str:
    """将多媒体部分转换为 HTML 字符串"""
    html_parts = []
    
    for part in parts:
        if part["type"] == "text":
            text = part["text"].replace("\n", "<br>")
            html_parts.append(f'<div>{text}</div>')
        elif part["type"] == "image":
            html_parts.append(
                f'<div style="text-align: center;">'
                f'<img src="{part["image"]}" style="max-width: 100%;"/>'
                f'</div>'
            )
    
    return "\n".join(html_parts)
```

##### 在 `process_question()` 中调用

```python
async def process_question(self, question: str, history: List):
    # ... 运行 bot
    
    answer = result.content
    
    # 处理图片
    processed_answer = self._separate_images_from_text(answer)
    
    history[-1] = [question, processed_answer]
    return "", history
```

### 效果展示

修复前：
```
**数据概览**: 共 22 行, 6 列
...
![股票走势图](data/image_show/stock_chart_123.png)
```
❌ 图片不显示

修复后：
```html
<div>
  **数据概览**: 共 22 行, 6 列<br>
  ...
</div>
<div style="text-align: center;">
  <img src="D:/.../stock_chart_123.png" 
       style="max-width: 100%; border-radius: 8px;"/>
</div>
```
✅ 图片正常显示

## 🎨 样式优化

为了让图片显示更美观，添加了以下 CSS 样式：

```css
img {
    max-width: 100%;           /* 响应式宽度 */
    max-height: 500px;         /* 限制最大高度 */
    border-radius: 8px;        /* 圆角 */
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);  /* 阴影效果 */
}
```

## 📝 相关文件

| 文件 | 修改内容 |
|------|---------|
| `app/tools/exc_sql.py` | 使用绝对路径生成图片链接 |
| `webui.py` | 添加图片处理和 HTML 转换逻辑 |

## 🧪 测试验证

### 测试步骤

1. 启动 WebUI：
   ```bash
   python webui.py
   ```

2. 输入查询：
   ```
   贵州茅台最近一个月的股价走势
   ```

3. 验证结果：
   - ✅ 文字信息显示正常
   - ✅ 折线图显示正常
   - ✅ 图片居中显示，带有圆角和阴影

### 预期输出

```
📊 ChatBI 股票助手

贵州茅台（600519.SH）最近一个月（22个交易日）的股价走势分析如下：

### 📈 整体趋势
- 起始日期：2026-03-25
- 最新日期：2026-04-24
...

[折线图显示在这里]
```

## 🔧 进一步优化建议

### 短期优化

1. **图片懒加载**：对于大量图片的情况，可以实现懒加载
2. **图片压缩**：减小 PNG 文件大小，提高加载速度
3. **缓存机制**：相同查询复用已有图表

### 长期优化

1. **交互式图表**：使用 Plotly 或 Echarts 替代 Matplotlib
2. **图片预览**：点击缩略图查看大图
3. **导出功能**：允许用户下载图表

## 📚 参考资料

- [Gradio Chatbot 文档](https://www.gradio.app/docs/gradio/chatbot)
- [Gradio 多媒体消息格式](https://www.gradio.app/guides/chatbot-multimodal)
- [HTML img 标签规范](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img)

---

**修复日期**: 2026-04-27  
**版本**: v1.1  
**状态**: ✅ 已修复并测试通过
