# 股票查询助手使用指南

## 📊 项目简介

这是一个基于 **Qwen-Agent** 框架和 **SQLite** 数据库的智能股票查询助手，通过自然语言交互方式，让您轻松查询和分析股票历史数据。

## ✨ 核心功能

- **智能对话**: 支持自然语言提问，AI 自动解析意图、生成 SQL 并执行
- **自动可视化**: 查询结果自动生成图表（折线图、柱状图等）
- **多模式交互**: 提供 Web 图形化界面和命令行两种交互模式
- **数据覆盖**: 包含贵州茅台、五粮液、广发证券、中芯国际四只股票的历史数据（2020年至今）

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

### 支持的股票列表

| 股票名称 | 股票代码 | 数据起始日期 |
|---------|---------|------------|
| 贵州茅台 | 600519.SH | 2020-01-02 |
| 五粮液 | 000858.SZ | 2020-01-02 |
| 广发证券 | 000776.SZ | 2020-01-02 |
| 中芯国际 | 688981.SH | 2020-07-16 |

## 🚀 快速开始

### 1. 环境准备

#### 安装依赖包

```bash
pip install qwen-agent dashscope pandas sqlalchemy matplotlib numpy
```

#### 配置 API Key

**Windows PowerShell:**
```powershell
$env:DASHSCOPE_API_KEY="your-api-key-here"
```

**Linux/Mac:**
```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

### 2. 数据准备（如已完成可跳过）

如果还没有生成数据库文件，请依次执行：

```bash
# 第一步：获取股票数据并保存为Excel
python fetch_stock_history.py

# 第二步：将Excel数据导入SQLite数据库
python import_to_sqlite.py
```

执行完成后会生成 `stock_prices.db` 文件。

### 3. 启动助手

#### 方式一：Web 图形界面（推荐）

```bash
python stock_assistant.py
```

程序会自动打开浏览器，显示聊天界面。

#### 方式二：命令行终端模式

编辑 `stock_assistant.py` 文件末尾：

```python
if __name__ == '__main__':
    # app_gui()          # 注释掉这行
    app_tui()            # 取消注释这行
```

然后运行：

```bash
python stock_assistant.py
```

## 💡 使用示例

### Web 界面示例问题

1. **查看走势**
   - "贵州茅台最近一年的收盘价走势"
   - "五粮液2024年各月的平均收盘价"

2. **对比分析**
   - "四只股票2024年平均收盘价对比"
   - "比较贵州茅台和五粮液的成交量"

3. **统计分析**
   - "中芯国际成交量最大的10个交易日"
   - "广发证券2024年涨跌幅超过5%的交易日有多少"

4. **综合查询**
   - "贵州茅台2024年最高价和最低价分别是多少"
   - "四只股票最近一个月的平均成交额排名"

### 终端模式示例

```
请输入您的问题: 贵州茅台最近30天的收盘价走势

🤖 正在分析您的问题...

----------------------------------------------------------------------
[表格数据]
[走势图图片]
----------------------------------------------------------------------
```

## ⚙️ 技术架构

### 核心技术栈

- **LLM 框架**: Qwen-Agent
- **大模型服务**: 阿里云 DashScope (通义千问 qwen-turbo)
- **数据库**: SQLite
- **数据处理**: Pandas, SQLAlchemy
- **可视化**: Matplotlib

### 工作流程

```
用户输入自然语言问题
    ↓
Qwen-Agent 理解意图
    ↓
生成 SQL 查询语句
    ↓
执行 SQL 查询 SQLite 数据库
    ↓
获取数据并自动生成图表
    ↓
返回结果（表格 + 图片）给用户
```

## 📁 项目文件说明

| 文件名 | 说明 |
|-------|------|
| `stock_assistant.py` | **主程序** - 股票查询助手入口 |
| `fetch_stock_history.py` | 数据获取脚本 - 从 Tushare 获取股票数据 |
| `import_to_sqlite.py` | 数据导入脚本 - 将Excel数据导入SQLite |
| `create_stock_table.sql` | SQL建表语句 |
| `stock_prices.db` | SQLite数据库文件（自动生成） |
| `stock_history_data.xlsx` | Excel数据文件（中间文件） |
| `image_show/` | 生成的图表存储目录（自动生成） |

## ⚠️ 注意事项

1. **日期格式**: 数据库中 `trade_date` 为字符串 'YYYYMMDD' 格式，例如 '20240101'
2. **API 配额**: 受限于 DashScope API 的调用次数和速率限制
3. **字体支持**: 中文图表显示依赖系统字体（SimHei 或 Microsoft YaHei）
4. **文件占用**: 如果提示数据库文件被占用，请关闭其他使用该文件的程序
5. **SQL 安全**: 虽然由 LLM 生成 SQL，但已做基本防护，建议不要输入恶意内容

## 🐛 常见问题

### Q1: 提示 "DASHSCOPE_API_KEY not found"

**解决方案**: 确保已正确设置环境变量
```bash
# Windows
$env:DASHSCOPE_API_KEY="your-api-key-here"

# Linux/Mac
export DASHSCOPE_API_KEY="your-api-key-here"
```

### Q2: 中文显示乱码

**解决方案**: 确保系统安装了中文字体（SimHei 或 Microsoft YaHei）

### Q3: 找不到数据库文件

**解决方案**: 先运行数据导入脚本
```bash
python fetch_stock_history.py
python import_to_sqlite.py
```

### Q4: Web 界面无法访问

**解决方案**: 
1. 检查防火墙设置
2. 确认端口未被占用
3. 尝试使用终端模式 `app_tui()`

## 📝 更新日志

### v1.0.0 (2026-04-25)
- ✅ 初始版本发布
- ✅ 支持四只股票历史数据查询
- ✅ 自动可视化功能
- ✅ Web 和终端双模式
- ✅ 基于 SQLite 本地数据库

## 📞 技术支持

如有问题，请检查：
1. Python 版本 >= 3.8
2. 所有依赖包已正确安装
3. DASHSCOPE_API_KEY 已正确配置
4. 数据库文件存在且未被占用

---

**祝您使用愉快！** 🎉