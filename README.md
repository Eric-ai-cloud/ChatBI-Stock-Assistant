# 📊 ChatBI 股票查询助手

基于 **Qwen-Agent** 框架和 **SQLite** 数据库的智能股票查询助手，通过自然语言交互，轻松查询和分析股票历史数据。

## ✨ 核心功能

### 1. 智能对话查询
- 支持自然语言提问，AI 自动解析意图、生成 SQL 并执行
- 覆盖贵州茅台、五粮液、广发证券、中芯国际四只股票（2020年至今）

### 2. 智能可视化
- 自动根据数据量选择最佳图表类型（≤20条柱状图，>20条折线图）
- 横坐标智能采样，避免标签重叠
- 支持中文显示，图表美观清晰

### 3. ARIMA 价格预测
- 基于 ARIMA(5,1,5) 模型预测未来 N 天股票收盘价
- 95% 置信区间展示
- 历史数据 + 预测结果可视化对比

### 4. 布林带异常检测
- 20日移动平均线 + 2倍标准差布林带
- 自动检测超买点（突破上轨）和超卖点（跌破下轨）
- 异常点可视化标记

### 5. 多模式交互
- Web 图形化界面（推荐）
- 命令行终端模式

## 🗄️ 数据库说明

### 表结构

```sql
CREATE TABLE stock_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code VARCHAR(20) NOT NULL,      -- 股票代码
    stock_name VARCHAR(50) NOT NULL,      -- 股票名称
    trade_date VARCHAR(10) NOT NULL,      -- 交易日期 (YYYYMMDD格式)
    open_price DECIMAL(10,2),             -- 开盘价
    high_price DECIMAL(10,2),             -- 最高价
    low_price DECIMAL(10,2),              -- 最低价
    close_price DECIMAL(10,2),            -- 收盘价
    pre_close DECIMAL(10,2),              -- 昨收价
    change_amount DECIMAL(10,2),          -- 涨跌额
    change_pct DECIMAL(10,4),             -- 涨跌幅(%)
    volume INTEGER,                       -- 成交量(手)
    amount DECIMAL(15,2)                  -- 成交额(千元)
);
```

### 支持的股票

| 股票名称 | 股票代码 | 数据起始日期 |
|---------|---------|------------|
| 贵州茅台 | 600519.SH | 2020-01-02 |
| 五粮液 | 000858.SZ | 2020-01-02 |
| 广发证券 | 000776.SZ | 2020-01-02 |
| 中芯国际 | 688981.SH | 2020-07-16 |

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/Eric-ai-cloud/ChatBI-Stock-Assistant.git
cd CASE-ChatBI助手

# 安装依赖
pip install -r requirements.txt
```

**配置 API Key：**

**Windows PowerShell:**
```powershell
$env:DASHSCOPE_API_KEY="your-api-key-here"
```

**Linux/Mac:**
```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

### 2. 数据准备（可选，项目中已包含示例数据）

如需更新股票数据：

```bash
# 第一步：从 Tushare 获取最新数据（需要 TUSHARE_TOKEN）
cd scripts
python fetch_stock_history.py

# 第二步：导入到 SQLite 数据库
python import_to_sqlite.py
```

### 3. 启动助手

#### Web 图形界面（推荐）

```bash
cd src
python stock_assistant.py
```

程序会自动打开浏览器，显示聊天界面。

#### 命令行终端模式

编辑 `src/stock_assistant.py` 文件末尾：

```python
if __name__ == '__main__':
    # app_gui()          # 注释掉这行
    app_tui()            # 取消注释这行
```

## 💡 使用示例

### 基础查询
- "贵州茅台最近一年的收盘价走势"
- "五粮液2024年各月的平均收盘价"

### 对比分析
- "四只股票2024年平均收盘价对比"
- "比较贵州茅台和五粮液的成交量"
- "对比2025年中芯国际和贵州茅台的涨跌幅"

### 统计分析
- "中芯国际成交量最大的10个交易日"
- "广发证券2024年涨跌幅超过5%的交易日有多少"
- "贵州茅台最近30天最高价和最低价"

### 预测分析
- "预测贵州茅台未来7天股价"
- "预测五粮液未来30天走势"

### 异常检测
- "检测贵州茅台最近的超买超卖点"
- "五粮液最近三个月有超买信号吗"

## 📁 项目结构

```
CASE-ChatBI助手/
├── src/                          # 主程序源码
│   └── stock_assistant.py        # 股票助手主程序
├── scripts/                      # 数据脚本
│   ├── fetch_stock_history.py    # 从 Tushare 获取数据
│   └── import_to_sqlite.py       # 导入数据到 SQLite
├── tests/                        # 测试文件
│   ├── test_db.py                # 数据库连接测试
│   ├── test_smart_chart.py       # 智能可视化测试
│   ├── test_data_preview.py      # 数据预览测试
│   ├── test_arima_prediction.py  # ARIMA 预测测试
│   ├── test_arima_tool.py        # ARIMA 工具测试
│   ├── test_boll_detection.py    # 布林带检测测试
│   ├── test_sql_preprocessing.py # SQL 预处理测试
│   ├── test_enhanced_sql_preprocessing.py
│   ├── test_high_low_prices.py   # 最高/最低价查询测试
│   ├── test_high_low_correct.py  # 最高/最低价修正测试
│   ├── test_recent_month_query.py
│   ├── test_recent_month_definition.py
│   ├── test_sql_patterns.py
│   ├── test_trading_days.py
│   └── test_trading_days_with_holidays.py
├── data/                         # 数据文件
│   ├── create_stock_table.sql    # 建表 SQL
│   ├── faq.txt                   # FAQ 知识库
│   ├── stock_prices.db           # SQLite 数据库
│   └── stock_history_data.xlsx   # Excel 数据源
├── docs/                         # 文档归档
│   ├── README_股票助手.md
│   ├── README_智能可视化升级.md
│   ├── README_数据预览优化.md
│   ├── README_FAQ优化.md
│   ├── README_SQL查询修复.md
│   ├── README_涨跌幅计算修复.md
│   ├── README_ARIMA预测功能.md
│   └── README_布林带检测功能.md
├── .gitignore
├── README.md
└── requirements.txt
```

## ⚙️ 技术架构

| 层级 | 技术栈 |
|------|--------|
| **LLM 框架** | Qwen-Agent |
| **大模型服务** | 阿里云 DashScope (通义千问 qwen-turbo) |
| **数据库** | SQLite + SQLAlchemy |
| **数据处理** | Pandas, NumPy |
| **可视化** | Matplotlib |
| **预测模型** | ARIMA(5,1,5) |
| **异常检测** | 布林带 (20日, 2σ) |

### 工作流程

```
用户输入自然语言问题
    ↓
Qwen-Agent 理解意图 + FAQ 知识库增强
    ↓
SQL 预处理（修正日期查询、字段名等常见错误）
    ↓
生成并执行 SQL 查询
    ↓
获取数据 → 智能选择图表类型
    ↓
返回结果（表格 + 图表）给用户
```

## ⚠️ 重要提示

### 日期查询规范
- `trade_date` 是字符串类型 `YYYYMMDD`（如 `'20240101'`）
- ❌ **禁止**对日期做算术运算：`MAX(trade_date) - 30`
- ✅ **正确**：使用 `ORDER BY trade_date DESC LIMIT 30` 获取最近 N 条

### 涨跌幅计算
- 公式：`(期末收盘价 - 期初收盘价) / 期初收盘价 × 100%`
- 使用子查询分别获取期初和期末收盘价
- ❌ 不要用 `MAX(close_price) - MIN(close_price)`（那是波动率）

### 最高/最低价
- 最高价用 `high_price` 字段，最低价用 `low_price` 字段
- 不要与 `close_price` 混淆

## 🐛 常见问题

### Q1: 提示 "DASHSCOPE_API_KEY not found"
确保已正确设置环境变量：
```bash
# Windows PowerShell
$env:DASHSCOPE_API_KEY="your-api-key-here"

# Linux/Mac
export DASHSCOPE_API_KEY="your-api-key-here"
```

### Q2: 中文图表显示乱码
确保系统安装了中文字体（SimHei 或 Microsoft YaHei）

### Q3: 找不到数据库文件
先运行数据导入脚本：
```bash
cd scripts
python fetch_stock_history.py
python import_to_sqlite.py
```

### Q4: Web 界面无法访问
1. 检查防火墙设置
2. 确认端口未被占用
3. 尝试使用终端模式 `app_tui()`

## 📝 版本历史

### v4.0 - 布林带异常检测
- ✅ 新增布林带(Bollinger Bands)异常点检测
- ✅ 超买/超卖点自动识别与可视化

### v3.0 - ARIMA 预测
- ✅ 新增 ARIMA(5,1,5) 价格预测功能
- ✅ FAQ 知识库优化，SQL 查询修复
- ✅ 涨跌幅计算逻辑修正

### v2.0 - 智能可视化
- ✅ 图表类型自动选择（柱状图/折线图）
- ✅ 数据预览增强
- ✅ 横坐标智能采样

### v1.0 - 基础版本
- ✅ 自然语言股票查询
- ✅ 自动可视化
- ✅ Web + 终端双模式

## 📞 技术支持

- Python 版本 >= 3.8
- 所有依赖包已正确安装
- DASHSCOPE_API_KEY 已正确配置

---

**祝您使用愉快！** 🎉
