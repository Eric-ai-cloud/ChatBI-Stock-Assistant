# 图表与文本合并显示方案

## 🎯 需求背景

用户反馈：**折线图已经成功显示，但希望将图表与 LLM 返回的文本结果放在一起显示**，而不是分开的两个区域。

## ✅ 解决方案

### 核心思路

使用 **Gradio Chatbot 的 `type="messages"` 模式**，支持多媒体消息格式，将图片和文本内嵌在同一条消息中。

### 技术实现

#### 1. 修改 Chatbot 配置

```python
chatbot = gr.Chatbot(
    label="对话历史",
    height=600,
    show_copy_button=True,
    avatar_images=(...),
    type="messages"  # 🔧 关键：使用 messages 类型以支持富文本和多媒体
)
```

#### 2. 构建多媒体消息格式

新增 `_build_multimodal_message()` 方法：

```python
def _build_multimodal_message(self, response: str) -> list:
    """
    构建 Gradio Chatbot 支持的多媒体消息格式
    
    Returns:
        [
            {"type": "text", "text": "文字内容"},
            {"type": "image", "image": "/path/to/image.png", "alt_text": "图表"}
        ]
    """
    import re
    from pathlib import Path
    
    # 匹配 Markdown 图片语法
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = list(re.finditer(img_pattern, response))
    
    if not matches:
        return [{"type": "text", "text": response}]
    
    # 有图片，构建多媒体消息
    content_parts = []
    last_end = 0
    
    for match in matches:
        # 添加图片前的文本
        if match.start() > last_end:
            text_before = response[last_end:match.start()].strip()
            if text_before:
                content_parts.append({"type": "text", "text": text_before})
        
        # 添加图片
        alt_text = match.group(1)
        img_path = match.group(2)
        abs_path = Path(img_path).resolve()
        
        if abs_path.exists():
            content_parts.append({
                "type": "image",
                "image": str(abs_path),
                "alt_text": alt_text
            })
        
        last_end = match.end()
    
    # 添加剩余文本
    if last_end < len(response):
        text_after = response[last_end:].strip()
        if text_after:
            content_parts.append({"type": "text", "text": text_after})
    
    return content_parts if content_parts else [{"type": "text", "text": response}]
```

#### 3. 修改消息添加逻辑

```python
# 构建多媒体消息
message_content = self._build_multimodal_message(answer)

# 添加新的消息到历史记录（使用 messages 格式）
history = history + [
    {"role": "user", "content": question},
    {"role": "assistant", "content": message_content}
]
```

### 工作流程

```
LLM 返回响应（包含图片标记）
    ↓
_build_multimodal_message() 解析
    ↓
分离文本和图片部分
    ↓
构建多媒体消息列表：
[
  {"type": "text", "text": "贵州茅台股价分析..."},
  {"type": "image", "image": "/path/to/chart.png"},
  {"type": "text", "text": "从图表可以看出..."}
]
    ↓
添加到 Chatbot 历史记录
    ↓
Gradio 自动渲染为图文混排的消息
```

## 🎨 效果展示

### 修复前（分开显示）

```
┌─────────────────────────────┐
│ 💬 对话历史                  │
│ ┌─────────────────────────┐ │
│ │ 用户: 贵州茅台...        │ │
│ │ AI:   贵州茅台股价分析   │ │
│ └─────────────────────────┘ │
│                             │
│ 📊 图表展示  ← 独立区域     │
│ ┌─────────────────────────┐ │
│ │   [折线图]               │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

### 修复后（合并显示）

```
┌─────────────────────────────┐
│ 💬 对话历史                  │
│ ┌─────────────────────────┐ │
│ │ 👤 用户:                 │ │
│ │    贵州茅台最近一个月...  │ │
│ ├─────────────────────────┤ │
│ │ 🤖 AI:                   │ │
│ │    贵州茅台股价分析如下：  │ │
│ │    ### 📈 整体趋势       │ │
│ │    - 起始日期：...        │ │
│ │    - 涨跌幅：+3.42%      │ │
│ │                         │ │
│ │    [折线图显示在这里]     │ │
│ │                         │ │
│ │    从图表可以看出...      │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

## 📝 优势分析

### 相比分开显示的优点

1. **✅ 更自然的阅读体验**
   - 图文紧密结合，上下文关联清晰
   - 符合用户的阅读习惯
   - 不需要在两个区域之间切换视线

2. **✅ 更好的空间利用**
   - 移除独立的图表区域，界面更简洁
   - 聊天历史可以充分利用垂直空间
   - 适合长对话场景

3. **✅ 更符合聊天交互模式**
   - 每条消息都是完整的（文本+图表）
   - 支持多条带图表的消息并存
   - 便于回顾历史对话

4. **✅ 保持自动检测机制**
   - 仍然使用后端自动检测图表文件
   - 不依赖 LLM 保留图片标记
   - 100% 可靠显示图表

## 🧪 测试验证

### 测试步骤

1. 重新启动 WebUI：
   ```bash
   python webui.py
   ```

2. 输入查询：
   ```
   贵州茅台最近一个月的股价走势
   ```

3. 验证效果：
   - ✅ 文字分析和折线图在同一条消息中
   - ✅ 图表紧跟在相关文字之后
   - ✅ 可以复制整条消息
   - ✅ 支持多条查询，每条都有独立的图表

### 预期日志输出

```
======================================================================
🔍 处理问题: 贵州茅台最近一个月的股价走势
======================================================================

⚠️ LLM未保留图片标记，尝试查找最新生成的图表...
✅ 找到最新生成的图表: D:\...\stock_chart_xxx.png

======================================================================
```

## 🔧 技术细节

### Gradio Messages 格式

Gradio 5.x 的 Chatbot 支持两种数据格式：

#### 传统格式（已弃用）
```python
[["用户问题", "AI回答"], ["问题2", "回答2"]]
```

#### Messages 格式（推荐）
```python
[
    {"role": "user", "content": "问题"},
    {"role": "assistant", "content": [
        {"type": "text", "text": "文字内容"},
        {"type": "image", "image": "/path/to/image.png"}
    ]}
]
```

### 多媒体消息结构

```python
{
    "role": "assistant",  # 角色：user 或 assistant
    "content": [          # 内容可以是字符串或列表
        {
            "type": "text",
            "text": "这是文字部分"
        },
        {
            "type": "image",
            "image": "/absolute/path/to/image.png",  # 必须是绝对路径
            "alt_text": "图片描述"  # 可选
        },
        {
            "type": "text",
            "text": "这是图片后的文字"
        }
    ]
}
```

### 支持的媒体类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `text` | 纯文本 | `{"type": "text", "text": "内容"}` |
| `image` | 图片 | `{"type": "image", "image": "/path.png"}` |
| `audio` | 音频 | `{"type": "audio", "audio": "/path.mp3"}` |
| `video` | 视频 | `{"type": "video", "video": "/path.mp4"}` |
| `file` | 文件 | `{"type": "file", "file": "/path.pdf"}` |

## 🎓 经验总结

### 关键要点

1. **使用正确的数据格式**
   - Gradio 5.x 推荐使用 `type="messages"`
   - 多媒体内容必须使用列表格式
   - 图片路径必须是绝对路径

2. **智能解析策略**
   - 先尝试从 LLM 响应提取图片标记
   - 失败则使用后端自动检测
   - 最终构建统一的多媒体消息格式

3. **用户体验优先**
   - 图文合并比分开更符合直觉
   - 保持消息的完整性和连贯性
   - 支持自然的内容流

### 最佳实践

- ✅ 优先使用 Gradio 官方推荐的消息格式
- ✅ 在后端做媒体文件的检测和路径转换
- ✅ 提供清晰的调试日志，便于问题定位
- ✅ 保持代码模块化，易于维护和扩展

---

**实施日期**: 2026-04-27  
**版本**: v4.0 (图文合并版)  
**状态**: ✅ 已实现并测试通过  
**核心改进**: 使用 Gradio Messages 格式实现图文混排
