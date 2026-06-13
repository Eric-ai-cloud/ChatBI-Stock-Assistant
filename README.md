# ChatBI 股票助手 (NanoBot 版本)

基于 NanoBot 框架的智能股票查询助手，支持自然语言查询、ARIMA 预测和布林带检测。

## 功能特性

- ✅ **智能SQL查询**: 自然语言转SQL，自动可视化
- ✅ **ARIMA预测**: 基于过去一年的数据预测未来股价
- ✅ **布林带检测**: 识别超买超卖异常点
- ✅ **WebUI界面**: 基于 Gradio 的友好交互界面（参考 qwen-agent WebUI 设计）
- ✅ **模块化架构**: 清晰的代码结构，易于维护

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 或者手动安装
pip install nanobot dashscope pandas sqlalchemy matplotlib numpy statsmodels gradio

# 设置 API Key
export DASHSCOPE_API_KEY="your-api-key-here"  # Linux/Mac
$env:DASHSCOPE_API_KEY="your-api-key-here"    # Windows PowerShell
```

### 2. 数据准备

从原项目复制数据库文件：

```bash
# 复制 SQLite 数据库
cp ../CASE-ChatBI助手/stock_prices.db data/

# 创建图表目录
mkdir -p data/image_show
```

### 3. 运行

#### 方式一：命令行模式

```bash
# 交互式命令行
python agent.py

# 直接查询
python agent.py "贵州茅台最近一个月的股价走势"
python agent.py "对比五粮液和中芯国际2024年的涨跌幅"
python agent.py "预测贵州茅台未来7天的股价"
python agent.py "检测贵州茅台的布林带超买超卖点"
```

#### 方式二：WebUI 界面（推荐）✨

**Windows 用户：**
```bash
# 双击运行或在命令行执行
start_webui.bat
```

**Linux/Mac 用户：**
```bash
chmod +x start_webui.sh
./start_webui.sh
```

**或直接运行：**
```bash
python webui.py
```

启动后在浏览器访问: **http://localhost:7860**

WebUI 提供以下功能：
- 💬 聊天式对话界面
- 📊 实时可视化结果展示
- 💡 示例问题快速提问
- 🗑️ 一键清空历史记录
- 🎨 美观的用户界面
- ⚙️ 参考 qwen-agent WebUI 设计模式

## 项目结构

```
CASE-ChatBI助手-nanobot-newgui/
├── agent.py                    # 命令行版主入口
├── webui.py                    # WebUI版主入口（参考 qwen-agent 设计）⭐
├── test_webui.py               # WebUI测试脚本 ⭐
├── start_webui.bat             # Windows启动脚本 ⭐
├── start_webui.sh              # Linux/Mac启动脚本 ⭐
├── WEBUI_GUIDE.md              # WebUI使用指南 ⭐
├── WEBUI_ARCHITECTURE.md       # WebUI架构说明（对比 qwen-agent）⭐
├── config.json                 # NanoBot配置
├── AGENTS.md                   # Agent提示词
├── faq.txt                     # FAQ知识库
├── requirements.txt            # 项目依赖 ⭐
├── app/
│   ├── tools/                  # 工具模块
│   │   ├── exc_sql.py         # SQL查询工具
│   │   ├── arima_stock.py     # ARIMA预测工具
│   │   └── boll_detection.py  # 布林带检测工具
│   ├── services/              # 业务逻辑层
│   │   ├── sql_preprocessor.py # SQL预处理
│   │   └── chart_generator.py  # 图表生成
│   └── utils/                 # 工具函数
│       ├── database.py        # 数据库连接
│       └── date_utils.py      # 日期处理
└── data/
    ├── stock_prices.db        # SQLite数据库
    └── image_show/            # 生成的图表
```

## WebUI 架构说明

本项目的 WebUI 参考了 qwen-agent 框架的 WebUI 设计模式，主要特点：

### 核心设计理念

1. **类封装**: 采用 `ChatBIWebUI` 类封装所有界面逻辑
2. **配置化**: 通过 `chatbot_config` 字典定制界面行为
3. **异步处理**: 使用 async/await 处理用户请求
4. **队列机制**: Gradio queue 管理并发请求

### 与 qwen-agent WebUI 的对比

| 特性 | qwen-agent | 本项目 |
|------|-----------|--------|
| Agent框架 | Qwen-Agent | NanoBot |
| 类名 | `WebUI` | `ChatBIWebUI` |
| 多Agent支持 | ✅ | ⚠️ 可扩展 |
| 文件上传 | ✅ | ❌ 可扩展 |
| 配置方式 | 相同 | 相同 |

详细对比请查看 [WEBUI_ARCHITECTURE.md](WEBUI_ARCHITECTURE.md)

## 支持的股票

- 贵州茅台 (600519.SH)
- 五粮液 (000858.SZ)
- 广发证券 (000776.SZ)
- 中芯国际 (688981.SH)

## 注意事项

⚠️ **重要规则**:
- `trade_date` 是字符串类型，禁止进行算术运算
- 最高价用 `high_price`，最低价用 `low_price`
- 涨跌幅计算必须展示原始数据和计算过程

## 支持的股票

- 贵州茅台 (600519.SH)
- 五粮液 (000858.SZ)
- 广发证券 (000776.SZ)
- 中芯国际 (688981.SH)

## 注意事项

⚠️ **重要规则**:
- `trade_date` 是字符串类型，禁止进行算术运算
- 最高价用 `high_price`，最低价用 `low_price`
- 涨跌幅计算必须展示原始数据和计算过程

## 文档

- 📖 [WebUI 使用指南](WEBUI_GUIDE.md) - 详细的使用说明
- 🏗️ [WebUI 架构说明](WEBUI_ARCHITECTURE.md) - 技术架构和与 qwen-agent 的对比

## 迁移说明

本项目从 Qwen-Agent 框架迁移到 NanoBot 框架，主要变化：

1. **工具注册**: 使用 `Tool` 类替代 `@register_tool` 装饰器
2. **异步执行**: 所有工具方法改为 `async execute()`
3. **模块化**: 将单体文件拆分为清晰的模块结构
4. **配置管理**: 使用 config.json 统一管理配置
5. **WebUI**: 参考 qwen-agent 设计，适配 NanoBot 框架

## License

MIT
