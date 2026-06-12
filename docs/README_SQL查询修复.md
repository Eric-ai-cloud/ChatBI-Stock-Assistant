# 股票助手SQL查询修复说明

## 📋 问题汇总

### 问题1：字符串日期算术运算错误

当用户询问"贵州茅台最近一个月的股价"时，LLM生成的SQL为：

```sql
SELECT * FROM stock_history 
WHERE stock_code = '600519.SH' 
  AND trade_date >= (SELECT MAX(trade_date) - 30 FROM stock_history WHERE stock_code = '600519.SH') 
ORDER BY trade_date DESC;
```

**问题：** 只返回17条记录，而不是期望的30条记录。

**根本原因：** `trade_date` 是 **VARCHAR(10)** 类型，SQLite会将其转换为数字后运算，导致错误的日期比较。

---

### 问题2：最高价/最低价字段混淆

用户询问"最低价和最高价以及对应的日期"时，LLM使用 `close_price` 而非 `high_price`/`low_price`。

**错误结果：**
- 最低价: 1401.18元（实际是收盘价）
- 最高价: 1485元（实际也是收盘价）

**正确结果：**
- 最低价: 1392.0元，日期: 20260313
- 最高价: 1498.07元，日期: 20260317

---

### 问题3："最近一个月"理解偏差 ⭐ 新增

用户询问"贵州茅台最近一个月股价走势"时，LLM生成 `LIMIT 30`（30个交易日）。

**问题分析：**
- ❌ **30个交易日** ≈ 43个自然日（约1.4个月）← LLM的做法
- ✅ **30个自然日** ≈ 22个交易日 ← 用户期望的"最近一个月"

**测试结果：**
```
最新交易日期：20260424
30个交易日范围：20260313 至 20260424（43个自然日）❌
30个自然日范围：20260325 至 20260424（22个交易日）✅
```

---

### 问题4：极值查询返回重复类型 ⭐ 新增

用户询问"最低价和最高价以及对应的日期"时，LLM生成的SQL为：

```sql
WITH recent_data AS (SELECT * FROM stock_history WHERE stock_code = '600519.SH' ORDER BY trade_date DESC LIMIT 30)
SELECT trade_date, high_price AS price, 'high' AS price_type FROM recent_data 
UNION ALL 
SELECT trade_date, low_price AS price, 'low' AS price_type FROM recent_data 
ORDER BY price DESC, price_type ASC 
LIMIT 2
```

**问题：** 返回了两个最高价（1479.93和1477.41），没有最低价。

**根本原因：** `ORDER BY price DESC` 会优先返回高价记录，导致两个最高价被选中。

---

### 问题5：字符串日期算术运算未被检测 ⭐ 新增

用户提供的日志显示，LLM生成的SQL中仍然使用了字符串日期算术运算：

```sql
WHERE trade_date >= (SELECT MAX(trade_date) FROM stock_history WHERE stock_code = '600519.SH') - 30
```

**问题：** 
- SQLite将 `'20260424' - 30` 转换为 `20260394`（错误的日期）
- 查询范围错误，导致返回的最高价和最低价都不正确
- 结果：最高价1477.41、最低价1399.87（都是错误的）

**根本原因：** 
智能SQL预处理只检测了 `LIMIT 30` 模式，没有检测到子查询中的字符串日期算术运算。

---

## ✅ 修复方案

### 1. 更新 system_prompt（stock_assistant-1.py）

在系统提示中添加明确的规则：

```python
system_prompt = """
⚠️⚠️⚠️ 【极其重要】trade_date 是字符串类型，绝对不能进行算术运算！ ⚠️⚠️⚠️

重要提示：
1. trade_date 字段是字符串类型，格式为 'YYYYMMDD'（例如：'20240101'）
2. ❌ 严禁使用：WHERE trade_date >= MAX(trade_date) - 30 （字符串不能减法！）
3. ✅ 查询最近N天/月的正确写法：
   ```sql
   SELECT * FROM (
       SELECT trade_date, close_price 
       FROM stock_history 
       WHERE stock_code = '600519.SH' 
       ORDER BY trade_date DESC 
       LIMIT 30
   ) ORDER BY trade_date ASC
   ```
4. ⚠️ 区分价格字段：
   - **最高价**：使用 `high_price` 字段（当日最高成交价）
   - **最低价**：使用 `low_price` 字段（当日最低成交价）
   - **收盘价**：使用 `close_price` 字段（当日收盘价）
5. 📌 "最近一个月"自动转换：
   - 系统会自动检测 LIMIT 30 并转换为自然月30天
   - 从最新交易日期往前推30个自然日（不是30个交易日）
"""
```

### 2. 添加智能SQL预处理功能

在 [`ExcSQLTool`](file://d:\AI-LLM-P\25-项目实战：ChatBI开发实战\CASE-ChatBI助手\stock_assistant-1.py#L130-L230) 类中添加 `_preprocess_recent_month_sql` 方法：

```python
def _preprocess_recent_month_sql(self, sql_input: str) -> str:
    """
    智能预处理SQL：检测并修正"最近一个月"查询
    
    问题：LLM可能生成 LIMIT 30（30个交易日≈43天）
    解决：转换为自然月30天的查询
    """
    # 1. 检测是否包含 "ORDER BY trade_date DESC LIMIT 30"
    # 2. 提取股票代码
    # 3. 查询最新交易日期
    # 4. 计算30天前的日期（latest_date - timedelta(days=30)）
    # 5. 替换为具体日期范围查询
```

**工作流程：**
```
LLM生成SQL → 检测到LIMIT 30 → 查询最新日期 → 计算起始日期 → 替换SQL → 执行查询
```

### 3. 更新 faq.txt

在文件开头添加最高优先级规则，并新增Q1.5示例：

````
## ⚠️⚠️⚠️ 最高优先级规则 ⚠️⚠️⚠️

### 🚫 绝对禁止的SQL写法
- 对字符串日期进行算术运算
- 硬编码具体日期

### ✅ 必须使用的正确写法
- 相对时间：ORDER BY + LIMIT（系统会自动转换）
- 具体时间：WHERE trade_date >= 'YYYYMMDD'

### Q1.5: 查询最近一个月的股价走势
- "最近一个月"指自然月30天，不是30个交易日
- 系统会自动将 LIMIT 30 转换为具体日期范围
- 推荐在应用层计算日期后传入SQL
```

### 4. 新增Q4示例

添加"查询最高价和最低价"的完整示例，强调字段区分。

---

## 🧪 测试验证

### 测试1：相对时间查询

运行 `test_recent_month_query.py`：

```
✅ 正确的SQL查询：返回 30 条记录
📅 日期范围：20260313 至 20260424
✓ 日期是否升序排列：True
```

### 测试2：最高价/最低价查询

运行 `test_high_low_prices.py`：

```
📊 最高价分析：
  最高价: 1498.07 元，日期: 20260317
  
📊 最低价分析：
  最低价: 1392.0 元，日期: 20260313
```

### 测试3：智能SQL预处理 ⭐ 新增

运行 `test_sql_preprocessing.py`：

```
📝 测试用例1：标准子查询模式
原始SQL: LIMIT 30（30个交易日）
处理后SQL: WHERE trade_date >= '20260325'（自然月30天）
✅ 返回 22 条记录（31个自然日）

📝 测试用例2：多字段查询
✅ 返回 22 条记录（31个自然日）

📝 测试用例3：具体日期范围查询
✅ SQL未被修改（符合预期）
```

### 测试4：极值查询正确性 ⭐ 新增

运行 `test_high_low_correct.py`：

```
❌ 错误写法：UNION ALL后按价格排序取前2条
返回 2 条记录：两个都是最高价
⚠️  问题：没有最低价！

✅ 正确写法1：分别查询各用LIMIT 1
执行失败：SQLite不支持UNION ALL前后使用LIMIT

✅ 正确写法2：使用子查询
返回结果：一行中包含最高价和最低价的所有信息
✅ 成功！

✅ 正确写法3：先查完整数据，应用层计算（推荐）
返回 22 条记录
📊 最高价：1479.93 元，日期：20260331
📊 最低价：1396.66 元，日期：20260327
✅ 成功：应用层计算更灵活、更可靠！
```

### 测试5：字符串日期算术运算修正 ⭐ 新增

运行 `test_enhanced_sql_preprocessing.py`：

```
📝 测试用例1：字符串日期算术运算
原始SQL: WHERE trade_date >= (SELECT MAX(trade_date) ...) - 30
处理后SQL: WHERE trade_date >= '20260325'

返回结果：
| high_date | high_price | low_date | low_price |
|-----------|------------|----------|-----------|
| 20260331  | 1479.93    | 20260327 | 1396.66   |

✅ 测试结果正确！

修正前：最高价1477.41、最低价1399.87（错误）❌
修正后：最高价1479.93、最低价1396.66（正确）✅
```

---

## 📝 关键要点总结

### 1. 字符串日期不能进行算术运算
- SQLite会将 `'20260424' - 30` 转换为 `20260394`（无效日期）
- 必须使用 `ORDER BY + LIMIT` 或具体日期范围

### 2. 价格字段要区分清楚
- `high_price` ≠ `close_price` ≠ `low_price`
- 用户问"最高价/最低价"时，必须用对应的字段

### 3. "最近一个月"的正确理解 ⭐ 重点
- **自然月30天** ≠ **30个交易日**
- 30个交易日 ≈ 43个自然日（因为周末和节假日休市）
- 系统会自动检测并转换 `LIMIT 30` 为自然月30天查询

### 4. 智能SQL预处理机制
- 检测：正则匹配 `ORDER BY trade_date DESC LIMIT 30`
- 计算：在应用层获取最新日期，减去30天
- 替换：生成具体的日期范围查询
- 优势：无需修改LLM，在后端自动修正

### 5. FAQ优先原则
- 在faq.txt和system_prompt中都要明确禁止错误写法
- 提供具体的正确示例
- 解释为什么某些写法是错误的

### 6. 极值查询的正确方法 ⭐ 重点
- **禁止**：UNION ALL后统一排序取前N条（会返回重复类型）
- **禁止**：在UNION ALL的各个部分使用LIMIT（SQLite不支持）
- **推荐**：使用子查询，一行中包含所有信息
- **最推荐**：先查完整数据，在应用层计算极值（灵活可靠）

### 7. 智能SQL预处理的两种检测模式 ⭐ 重点

**模式1：LIMIT 30检测**
- 检测：`ORDER BY trade_date DESC LIMIT 30`
- 转换：30个交易日 → 自然月30天
- 替换：添加 `WHERE trade_date >= 'YYYYMMDD'`

**模式2：字符串日期算术运算检测（新增）**
- 检测：`trade_date >= (SELECT MAX(trade_date) ...) - 30`
- 转换：字符串减法 → 具体日期常量
- 替换：`trade_date >= 'YYYYMMDD'`

**优先级：**
- 模式2 > 模式1（先检测并修正算术运算）

### 8. 统一转换策略
- 所有相对时间查询最终都转换为具体日期常量
- 避免SQLite的隐式类型转换问题
- 提高SQL的可读性和可维护性

---

## 🎯 预期效果对比

### 修复前
```sql
-- ❌ 错误1：字符串算术运算，返回17条
WHERE trade_date >= (SELECT MAX(trade_date) - 30 ...)

-- ❌ 错误2：使用close_price找最高/最低价
SELECT MAX(close_price), MIN(close_price)

-- ❌ 错误3：30个交易日≈43天，超出预期
ORDER BY trade_date DESC LIMIT 30

-- ❌ 错误：返回两个最高价
SELECT ... UNION ALL SELECT ... ORDER BY price DESC LIMIT 2
-- 结果：1479.93 (high), 1477.41 (high)
```

### 修复后
```sql
-- ✅ 正确1：自动转换为自然月30天
WHERE trade_date >= '20260325'  -- 动态计算

-- ✅ 正确2：使用正确的字段
SELECT MAX(high_price), MIN(low_price)

-- ✅ 正确3：系统自动转换，返回22条（30个自然日）
LIMIT 30 → WHERE trade_date >= 'YYYYMMDD'

-- ✅ 正确：子查询方式
SELECT 
    (SELECT ... ORDER BY high_price DESC LIMIT 1) as high_date,
    (SELECT MAX(high_price) ...) as high_price,
    (SELECT ... ORDER BY low_price ASC LIMIT 1) as low_date,
    (SELECT MIN(low_price) ...) as low_price
-- 结果：high_date=20260331, high_price=1479.93, low_date=20260327, low_price=1396.66

-- ✅ 正确：应用层计算
SELECT trade_date, high_price, low_price FROM ...
# Python: df['high_price'].max(), df['low_price'].min()
-- 结果：灵活、可靠、易维护
```

---

## 🚀 下一步

请重新启动股票助手服务，新的配置将生效：

```bash
python stock_assistant-1.py
```

现在LLM会根据更新后的system_prompt和faq.txt生成SQL，并且系统会自动修正"最近一个月"的查询逻辑！🎉
