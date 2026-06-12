import os
import re
import asyncio
from typing import Optional
import dashscope
from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
import pandas as pd
from sqlalchemy import create_engine, text
from qwen_agent.tools.base import BaseTool, register_tool
import matplotlib.pyplot as plt
import io
import base64
import time
import numpy as np
from datetime import datetime, timedelta

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 配置 DashScope
dashscope.api_key = os.getenv('DASHSCOPE_API_KEY', '')
dashscope.timeout = 30

# ====== 股票助手 system prompt 和函数描述 ======
system_prompt = """我是股票查询助手，以下是关于股票历史数据表相关的字段，我可能会编写对应的SQL，对数据进行查询

-- 股票历史数据表
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

支持的股票列表：
- 贵州茅台 (600519.SH)
- 五粮液 (000858.SZ)
- 广发证券 (000776.SZ)
- 中芯国际 (688981.SH)

数据时间范围：2020-01-02 至今

⚠️⚠️⚠️ 【极其重要】trade_date 是字符串类型，绝对不能进行算术运算！ ⚠️⚠️⚠️

重要提示：
1. trade_date 字段是字符串类型，格式为 'YYYYMMDD'（例如：'20240101'）
2. ❌ 严禁使用：WHERE trade_date >= MAX(trade_date) - 30 （字符串不能减法！）
3. ❌ 严禁使用：WHERE trade_date >= (SELECT MAX(trade_date) - 30 ...) （这是错误的！）
4. ✅ 查询最近N天/月的正确写法：
   ```sql
   SELECT * FROM (
       SELECT trade_date, close_price 
       FROM stock_history 
       WHERE stock_code = '600519.SH' 
       ORDER BY trade_date DESC 
       LIMIT 30
   ) ORDER BY trade_date ASC
   ```
5. 查询具体日期范围时使用：WHERE trade_date >= '20240101' AND trade_date <= '20241231'
6. ⚠️ 区分价格字段：
   - **最高价**：使用 `high_price` 字段（当日最高成交价）
   - **最低价**：使用 `low_price` 字段（当日最低成交价）
   - **收盘价**：使用 `close_price` 字段（当日收盘价）
   - 用户问"最高价/最低价"时，必须用 high_price/low_price，不能用 close_price
   
7. ⚠️ 查询极值的正确方法：
   - ❌ 禁止：UNION ALL后按价格排序取前2条（会返回两个最高价）
   - ❌ 禁止：在UNION ALL的各个部分使用LIMIT（SQLite不支持）
   - ✅ 推荐：使用子查询，一行中包含所有信息
   - ✅ 推荐：先查完整数据，在应用层计算极值（最灵活可靠）
   - 示例：
     ```sql
     -- 方法1：子查询方式
     SELECT 
         (SELECT trade_date FROM stock_history WHERE ... ORDER BY high_price DESC LIMIT 1) as high_date,
         (SELECT MAX(high_price) FROM stock_history WHERE ...) as high_price,
         (SELECT trade_date FROM stock_history WHERE ... ORDER BY low_price ASC LIMIT 1) as low_date,
         (SELECT MIN(low_price) FROM stock_history WHERE ...) as low_price
     
     -- 方法2：应用层计算（推荐）
     SELECT trade_date, high_price, low_price FROM stock_history WHERE ...
     # 然后在Python中：df['high_price'].max(), df['low_price'].min()
     ```
8. 计算涨跌幅使用公式：(期末收盘价 - 期初收盘价) / 期初收盘价 * 100
9. 计算均线可以使用 AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN N PRECEDING AND CURRENT ROW)

📌 当用户询问"最近一个月"、"最近一周"、"近期走势"等相对时间时：
   - 系统会自动检测并转换：LIMIT 30 → 自然月30天
   - 如果LLM生成 LIMIT 30，工具会自动转换为具体日期范围查询
   - 也可以直接生成：WHERE trade_date >= 'YYYYMMDD'（需要在应用层计算日期）
   - 绝对不要对trade_date进行算术运算（如 MAX(trade_date) - 30）

我将回答用户关于股票价格、走势、统计分析等相关问题。

每当 exc_sql 工具返回 markdown 表格和图片时，你必须原样输出工具返回的全部内容（包括图片），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。
"""

functions_desc = [
    {
        "name": "exc_sql",
        "description": "对于生成的SQL，进行SQL查询",
        "parameters": {
            "type": "object",
            "properties": {
                "sql_input": {
                    "type": "string",
                    "description": "生成的SQL语句",
                }
            },
            "required": ["sql_input"],
        },
    },
]

# ====== 会话隔离 DataFrame 存储 ======
_last_df_dict = {}

def get_session_id(kwargs):
    """获取当前会话的唯一 session_id"""
    messages = kwargs.get('messages')
    return id(messages) if messages is not None else None

def get_db_engine():
    """获取数据库连接引擎（复用）"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    return create_engine(f'sqlite:///{db_path}')

# ====== exc_sql 工具类实现 ======
@register_tool('exc_sql')
class ExcSQLTool(BaseTool):
    """
    SQL查询工具，执行传入的SQL语句并返回结果，并自动进行可视化。
    """
    description = '对于生成的SQL，进行SQL查询，并自动可视化'
    parameters = [{
        'name': 'sql_input',
        'type': 'string',
        'description': '生成的SQL语句',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        import json

        # 获取session_id用于数据隔离
        session_id = get_session_id(kwargs)

        args = json.loads(params)
        sql_input = args['sql_input']
        print('原始sql_input=', sql_input)

        # 🆕 智能SQL预处理：检测并修正"最近一个月"查询
        sql_input = self._preprocess_recent_month_sql(sql_input)
        print('处理后sql_input=', sql_input)

        engine = get_db_engine()
        
        try:
            # 使用 SQLAlchemy 的 text() 包装 SQL 语句，避免格式化问题
            df = pd.read_sql(text(sql_input), engine)
            print(f'df shape: {df.shape}')
            print('df=', df.head())

            # 将DataFrame存储到会话中
            if session_id:
                _last_df_dict[session_id] = df

            # 构建综合数据预览信息
            md_parts = []
            
            # 1. 数据集基本信息
            md_parts.append(f"**数据概览**: 共 {len(df)} 行, {len(df.columns)} 列")
            md_parts.append(f"**字段列表**: {', '.join(df.columns.tolist())}\n")
            
            # 2. 前5行数据
            if len(df) > 0:
                md_parts.append("### 📋 前5行数据")
                head_df = df.head(5)
                md_parts.append(head_df.to_markdown(index=False))
                md_parts.append("")  # 空行分隔
            
            # 3. 后5行数据（如果数据量大于10）
            if len(df) > 10:
                md_parts.append("### 📋 后5行数据")
                tail_df = df.tail(5)
                md_parts.append(tail_df.to_markdown(index=False))
                md_parts.append("")  # 空行分隔
            
            # 4. 描述统计信息（仅对数值列）
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0 and len(df) > 1:
                md_parts.append("### 📊 数值列统计信息")
                desc_df = df[numeric_cols].describe()
                # 保留2位小数
                desc_df = desc_df.round(2)
                md_parts.append(desc_df.to_markdown())
                md_parts.append("")  # 空行分隔
                
                # 🔥 新增：显式标注极值信息，帮助LLM准确引用
                if 'trade_date' in df.columns:
                    extreme_info = self._extract_extreme_values(df, numeric_cols)
                    if extreme_info:
                        md_parts.append("### ⚠️ 关键极值点（请准确引用以下信息）")
                        md_parts.append(extreme_info)
                        md_parts.append("")
            
            # 合并所有部分
            md = '\n'.join(md_parts)
            
            # 如果只有一行数据，直接返回表格，不进行可视化
            if len(df) == 1:
                print('检测到单行数据，跳过可视化')
                return md
            
            # 多行数据才进行可视化
            # 自动创建目录
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'stock_chart_{int(time.time() * 1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            # 生成智能图表（根据数据量自动选择图表类型）
            generate_smart_chart_png(df, save_path)
            
            img_path = os.path.join('image_show', filename)
            img_md = f'![股票走势图]({img_path})'
            return f"{md}\n\n{img_md}"
        except Exception as e:
            error_msg = f"SQL执行错误: {str(e)}\n请检查SQL语句是否正确，确保字段名和表名正确。"
            print(error_msg)
            return error_msg

    def _preprocess_recent_month_sql(self, sql_input: str) -> str:
        """
        智能预处理SQL：检测并修正"最近一个月"查询
        
        问题1：LLM可能生成 LIMIT 30（30个交易日≈43天）
        问题2：LLM可能对字符串日期进行算术运算（MAX(trade_date) - 30）
        
        解决：转换为自然月30天的查询，使用具体日期常量
        """
        import re
        
        # 检测并修正字符串日期算术运算（最高优先级）
        arithmetic_pattern = r'trade_date\s*>=\s*\(?\s*SELECT\s+MAX\(trade_date\).*?\)?\s*-\s*\d+'
        
        if re.search(arithmetic_pattern, sql_input, re.IGNORECASE | re.DOTALL):
            print("⚠️ 检测到字符串日期算术运算，正在修正...")
            return self._fix_arithmetic_date(sql_input)
        
        # 检测是否包含 "ORDER BY trade_date DESC LIMIT 30" 模式
        pattern = r'ORDER\s+BY\s+trade_date\s+DESC\s+LIMIT\s+30'
        
        if not re.search(pattern, sql_input, re.IGNORECASE):
            return sql_input
        
        print("⚠️ 检测到'最近一个月'查询（LIMIT 30），正在转换...")
        return self._convert_limit_to_date_range(sql_input)

    def _fix_arithmetic_date(self, sql_input: str) -> str:
        """修正字符串日期算术运算"""
        stock_code_match = re.search(r"stock_code\s*=\s*['\"]([^'\"]+)['\"]", sql_input)
        if not stock_code_match:
            print("⚠️ 未找到股票代码，无法转换")
            return sql_input
        
        stock_code = stock_code_match.group(1)
        engine = get_db_engine()
        
        try:
            latest_date_sql = f"SELECT MAX(trade_date) as max_date FROM stock_history WHERE stock_code = '{stock_code}'"
            df_latest = pd.read_sql(text(latest_date_sql), engine)
            latest_date_str = df_latest['max_date'].iloc[0]
            
            if not latest_date_str:
                return sql_input
            
            latest_date = datetime.strptime(str(latest_date_str), '%Y%m%d')
            start_date = latest_date - timedelta(days=30)
            start_date_str = start_date.strftime('%Y%m%d')
            
            print(f"   最新日期: {latest_date_str}, 起始日期: {start_date_str}")
            
            # 替换所有出现的地方
            pattern1 = r"trade_date\s*>=\s*\(?\s*SELECT\s+MAX\(trade_date\)\s+FROM\s+stock_history\s+WHERE\s+stock_code\s*=\s*['\"][^'\"]+['\"]\s*\)?\s*-\s*\d+"
            new_sql = re.sub(pattern1, f"trade_date >= '{start_date_str}'", sql_input, flags=re.IGNORECASE | re.DOTALL)
            
            if new_sql == sql_input:
                pattern2 = r"trade_date\s*>=\s*\(?.*?MAX\(trade_date\).*?\)?\s*-\s*\d+"
                new_sql = re.sub(pattern2, f"trade_date >= '{start_date_str}'", sql_input, flags=re.IGNORECASE | re.DOTALL)
            
            print(f"   ✅ SQL已修正为具体日期范围查询")
            return new_sql
                
        except Exception as e:
            print(f"   ❌ SQL预处理失败: {str(e)}")
            return sql_input

    def _convert_limit_to_date_range(self, sql_input: str) -> str:
        """将LIMIT 30转换为具体日期范围"""
        stock_code_match = re.search(r"stock_code\s*=\s*['\"]([^'\"]+)['\"]", sql_input)
        if not stock_code_match:
            print("⚠️ 未找到股票代码，无法转换")
            return sql_input
        
        stock_code = stock_code_match.group(1)
        engine = get_db_engine()
        
        try:
            latest_date_sql = f"SELECT MAX(trade_date) as max_date FROM stock_history WHERE stock_code = '{stock_code}'"
            df_latest = pd.read_sql(text(latest_date_sql), engine)
            latest_date_str = df_latest['max_date'].iloc[0]
            
            if not latest_date_str:
                return sql_input
            
            latest_date = datetime.strptime(str(latest_date_str), '%Y%m%d')
            start_date = latest_date - timedelta(days=30)
            start_date_str = start_date.strftime('%Y%m%d')
            
            print(f"   最新日期: {latest_date_str}, 起始日期: {start_date_str}")
            
            # 匹配子查询模式
            subquery_pattern = r'FROM\s*\(\s*SELECT\s+(.*?)\s+FROM\s+stock_history\s+WHERE\s+stock_code\s*=\s*[\'"][^\'"]+[\'"]\s+ORDER\s+BY\s+trade_date\s+DESC\s+LIMIT\s+30\s*\)\s*ORDER\s+BY\s+trade_date\s+ASC'
            
            match = re.search(subquery_pattern, sql_input, re.IGNORECASE | re.DOTALL)
            if match:
                select_fields = match.group(1).strip()
                new_sql = f"""SELECT {select_fields} 
FROM stock_history 
WHERE stock_code = '{stock_code}' 
  AND trade_date >= '{start_date_str}'
ORDER BY trade_date ASC"""
                
                print(f"   ✅ SQL已修正为自然月30天查询")
                return new_sql
            else:
                # 备选方案：直接在WHERE中添加日期条件
                print("   ⚠️ 未匹配到标准子查询模式，使用备选方案")
                
                if 'WHERE' in sql_input.upper():
                    new_sql = re.sub(
                        r'(WHERE\s+stock_code\s*=\s*[\'"][^\'"]+[\'"])',
                        f"\\1 AND trade_date >= '{start_date_str}'",
                        sql_input,
                        flags=re.IGNORECASE
                    )
                    new_sql = re.sub(r'\s+LIMIT\s+30', '', new_sql, flags=re.IGNORECASE)
                    return new_sql
                
        except Exception as e:
            print(f"   ❌ SQL预处理失败: {str(e)}")
            return sql_input
        
        return sql_input
    
    def _extract_extreme_values(self, df: pd.DataFrame, numeric_cols: list) -> str:
        """提取并格式化极值信息，帮助LLM准确引用"""
        if 'trade_date' not in df.columns:
            return ""
        
        lines = []
        
        # 查找包含价格的列
        price_cols = [col for col in numeric_cols if 'price' in col.lower()]
        
        if price_cols:
            for col in price_cols:
                max_idx = df[col].idxmax()
                min_idx = df[col].idxmin()
                
                max_date = df.loc[max_idx, 'trade_date']
                max_val = df.loc[max_idx, col]
                min_date = df.loc[min_idx, 'trade_date']
                min_val = df.loc[min_idx, col]
                
                col_name_cn = {
                    'high_price': '最高价',
                    'low_price': '最低价',
                    'close_price': '收盘价',
                    'open_price': '开盘价'
                }.get(col, col)
                
                lines.append(f"- **{col_name_cn}最高值**: {max_val:.2f}元 (日期: {max_date})")
                lines.append(f"- **{col_name_cn}最低值**: {min_val:.2f}元 (日期: {min_date})")
        
        return '\n'.join(lines) if lines else ""


# ====== ARIMA股票预测工具 ======
@register_tool('arima_stock')
class ArimaStockTool(BaseTool):
    """
    ARIMA股票价格预测工具
    基于过去一年的历史数据，使用ARIMA(5,1,5)模型预测未来N天的股票收盘价
    """
    description = '使用ARIMA模型预测股票未来价格走势，基于过去一年的历史数据进行建模'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码（必填），如 600519.SH、000858.SZ',
        'required': True
    }, {
        'name': 'n',
        'type': 'integer',
        'description': '预测天数（可选，默认7天）',
        'required': False,
        'default': 7
    }]

    def call(self, params: str, **kwargs) -> str:
        import json
        from statsmodels.tsa.arima.model import ARIMA
        import warnings
        warnings.filterwarnings('ignore')

        # 解析参数
        args = json.loads(params)
        ts_code = args.get('ts_code')
        n_days = args.get('n', 7)

        if not ts_code:
            return "❌ 错误：股票代码(ts_code)是必填参数！"

        print(f"\n🔮 开始ARIMA预测: {ts_code}, 预测{n_days}天")

        engine = get_db_engine()
        
        try:
            # 计算一年前的日期
            today = datetime.now()
            one_year_ago = today - timedelta(days=365)
            start_date_str = one_year_ago.strftime('%Y%m%d')
            
            # 查询历史数据
            query_sql = f"""
            SELECT trade_date, close_price 
            FROM stock_history 
            WHERE stock_code = '{ts_code}' 
              AND trade_date >= '{start_date_str}'
            ORDER BY trade_date ASC
            """
            
            df_history = pd.read_sql(text(query_sql), engine)
            
            if len(df_history) == 0:
                return f"❌ 错误：未找到股票 {ts_code} 的历史数据！"
            
            print(f"   获取到 {len(df_history)} 条历史数据")
            
            # 准备时间序列数据
            df_history['trade_date_dt'] = pd.to_datetime(df_history['trade_date'], format='%Y%m%d')
            df_history.set_index('trade_date_dt', inplace=True)
            ts_data = df_history['close_price'].copy()
            
            print(f"   📊 时间序列数据点数: {len(ts_data)}")
            
            # 训练ARIMA模型 (5,1,5)
            print(f"   正在训练ARIMA(5,1,5)模型...")
            model = ARIMA(ts_data, order=(5, 1, 5))
            model_fit = model.fit()
            
            # 预测未来N天
            print(f"   正在预测未来{n_days}天的价格...")
            forecast_result = model_fit.get_forecast(steps=n_days)
            forecast_mean = forecast_result.predicted_mean
            forecast_ci = forecast_result.conf_int()
            
            # 生成预测日期（仅交易日，排除周末和法定节假日）
            last_date = ts_data.index[-1]
            forecast_dates = self._generate_trading_dates(last_date, n_days)
            
            print(f"   📅 预测日期范围: {forecast_dates[0].strftime('%Y-%m-%d')} 至 {forecast_dates[-1].strftime('%Y-%m-%d')}")
            
            # 构建预测结果DataFrame
            df_forecast = pd.DataFrame({
                'forecast_date': forecast_dates.strftime('%Y%m%d'),
                'predicted_price': forecast_mean.values,
                'lower_ci': forecast_ci.iloc[:, 0].values,
                'upper_ci': forecast_ci.iloc[:, 1].values
            })
            
            print(f"   ✅ 预测完成！价格范围: {df_forecast['predicted_price'].min():.2f} - {df_forecast['predicted_price'].max():.2f}")
            
            # 构建Markdown输出
            md_parts = []
            md_parts.append(f"## 📈 ARIMA股票价格预测结果")
            md_parts.append(f"**股票代码**: {ts_code}")
            md_parts.append(f"**预测天数**: {n_days}天")
            md_parts.append(f"**历史数据**: {len(ts_data)}条（过去一年）")
            md_parts.append(f"**模型**: ARIMA(5,1,5)\n")
            
            md_parts.append("### 🔮 预测结果")
            md_parts.append(df_forecast.to_markdown(index=False))
            md_parts.append("")
            
            # 生成可视化图表
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'arima_forecast_{ts_code.replace(".", "_")}_{int(time.time() * 1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            # 绘制综合预测图
            self._plot_arima_forecast(ts_data, forecast_dates, forecast_mean, forecast_ci, 
                                     n_days, save_path)
            
            img_path = os.path.join('image_show', filename)
            img_md = f'![ARIMA预测图]({img_path})'
            
            md_parts.append(img_md)
            md_parts.append("\n**说明**:")
            md_parts.append("- 蓝色线：历史收盘价（最近60天）")
            md_parts.append("- 紫色线：预测价格")
            md_parts.append("- 紫色阴影：95%置信区间")
            md_parts.append("- ⚠️ 预测仅供参考，不构成投资建议")
            
            return '\n'.join(md_parts)
            
        except Exception as e:
            error_msg = f"❌ ARIMA预测失败: {str(e)}\n请检查股票代码是否正确。"
            print(error_msg)
            return error_msg

    def _generate_trading_dates(self, last_date, n_days):
        """生成未来交易日（排除周末和常见节假日）"""
        forecast_dates = []
        current_date = last_date + pd.Timedelta(days=1)
        
        while len(forecast_dates) < n_days:
            weekday = current_date.weekday()
            
            # 跳过周末
            if weekday >= 5:
                current_date += pd.Timedelta(days=1)
                continue
            
            # 简单的节假日过滤
            month = current_date.month
            day = current_date.day
            
            is_holiday = False
            if month == 1 and day == 1:  # 元旦
                is_holiday = True
            elif month == 5 and day == 1:  # 劳动节
                is_holiday = True
            elif month == 10 and day <= 3:  # 国庆节
                is_holiday = True
            elif month == 2 and day <= 5:  # 春节（近似）
                is_holiday = True
            
            if not is_holiday:
                forecast_dates.append(current_date)
            
            current_date += pd.Timedelta(days=1)
        
        return pd.DatetimeIndex(forecast_dates)

    def _plot_arima_forecast(self, ts_data, forecast_dates, forecast_mean, forecast_ci, n_days, save_path):
        """绘制ARIMA预测图表"""
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # 绘制完整的历史数据
        ax.plot(ts_data.index, ts_data.values, 
               label='历史收盘价', color='#2E86AB', linewidth=1.5, alpha=0.7)
        
        # 突出显示最近60天
        recent_history = ts_data.tail(60)
        ax.plot(recent_history.index, recent_history.values, 
               color='#2E86AB', linewidth=2.5, marker='o', markersize=4, alpha=1.0)
        
        # 添加连接点实现连贯性
        last_history_date = recent_history.index[-1]
        last_history_price = recent_history.values[-1]
        
        connected_dates = [last_history_date] + list(forecast_dates)
        connected_prices = [last_history_price] + list(forecast_mean.values)
        
        # 绘制连贯的预测线
        ax.plot(connected_dates, connected_prices, 
               label='预测价格', color='#A23B72', linewidth=2.5, marker='s', markersize=6, linestyle='--')
        
        # 绘制置信区间
        connected_lower = [last_history_price] + list(forecast_ci.iloc[:, 0].values)
        connected_upper = [last_history_price] + list(forecast_ci.iloc[:, 1].values)
        ax.fill_between(connected_dates, 
                       connected_lower,
                       connected_upper,
                       alpha=0.15, color='#A23B72', label='95%置信区间')
        
        # 添加垂直分隔线
        ax.axvline(x=last_history_date, color='gray', linestyle=':', linewidth=1.5, alpha=0.5)
        
        # 设置标题和标签
        ax.set_title(f'{ts_data.name or "股票"} 价格预测 (ARIMA模型)\n历史{len(ts_data)}天 + 预测{n_days}个交易日', 
                    fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('交易日期', fontsize=13)
        ax.set_ylabel('收盘价 (元)', fontsize=13)
        ax.legend(loc='best', fontsize=11, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 格式化x轴日期
        import matplotlib.dates as mdates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.xticks(rotation=45, ha='right')
        
        # 添加文本标注
        ax.text(last_history_date, last_history_price * 1.02, 
               f'今天\n{last_history_date.strftime("%Y-%m-%d")}',
               ha='center', va='bottom', fontsize=9, 
               bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3))
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()


# ====== 布林带异常点检测工具 ======
@register_tool('boll_detection')
class BollDetectionTool(BaseTool):
    """
    布林带(Bollinger Bands)股票异常点检测工具
    基于20日移动平均线和2倍标准差，检测股票的超买和超卖点
    """
    description = '使用布林带模型检测股票的超买和超卖异常点，默认检测过去一年的数据'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码（必填），如 600519.SH、000858.SZ',
        'required': True
    }, {
        'name': 'start_date',
        'type': 'string',
        'description': '开始日期（可选，YYYYMMDD格式），默认为一年前',
        'required': False
    }, {
        'name': 'end_date',
        'type': 'string',
        'description': '结束日期（可选，YYYYMMDD格式），默认为今天',
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        import json
        import os
        import time

        # 解析参数
        args = json.loads(params)
        ts_code = args.get('ts_code')
        start_date = args.get('start_date', None)
        end_date = args.get('end_date', None)

        if not ts_code:
            return "❌ 错误：股票代码(ts_code)是必填参数！"

        print(f"\n📊 开始布林带异常点检测: {ts_code}")

        engine = get_db_engine()
        
        try:
            # 如果没有指定日期范围，默认检测过去一年
            if not start_date or not end_date:
                today = datetime.now()
                if not end_date:
                    end_date = today.strftime('%Y%m%d')
                if not start_date:
                    one_year_ago = today - timedelta(days=365)
                    start_date = one_year_ago.strftime('%Y%m%d')
                print(f"   检测范围: 默认过去一年 ({start_date} 至 {end_date})")
            else:
                print(f"   检测范围: {start_date} 至 {end_date}")
            
            # 查询历史数据
            query_sql = f"""
            SELECT trade_date, close_price 
            FROM stock_history 
            WHERE stock_code = '{ts_code}' 
              AND trade_date >= '{start_date}'
              AND trade_date <= '{end_date}'
            ORDER BY trade_date ASC
            """
            
            df_history = pd.read_sql(text(query_sql), engine)
            
            if len(df_history) == 0:
                return f"❌ 错误：未找到股票 {ts_code} 在指定时间范围内的历史数据！"
            
            print(f"   获取到 {len(df_history)} 条历史数据")
            
            # 准备数据
            df_history['trade_date_dt'] = pd.to_datetime(df_history['trade_date'], format='%Y%m%d')
            df_history.set_index('trade_date_dt', inplace=True)
            
            close_prices = df_history['close_price']
            
            # 计算布林带指标
            window = 20
            num_std = 2
            
            middle_band = close_prices.rolling(window=window).mean()
            std_dev = close_prices.rolling(window=window).std()
            upper_band = middle_band + (std_dev * num_std)
            lower_band = middle_band - (std_dev * num_std)
            
            # 检测异常点
            overbought = close_prices > upper_band
            oversold = close_prices < lower_band
            
            df_overbought = df_history[overbought].copy()
            df_oversold = df_history[oversold].copy()
            
            df_overbought['signal_type'] = '超买'
            df_oversold['signal_type'] = '超卖'
            
            df_anomalies = pd.concat([df_overbought, df_oversold], ignore_index=False)
            df_anomalies = df_anomalies.sort_index()
            
            print(f"   ✅ 检测完成！超买:{len(df_overbought)}, 超卖:{len(df_oversold)}, 总计:{len(df_anomalies)}")
            
            # 构建Markdown输出
            md_parts = []
            md_parts.append(f"## 📊 布林带异常点检测结果")
            md_parts.append(f"**股票代码**: {ts_code}")
            md_parts.append(f"**检测范围**: {start_date} 至 {end_date}")
            md_parts.append(f"**数据点数**: {len(df_history)}个交易日")
            md_parts.append(f"**布林带参数**: 20日周期 + 2σ\n")
            
            md_parts.append("### 📈 检测统计")
            md_parts.append(f"- **超买点**（收盘价突破上轨）: {len(df_overbought)} 个")
            md_parts.append(f"- **超卖点**（收盘价跌破下轨）: {len(df_oversold)} 个")
            md_parts.append(f"- **总异常点**: {len(df_anomalies)} 个\n")
            
            # 如果有异常点，显示详细信息
            if len(df_anomalies) > 0:
                md_parts.append("### 🔍 异常点详情")
                
                df_display = df_anomalies.reset_index()
                df_display.rename(columns={'trade_date_dt': '交易日期'}, inplace=True)
                df_display['交易日期'] = df_display['交易日期'].dt.strftime('%Y-%m-%d')
                
                display_cols = ['交易日期', 'close_price', 'signal_type']
                df_show = df_display[display_cols].rename(columns={
                    'close_price': '收盘价',
                    'signal_type': '信号类型'
                })
                
                md_parts.append(df_show.to_markdown(index=False))
                md_parts.append("")
            
            # 生成可视化图表
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'boll_detection_{ts_code.replace(".", "_")}_{int(time.time() * 1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            # 绘制布林带图
            self._plot_bollinger_bands(close_prices, middle_band, upper_band, lower_band,
                                      df_overbought, df_oversold, ts_code, start_date, end_date, save_path)
            
            img_path = os.path.join('image_show', filename)
            img_md = f'![布林带检测图]({img_path})'
            
            md_parts.append(img_md)
            md_parts.append("\n**说明**:")
            md_parts.append("- 蓝色线：收盘价")
            md_parts.append("- 红色线：中轨（20日移动平均线）")
            md_parts.append("- 橙色虚线：上轨和下轨（中轨 ± 2倍标准差）")
            md_parts.append("- 红色三角▲：超买点（收盘价突破上轨）")
            md_parts.append("- 绿色三角▼：超卖点（收盘价跌破下轨）")
            md_parts.append("- ⚠️ 检测结果仅供参考，不构成投资建议")
            
            return '\n'.join(md_parts)
            
        except Exception as e:
            error_msg = f"❌ 布林带检测失败: {str(e)}\n请检查股票代码是否正确。"
            print(error_msg)
            return error_msg

    def _plot_bollinger_bands(self, close_prices, middle_band, upper_band, lower_band,
                             df_overbought, df_oversold, ts_code, start_date, end_date, save_path):
        """绘制布林带图表"""
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # 绘制收盘价
        ax.plot(close_prices.index, close_prices.values, 
               label='收盘价', color='#2E86AB', linewidth=1.5)
        
        # 绘制布林带（移除NaN值）
        middle_band_valid = middle_band.dropna()
        ax.plot(middle_band_valid.index, middle_band_valid.values, 
               label='中轨(20日均线)', color='#FF6B6B', linewidth=2, linestyle='-')
        
        upper_band_valid = upper_band.dropna()
        lower_band_valid = lower_band.dropna()
        
        ax.plot(upper_band_valid.index, upper_band_valid.values, 
               label='上轨(中轨+2σ)', color='#FFA500', linewidth=1.5, linestyle='--')
        ax.plot(lower_band_valid.index, lower_band_valid.values, 
               label='下轨(中轨-2σ)', color='#FFA500', linewidth=1.5, linestyle='--')
        
        # 填充布林带区域
        ax.fill_between(upper_band_valid.index, upper_band_valid.values, lower_band_valid.values, 
                       alpha=0.1, color='#FFA500', label='布林带区间')
        
        # 标记异常点
        if len(df_overbought) > 0:
            ax.scatter(df_overbought.index, df_overbought['close_price'], 
                      color='red', marker='^', s=100, zorder=5, label='超买点')
        
        if len(df_oversold) > 0:
            ax.scatter(df_oversold.index, df_oversold['close_price'], 
                      color='green', marker='v', s=100, zorder=5, label='超卖点')
        
        # 设置标题和标签
        ax.set_title(f'{ts_code} 布林带异常点检测\n({start_date} 至 {end_date})', 
                    fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('交易日期', fontsize=13)
        ax.set_ylabel('价格 (元)', fontsize=13)
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 格式化x轴日期
        import matplotlib.dates as mdates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()


# ========== 智能可视化函数（优化版）========== 

def _plot_generic_chart(ax, df_sql, x_col, y_cols, use_line_chart, data_len):
    """绘制通用统计图表"""
    if use_line_chart:
        x = np.arange(len(df_sql))
        
        if len(df_sql) > 10:
            sample_indices = np.linspace(0, len(df_sql) - 1, 10, dtype=int)
            df_sampled = df_sql.iloc[sample_indices]
            x_sampled = np.arange(len(df_sampled))
            x_labels = [str(val).replace('%', '%%') for val in df_sampled[x_col]]
        else:
            df_sampled = df_sql
            x_sampled = x
            x_labels = [str(val).replace('%', '%%') for val in df_sql[x_col]]
        
        for y_col in y_cols[:3]:
            safe_label = str(y_col).replace('%', '%%')
            ax.plot(x_sampled, df_sampled[y_col], label=safe_label, linewidth=2, marker='o', markersize=5)
        
        plt.xticks(x_sampled, x_labels, rotation=45, ha='right')
        chart_type = "折线图"
    else:
        x = np.arange(len(df_sql))
        bottom = np.zeros(len(df_sql))
        
        for y_col in y_cols[:3]:
            safe_label = str(y_col).replace('%', '%%')
            ax.bar(x, df_sql[y_col], bottom=bottom, label=safe_label, alpha=0.8)
            bottom += df_sql[y_col]
        
        safe_xtick_labels = [str(val).replace('%', '%%') for val in df_sql[x_col]]
        plt.xticks(x, safe_xtick_labels, rotation=45, ha='right')
        chart_type = "柱状图"
    
    ax.set_title(f"数据统计 ({chart_type}, {data_len}条数据)", fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.set_xlabel(str(x_col))
    ax.set_ylabel("数值")


def generate_smart_chart_png(df_sql, save_path):
    """
    智能生成股票数据图表
    根据数据量自动选择图表类型：数据量<=20用柱状图，>20用折线图（采样至10个点）
    """
    columns = df_sql.columns.tolist()
    data_len = len(df_sql)
    
    has_date = 'trade_date' in columns or '交易日期' in columns
    has_close = 'close_price' in columns or '收盘价' in columns
    has_stock_name = 'stock_name' in columns or '股票名称' in columns
    
    fig, ax = plt.subplots(figsize=(12, 6))
    use_line_chart = data_len > 20
    
    if has_date and has_close:
        date_col = 'trade_date' if 'trade_date' in columns else '交易日期'
        close_col = 'close_price' if 'close_price' in columns else '收盘价'
        name_col = 'stock_name' if 'stock_name' in columns else '股票名称'
        
        if has_stock_name and df_sql[name_col].nunique() > 1:
            # 多只股票对比图
            for stock_name in df_sql[name_col].unique():
                stock_data = df_sql[df_sql[name_col] == stock_name].sort_values(by=date_col)
                
                if use_line_chart and len(stock_data) > 10:
                    sample_indices = np.linspace(0, len(stock_data) - 1, 10, dtype=int)
                    stock_data = stock_data.iloc[sample_indices]
                
                dates = [str(d)[:4] + '-' + str(d)[4:6] + '-' + str(d)[6:8] for d in stock_data[date_col]]
                ax.plot(dates, stock_data[close_col], label=stock_name, linewidth=2, 
                       marker='o' if use_line_chart else None, markersize=4)
            
            chart_type = "折线图" if use_line_chart else "柱状图"
            ax.set_title(f"多股票收盘价对比 ({chart_type}, {data_len}条数据)", fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.set_xlabel("交易日期")
            ax.set_ylabel("收盘价 (元)")
            plt.xticks(rotation=45)
        else:
            # 单只股票走势图
            stock_data = df_sql.sort_values(by=date_col)
            
            if use_line_chart and len(stock_data) > 10:
                sample_indices = np.linspace(0, len(stock_data) - 1, 10, dtype=int)
                stock_data_sampled = stock_data.iloc[sample_indices]
            else:
                stock_data_sampled = stock_data
            
            dates = [str(d)[:4] + '-' + str(d)[4:6] + '-' + str(d)[6:8] for d in stock_data_sampled[date_col]]
            
            if use_line_chart:
                ax.plot(dates, stock_data_sampled[close_col], color='#FF6B6B', linewidth=2, 
                       label='收盘价', marker='o', markersize=5)
                
                if 'open_price' in columns or '开盘价' in columns:
                    open_col = 'open_price' if 'open_price' in columns else '开盘价'
                    ax.plot(dates, stock_data_sampled[open_col], color='#4ECDC4', linewidth=1.5, 
                           label='开盘价', linestyle='--', marker='s', markersize=4)
            else:
                x = np.arange(len(stock_data_sampled))
                ax.bar(x, stock_data_sampled[close_col], color='#FF6B6B', alpha=0.7, label='收盘价')
                
                if 'open_price' in columns or '开盘价' in columns:
                    open_col = 'open_price' if 'open_price' in columns else '开盘价'
                    ax.bar(x + 0.35, stock_data_sampled[open_col], width=0.35, color='#4ECDC4', alpha=0.7, label='开盘价')
                    plt.xticks(x + 0.175, dates, rotation=45, ha='right')
                else:
                    plt.xticks(x, dates, rotation=45, ha='right')
            
            stock_name_display = stock_data[name_col].iloc[0] if has_stock_name else '股票'
            chart_type = "折线图" if use_line_chart else "柱状图"
            ax.set_title(f"{stock_name_display}价格走势 ({chart_type}, {data_len}条数据)", 
                        fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.set_xlabel("交易日期")
            ax.set_ylabel("价格 (元)")
            if use_line_chart:
                plt.xticks(rotation=45)
    else:
        # 通用统计图
        if len(columns) >= 2:
            x_col = columns[0]
            y_cols = [col for col in columns[1:] if df_sql[col].dtype in ['float64', 'int64']]
            
            if y_cols:
                _plot_generic_chart(ax, df_sql, x_col, y_cols, use_line_chart, data_len)
            else:
                ax.text(0.5, 0.5, '无可视化数据', ha='center', va='center', fontsize=16)
        else:
            ax.text(0.5, 0.5, '数据不足以生成图表', ha='center', va='center', fontsize=16)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


# ====== 初始化股票助手服务 ======
def init_agent_service():
    """初始化股票助手服务"""
    llm_cfg = {
        'model': 'qwen-max',
        'model_server': 'dashscope',
        'timeout': 30,
        'retry_count': 3,
    }
    function_list=['exc_sql', 'arima_stock', 'boll_detection',
                            {
                            "mcpServers": {
                                "tavily-mcp": {
                                "args": [
                                    "-y",
                                    "tavily-mcp@0.1.4"
                                ],
                                "autoApprove": [],
                                "command": "npx",
                                "env": {
                                    "TAVILY_API_KEY":os.getenv('TAVILY_API_KEY', '')    
                                }
                                }
                            }
                            }                  
    ]
    try:
        bot = Assistant(
            llm=llm_cfg,
            name='股票查询助手',
            description='股票历史数据查询与分析',
            system_message=system_prompt,
            function_list=function_list,
            files=['../data/faq.txt']
        )
        print("✓ 股票助手初始化成功！")
        return bot
    except Exception as e:
        print(f"✗ 助手初始化失败: {str(e)}")
        raise


def app_tui():
    """终端交互模式
    
    提供命令行交互界面，支持：
    - 连续对话
    - 文件输入
    - 实时响应
    """
    try:
        # 初始化助手
        bot = init_agent_service()

        # 对话历史
        messages = []
        print("\n" + "="*70)
        print("欢迎使用股票查询助手！")
        print("="*70)
        print("示例问题：")
        print("  1. 贵州茅台最近30天的收盘价走势")
        print("  2. 四只股票2024年的平均收盘价对比")
        print("  3. 五粮液成交量最大的10天")
        print("="*70 + "\n")
        
        while True:
            try:
                # 获取用户输入
                query = input('\n请输入您的问题: ')
                
                # 输入验证
                if not query:
                    print('问题不能为空！')
                    continue
                
                if query.lower() in ['quit', 'exit', '退出']:
                    print("感谢使用，再见！")
                    break
                    
                # 构建消息
                messages.append({'role': 'user', 'content': query})

                print("\n🤖 正在分析您的问题...")
                # 运行助手并处理响应
                response = []
                for response in bot.run(messages):
                    pass  # 流式响应，最后会返回完整结果
                
                if response:
                    print("\n" + "-"*70)
                    print(response[-1]['content'])
                    print("-"*70 + "\n")
                
                messages.extend(response)
            except KeyboardInterrupt:
                print("\n\n感谢使用，再见！")
                break
            except Exception as e:
                print(f"\n✗ 处理请求时出错: {str(e)}")
                print("请重试或输入新的问题\n")
    except Exception as e:
        print(f"✗ 启动终端模式失败: {str(e)}")


def app_gui():
    """图形界面模式，提供 Web 图形界面"""
    try:
        print("\n正在启动 Web 界面...")
        # 初始化助手
        bot = init_agent_service()
        
        # 配置聊天界面，列举典型股票查询问题
        chatbot_config = {
            'prompt.suggestions': [
                '查询2025年全年贵州茅台的收盘价走势',
                '统计2025年4月广发证券的日均成交量',
                '对比2025年中芯国际和贵州茅台的涨跌幅',
                '查询2025年的贵州茅台的布林带超买超卖点'
            ]
        }
        
        print("✓ Web 界面准备就绪")
        print("正在启动服务，请稍候...\n")
        
        # 启动 Web 界面
        WebUI(
            bot,
            chatbot_config=chatbot_config
        ).run()
    except Exception as e:
        print(f"✗ 启动 Web 界面失败: {str(e)}")
        print("请检查网络连接和 DASHSCOPE_API_KEY 配置")


if __name__ == '__main__':
    # 运行模式选择
    app_gui()          # 图形界面模式（默认）
    # app_tui()        # 如需终端模式，注释上一行，取消注释此行