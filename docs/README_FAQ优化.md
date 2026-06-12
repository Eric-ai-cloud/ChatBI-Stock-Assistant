# FAQ 知识库优化说明

## 📋 问题背景

### 原始问题
用户提问："对比2025年中芯国际和贵州茅台的涨跌幅"

**AI 生成的 SQL（过于复杂）:**
```sql
-- 第一次尝试：复杂的 CTE + JOIN + LIMIT 偏移
WITH smic_data AS (...), moutai_data AS (...) 
SELECT ... FROM smic_data JOIN moutai_data ...
LIMIT 1, (SELECT COUNT(*)-1 FROM smic_data)

-- 第二次尝试：仍然复杂
WITH smic_data AS (...), moutai_data AS (...)
SELECT ... FROM smic_data, moutai_data
```

**问题分析:**
1. ❌ AI 试图用一条复杂 SQL 同时获取两只股票数据
2. ❌ 使用了不必要的 CTE（公用表表达式）
3. ❌ 使用了复杂的 JOIN 和 LIMIT 偏移
4. ❌ SQL 容易出错且难以维护

---

## ✨ 优化方案

### 1. 优化 FAQ 内容

#### 优化前（过于简单）
```
Q1：对比2000年股票A和股票B的涨跌幅
A1：
我需要先找到股票A在2000年第一天和最后一天的价格...
然后计算股票A的涨跌幅 = (最后一天价格 - 第一天价格) / 第一天价格 * 100%
```

**问题:** 
- 只说明了思路，没有给出具体 SQL 示例
- 没有告诉 AI "不要使用复杂JOIN"
- 缺乏最佳实践指导

#### 优化后（简洁实用）
```markdown
### Q2: 如何对比两只股票的涨跌幅？
**A2:** 分别查询每只股票的年初和年末价格，然后计算涨跌幅

**推荐做法：** 分别查询两只股票的数据，不要尝试用复杂JOIN一次性获取。

**示例：**
```sql
-- 先查中芯国际
SELECT MIN(trade_date) as start_date, MAX(trade_date) as end_date,
       FIRST_VALUE(open_price) OVER (ORDER BY trade_date) as start_open,
       FIRST_VALUE(close_price) OVER (ORDER BY trade_date DESC) as end_close
FROM stock_history 
WHERE stock_code = '688981.SH' 
  AND trade_date >= '20250101' 
  AND trade_date <= '20251231'
```
```

**优势:**
- ✅ 明确告诉 AI "分别查询，不要用复杂JOIN"
- ✅ 提供具体的 SQL 示例
- ✅ 展示正确的写法

---

### 2. FAQ 结构优化

新的 FAQ 包含以下部分：

#### 📌 常见问题示例（4个典型问题）
1. 查询单只股票收盘价
2. **对比两只股票涨跌幅** ⭐ 重点
3. 查询平均收盘价
4. 查询成交量最大的几天

#### 📌 SQL 编写关键提示
1. **日期格式**: `'YYYYMMDD'` 字符串格式
2. **字段说明**: 完整的字段列表和说明
3. **排序建议**: 务必使用 `ORDER BY trade_date`

#### 📌 数据范围说明
- 支持的股票列表（4只股票）
- 时间范围（2020-01-02 至今）
- 特殊说明（中芯国际从 2020-07-16 开始）

#### 📌 注意事项
1. **避免复杂JOIN** ⭐ 核心原则
2. 涨跌幅计算公式
3. 聚合函数使用
4. LIMIT 使用

#### 📌 最佳实践示例
- 场景1: 查询单只股票走势
- 场景2: 对比多只股票（分步查询）
- 场景3: 统计分析

---

## 🎯 预期效果

### 优化后的 AI 行为

当用户再次提问："对比2025年中芯国际和贵州茅台的涨跌幅"

**期望的 SQL 生成:**

```sql
-- 第一步：查询中芯国际
SELECT 
    MIN(trade_date) as start_date,
    MAX(trade_date) as end_date,
    FIRST_VALUE(open_price) OVER (ORDER BY trade_date) as start_open,
    FIRST_VALUE(close_price) OVER (ORDER BY trade_date DESC) as end_close
FROM stock_history 
WHERE stock_code = '688981.SH' 
  AND trade_date >= '20250101' 
  AND trade_date <= '20251231'

-- 第二步：查询贵州茅台（类似SQL）
SELECT ...
FROM stock_history 
WHERE stock_code = '600519.SH' 
  AND trade_date >= '20250101' 
  AND trade_date <= '20251231'
```

**或者更简单的写法:**
```sql
-- 中芯国际年初价格
SELECT open_price as start_price
FROM stock_history 
WHERE stock_code = '688981.SH' 
  AND trade_date >= '20250101'
ORDER BY trade_date ASC
LIMIT 1

-- 中芯国际年末价格
SELECT close_price as end_price
FROM stock_history 
WHERE stock_code = '688981.SH' 
  AND trade_date <= '20251231'
ORDER BY trade_date DESC
LIMIT 1

-- 贵州茅台类似查询...
```

---

## 💡 核心改进点

### 1. 明确指导原则
```markdown
**推荐做法：** 分别查询两只股票的数据，不要尝试用复杂JOIN一次性获取。
```

### 2. 提供正确示例
```sql
-- 清晰、简单的 SQL 示例
SELECT trade_date, close_price 
FROM stock_history 
WHERE stock_name = '贵州茅台' 
  AND trade_date >= '20240101' 
ORDER BY trade_date
```

### 3. 强调注意事项
```markdown
### 1. 避免复杂JOIN
- ❌ 不推荐：用 JOIN 连接多只股票的数据
- ✅ 推荐：分别查询每只股票，然后在回答时对比
```

### 4. 完整的数据说明
- 股票代码映射表
- 日期格式说明
- 字段含义解释

---

## 📊 对比总结

| 维度 | 优化前 | 优化后 |
|-----|-------|-------|
| FAQ 长度 | 11行（过于简单） | ~150行（全面但简洁） |
| SQL 示例 | ❌ 无 | ✅ 多个场景示例 |
| 最佳实践 | ❌ 无 | ✅ 明确指导原则 |
| 数据说明 | ❌ 无 | ✅ 完整说明 |
| AI 理解度 | 低（生成复杂SQL） | 高（生成简洁SQL） |

---

## 🚀 使用方法

FAQ 文件已在 [stock_assistant-1.py](file://d:\AI-LLM-P\25-项目实战：ChatBI开发实战\CASE-ChatBI助手\stock_assistant-1.py#L362) 中自动加载：

```python
bot = Assistant(
    llm=llm_cfg,
    name='股票查询助手',
    description='股票历史数据查询与分析',
    system_message=system_prompt,
    function_list=['exc_sql'],
    files=['faq.txt']  # ✅ 已加载
)
```

无需额外配置，重启助手即可生效！

---

## 📝 维护建议

### 何时更新 FAQ
1. 发现 AI 生成错误的 SQL 模式
2. 用户频繁询问某类问题
3. 新增股票或功能
4. 发现常见的误解或错误

### 更新原则
1. **保持简洁**: 每个问题控制在合理长度
2. **提供示例**: 给出具体的 SQL 代码
3. **明确指导**: 告诉 AI "应该怎么做"和"不应该怎么做"
4. **定期优化**: 根据实际使用情况调整

---

## ✅ 总结

本次优化通过改进 FAQ 知识库：
- ✅ 明确了"避免复杂JOIN"的原则
- ✅ 提供了多个实用的 SQL 示例
- ✅ 添加了完整的数据说明和最佳实践
- ✅ 保持简洁实用，不过度复杂

**预期效果**: AI 将生成更简洁、更可靠的 SQL 查询，提升用户体验！🎉