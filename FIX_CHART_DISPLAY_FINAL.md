# WebUI 图表显示最终解决方案

## 🎯 问题回顾

用户反馈：**Web 界面没有显示折线图**

之前的尝试：
1. ❌ 使用 Markdown 图片语法 `![alt](path)` - Gradio Chatbot 不支持
2. ❌ 转换为 HTML `<img>` 标签 - Gradio 5.x 默认不渲染 HTML
3. ❌ Base64 编码嵌入 - 虽然有效但数据量大，且仍需要 HTML 支持

## ✅ 最终解决方案

### 核心思路

**将图表和聊天历史分离显示**，而不是试图在 Chatbot 中嵌入图片。

### 实现方式

#### 1. 界面布局调整

```python
with gr.Column(scale=4):
    # 聊天历史（纯文本）
    chatbot = gr.Chatbot(...)
    
    # 🔧 新增：独立的图表显示区域
    chart_display = gr.Image(
        label="📊 图表展示",
        height=400,
        visible=False,  # 初始隐藏
        show_download_button=True
    )
    
    # 输入区域
    with gr.Row():
        question_input = gr.Textbox(...)
        submit_btn = gr.Button(...)
```

#### 2. 处理逻辑

新增 `process_question_with_chart()` 方法：

```python
async def process_question_with_chart(self, question: str, history: List):
    # 1. 运行 bot 获取响应
    result = await self.bot.run(question, session_key=session_key)
    answer = result.content
    
    # 2. 提取图表路径
    chart_path = self._extract_chart_path(answer)
    
    # 3. 清理回答中的图片标记
    clean_answer = self._remove_image_markers(answer)
    
    # 4. 更新聊天历史（纯文本）
    history[-1] = [question, clean_answer]
    
    # 5. 返回三元组：输入框、历史、图表
    if chart_path:
        return "", history, gr.update(value=chart_path, visible=True)
    else:
        return "", history, gr.update(visible=False)
```

#### 3. 辅助方法

##### `_extract_chart_path()` - 提取图片路径

```python
def _extract_chart_path(self, response: str) -> str:
    """从响应中提取图表路径"""
    import re
    from pathlib import Path
    
    # 匹配 Markdown 图片语法
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    match = re.search(img_pattern, response)
    
    if match:
        img_path = match.group(2)
        abs_path = Path(img_path).resolve()
        
        if abs_path.exists():
            return str(abs_path)
    
    return ""
```

##### `_remove_image_markers()` - 清理图片标记

```python
def _remove_image_markers(self, response: str) -> str:
    """从响应中移除图片标记"""
    import re
    
    # 移除 Markdown 图片语法
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    clean_response = re.sub(img_pattern, '', response)
    
    # 清理多余空行
    clean_response = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_response)
    
    return clean_response.strip()
```

### 效果展示

修复后的界面布局：

```
┌─────────────────────────────────────────────┐
│  ChatBI 股票助手                             │
├─────────────────────────────────────────────┤
│                                             │
│  💬 对话历史                                 │
│  ┌───────────────────────────────────────┐  │
│  │ 用户: 贵州茅台最近一个月的股价走势      │  │
│  │ AI:   贵州茅台（600519.SH）...         │  │
│  │       （文字分析内容）                  │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  📊 图表展示  ← 🔧 新增区域                 │
│  ┌───────────────────────────────────────┐  │
│  │                                       │  │
│  │     [折线图显示在这里]                 │  │
│  │                                       │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [输入框]  [发送按钮]                        │
└─────────────────────────────────────────────┘
```

### 工作流程

```
用户输入问题
    ↓
NanoBot 处理（调用 exc_sql 工具）
    ↓
生成图表文件 (data/image_show/xxx.png)
    ↓
LLM 返回包含图片路径的响应
    ↓
WebUI 处理：
  ├─ 提取图片路径 → 显示在 chart_display
  └─ 清理图片标记 → 显示在 chatbot
    ↓
用户看到：文字 + 图表（分开显示）
```

## 📝 修改的文件

| 文件 | 修改内容 |
|------|---------|
| `webui.py` | 1. 添加 `chart_display` 组件<br>2. 新增 `process_question_with_chart()`<br>3. 新增 `_extract_chart_path()`<br>4. 新增 `_remove_image_markers()`<br>5. 修改事件绑定 |

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
   - ✅ 聊天历史显示文字分析
   - ✅ 图表区域显示折线图
   - ✅ 可以下载图表图片

### 预期输出

**聊天历史区域：**
```
用户: 贵州茅台最近一个月的股价走势

AI: 贵州茅台（600519.SH）最近一个月（22个交易日）的股价走势分析如下：

### 📈 整体趋势
- 起始日期：2026-03-25（收盘价 1410.27 元）
- 最新日期：2026-04-24（收盘价 1458.4 元）
...
```

**图表展示区域：**
```
📊 图表展示
┌────────────────────────┐
│                        │
│   [折线图正常显示]      │
│                        │
└────────────────────────┘
[下载按钮]
```

## 🎨 优势分析

### 相比之前方案的优点

1. **✅ 可靠性高**
   - 不依赖 HTML 渲染
   - 使用 Gradio 原生 Image 组件
   - 兼容所有 Gradio 版本

2. **✅ 用户体验好**
   - 图表清晰可见
   - 支持下载功能
   - 图文分离，布局清晰

3. **✅ 实现简单**
   - 代码逻辑清晰
   - 易于维护和扩展
   - 不需要复杂的转换

4. **✅ 性能优秀**
   - 无 base64 编码开销
   - 直接文件路径引用
   - 加载速度快

### 可能的改进空间

1. **布局优化**
   - 可以将图表放在右侧（使用 `gr.Row` 分栏）
   - 或者使用 Tab 切换显示

2. **交互增强**
   - 点击图片放大查看
   - 支持多图切换
   - 添加图表说明

## 🔧 进一步优化建议

### 方案一：左右分栏布局

```python
with gr.Row():
    with gr.Column(scale=2):
        chatbot = gr.Chatbot(...)
    
    with gr.Column(scale=1):
        chart_display = gr.Image(...)
```

### 方案二：Tab 切换

```python
with gr.Tabs():
    with gr.Tab("💬 对话"):
        chatbot = gr.Chatbot(...)
    
    with gr.Tab("📊 图表"):
        chart_display = gr.Image(...)
```

### 方案三：折叠面板

```python
with gr.Accordion("📊 查看图表", open=False):
    chart_display = gr.Image(...)
```

## 📚 技术要点

### Gradio Image 组件

```python
gr.Image(
    value=None,           # 图片路径或 numpy 数组
    label="图表展示",
    height=400,
    visible=False,        # 控制显示/隐藏
    show_download_button=True  # 显示下载按钮
)
```

### 动态更新组件

```python
# 显示图片
gr.update(value="/path/to/image.png", visible=True)

# 隐藏图片
gr.update(visible=False)
```

## 🎓 经验总结

### 关键教训

1. **不要强行在不支持的组件中嵌入富文本**
   - Gradio Chatbot 主要用于文本对话
   - 图片、视频等多媒体应使用专用组件

2. **分离关注点**
   - 聊天历史：纯文本
   - 图表展示：Image 组件
   - 各司其职，清晰明了

3. **利用 Gradio 的状态管理**
   - 使用 `visible` 属性控制显示
   - 使用 `gr.update()` 动态更新

### 最佳实践

- ✅ 优先使用 Gradio 原生组件
- ✅ 避免复杂的 HTML/CSS hack
- ✅ 保持代码简洁可维护
- ✅ 注重用户体验和易用性

---

**修复日期**: 2026-04-27  
**版本**: v2.0 (最终方案)  
**状态**: ✅ 已实现并测试通过  
**作者**: ChatBI 开发团队
