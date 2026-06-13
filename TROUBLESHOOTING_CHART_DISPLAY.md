# 图表显示问题 - 完整诊断与修复方案

## 🔍 问题诊断流程

### 步骤1: 确认图表文件是否生成

检查 `data/image_show/` 目录下是否有最新的 PNG 文件：

```bash
Get-ChildItem "data\image_show\*.png" | Sort-Object LastWriteTime -Descending | Select-Object -First 3
```

**结果**: ✅ 图表文件正常生成（75KB）

### 步骤2: 确认工具返回格式

检查 `app/tools/exc_sql.py` 的返回值：

```python
# 生成图表
img_path = self.chart_generator.generate_smart_chart(df)

# 转换为绝对路径
from pathlib import Path
abs_img_path = Path(img_path).resolve()

# 使用 Markdown 格式返回
img_md = f'![股票走势图]({abs_img_path})'

return f"{md}\n\n{img_md}"
```

**结果**: ✅ 工具正确返回包含图片标记的文本

### 步骤3: 确认 LLM 是否保留图片标记 ⚠️

**问题根源**: LLM 在生成最终回答时，可能会重新组织语言，**丢弃工具返回的图片标记**。

这是 Agent 系统的常见问题：
```
工具返回: "数据概览...\n![股票走势图](path)"
    ↓ (LLM 处理)
最终输出: "数据概览..."  ← 图片标记被删除了！
```

## ✅ 解决方案

### 方案1: 修改系统提示词（已实施）✅

在 [`AGENTS.md`](file://d:\AI-LLM-P\25-项目实战：ChatBI开发实战\CASE-ChatBI助手-nanobot-newgui\AGENTS.md) 中添加明确的规则：

```markdown
### 🔧 图片显示规则（重要！）
- **当工具返回包含 `![xxx](路径)` 的图片标记时，必须原样保留在回答中**
- **不要删除、修改或重新组织图片标记**
- **图片标记应该放在相关数据分析之后**
```

### 方案2: 添加调试日志（已实施）✅

在 [`webui.py`](file://d:\AI-LLM-P\25-项目实战：ChatBI开发实战\CASE-ChatBI助手-nanobot-newgui\webui.py) 中添加详细的调试信息：

```python
async def process_question_with_chart(self, question: str, history: List):
    # 运行 bot
    result = await self.bot.run(question, session_key=session_key)
    answer = result.content
    
    print(f"📝 LLM 原始响应 (前500字符):")
    print(answer[:500])
    
    # 提取图片路径
    chart_path = self._extract_chart_path(answer)
    print(f"🖼️ 提取的图表路径: {chart_path if chart_path else '未找到'}")
```

### 方案3: 增强图片提取逻辑（已实施）✅

支持多种图片格式：
- Markdown: `![alt](path)`
- HTML: `<img src="path"/>`

## 🧪 测试验证

### 启动 WebUI 并观察日志

```bash
python webui.py
```

输入查询：
```
贵州茅台最近一个月的股价走势
```

### 预期日志输出

```
======================================================================
🔍 处理问题: 贵州茅台最近一个月的股价走势
======================================================================

📝 LLM 原始响应 (前500字符):
贵州茅台（600519.SH）最近一个月（22个交易日）的股价走势分析如下：

### 📈 整体趋势
- 起始日期：2026-03-25（收盘价 1410.27 元）
...
![股票走势图](D:/.../stock_chart_xxx.png)

🔎 正在搜索图片标记...
✅ 找到 1 个图片标记
   [1] Alt: 股票走势图
       路径: D:/.../stock_chart_xxx.png
       绝对路径: D:\...\stock_chart_xxx.png
       文件存在: True

🖼️ 提取的图表路径: D:\...\stock_chart_xxx.png
✅ 图表文件存在: True
📊 文件大小: 75128 bytes
======================================================================
```

### 界面效果

```
┌─────────────────────────────────────┐
│ 💬 对话历史                          │
│ ┌─────────────────────────────────┐ │
│ │ 用户: 贵州茅台最近一个月...      │ │
│ │ AI:   贵州茅台股价分析...        │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 📊 图表展示  ← 应该显示折线图       │
│ ┌─────────────────────────────────┐ │
│ │                                 │ │
│ │   [折线图正常显示]               │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## 🛠️ 如果仍然没有显示

### 检查清单

1. **查看控制台日志**
   - 是否显示 "找到 X 个图片标记"？
   - 如果显示 "未找到任何图片标记"，说明 LLM 没有保留图片

2. **检查 LLM 响应**
   - 日志中会打印 LLM 的原始响应
   - 确认响应中是否包含 `![xxx](path)` 格式

3. **检查文件路径**
   - 确认图片文件确实存在
   - 路径是否正确

### 可能的原因和对策

| 现象 | 原因 | 对策 |
|------|------|------|
| 日志显示"未找到图片标记" | LLM 删除了图片标记 | 加强 AGENTS.md 中的指令，或调整模型参数 |
| 日志显示"文件不存在" | 路径错误或文件未生成 | 检查 exc_sql.py 的图表生成逻辑 |
| 日志显示找到图片但界面不显示 | Gradio Image 组件问题 | 检查 Gradio 版本，尝试重启 |
| 完全没有日志输出 | 代码未执行到 | 检查事件绑定是否正确 |

## 🔧 进一步优化建议

### 如果 LLM 仍然不保留图片标记

可以尝试以下方法：

#### 方法A: 使用特殊的占位符

修改 `exc_sql.py`，使用特殊标记：

```python
# 使用特殊标记而不是标准 Markdown
img_marker = f"__CHART_PATH__:{abs_img_path}__"
return f"{md}\n\n{img_marker}"
```

然后在 WebUI 中替换：

```python
def _extract_chart_path(self, response: str) -> str:
    # 查找特殊标记
    marker_pattern = r'__CHART_PATH__:(.+?)__'
    match = re.search(marker_pattern, response)
    
    if match:
        chart_path = match.group(1)
        # 从响应中移除标记
        response = re.sub(marker_pattern, '', response)
        return chart_path
    
    return ""
```

#### 方法B: 强制后处理

在 LLM 返回后，手动插入图片：

```python
# 检测是否调用了 exc_sql 工具
if 'exc_sql' in tool_calls:
    # 自动生成最新图表
    latest_chart = get_latest_chart()
    if latest_chart:
        answer += f"\n\n![股票走势图]({latest_chart})"
```

#### 方法C: 调整模型参数

在 `config.json` 中调整参数，让 LLM 更忠实于工具返回：

```json
{
  "model_params": {
    "temperature": 0.1,  // 降低随机性
    "top_p": 0.8
  }
}
```

## 📝 相关文件

| 文件 | 作用 |
|------|------|
| `AGENTS.md` | 系统提示词，控制 LLM 行为 |
| `webui.py` | WebUI 主程序，包含图片提取逻辑 |
| `app/tools/exc_sql.py` | SQL 工具，生成图表并返回路径 |
| `app/services/chart_generator.py` | 图表生成服务 |

## 🎯 下一步行动

1. **重新启动 WebUI**
   ```bash
   python webui.py
   ```

2. **观察控制台日志**
   - 查看 LLM 的原始响应
   - 确认是否包含图片标记

3. **根据日志判断问题**
   - 如果有图片标记但不显示 → Gradio 组件问题
   - 如果没有图片标记 → LLM 行为问题，需要调整提示词

4. **反馈结果**
   - 将日志输出提供给我
   - 我会根据实际情况进一步调整

---

**修复时间**: 2026-04-27  
**状态**: 🔧 调试中，等待测试反馈  
**关键修改**: 
- ✅ 添加详细调试日志
- ✅ 增强系统提示词
- ✅ 支持多种图片格式解析
