"""
测试：验证"最近一个月"的正确理解
对比30个交易日 vs 30个自然日的差异
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import datetime, timedelta

def test_recent_month_definition():
    """测试最近一个月的定义"""
    
    # 连接数据库
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    print("="*70)
    print("测试：'最近一个月'的正确定义")
    print("="*70)
    
    # 方法1：获取最新交易日期
    latest_date_sql = """
    SELECT MAX(trade_date) as max_date 
    FROM stock_history 
    WHERE stock_code = '600519.SH'
    """
    
    df_latest = pd.read_sql(text(latest_date_sql), engine)
    latest_date_str = df_latest['max_date'].iloc[0]
    print(f"\n📅 最新交易日期：{latest_date_str}")
    
    # 转换为datetime对象
    latest_date = datetime.strptime(latest_date_str, '%Y%m%d')
    one_month_ago = latest_date - timedelta(days=30)
    one_month_ago_str = one_month_ago.strftime('%Y%m%d')
    
    print(f"📅 30天前的日期：{one_month_ago_str}")
    print(f"   （自然月30天）")
    
    # 方法2：查询最近30个自然日的数据
    natural_month_sql = f"""
    SELECT trade_date, close_price, high_price, low_price
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date >= '{one_month_ago_str}'
    ORDER BY trade_date ASC
    """
    
    print(f"\n✅ 方法1：按自然月30天查询")
    print(f"SQL: WHERE trade_date >= '{one_month_ago_str}'")
    
    df_natural = pd.read_sql(text(natural_month_sql), engine)
    print(f"返回 {len(df_natural)} 条记录")
    if len(df_natural) > 0:
        print(f"日期范围：{df_natural['trade_date'].iloc[0]} 至 {df_natural['trade_date'].iloc[-1]}")
        
        # 计算实际天数
        start_date = datetime.strptime(df_natural['trade_date'].iloc[0], '%Y%m%d')
        end_date = datetime.strptime(df_natural['trade_date'].iloc[-1], '%Y%m%d')
        actual_days = (end_date - start_date).days + 1
        print(f"实际跨越：{actual_days} 个自然日")
    
    # 方法3：查询最近30个交易日（当前LLM的做法）
    trading_days_sql = """
    SELECT * FROM (
        SELECT trade_date, close_price 
        FROM stock_history 
        WHERE stock_code = '600519.SH' 
        ORDER BY trade_date DESC 
        LIMIT 30
    ) ORDER BY trade_date ASC
    """
    
    print(f"\n❌ 方法2：按30个交易日查询（当前LLM做法）")
    df_trading = pd.read_sql(text(trading_days_sql), engine)
    print(f"返回 {len(df_trading)} 条记录")
    if len(df_trading) > 0:
        print(f"日期范围：{df_trading['trade_date'].iloc[0]} 至 {df_trading['trade_date'].iloc[-1]}")
        
        # 计算实际天数
        start_date = datetime.strptime(df_trading['trade_date'].iloc[0], '%Y%m%d')
        end_date = datetime.strptime(df_trading['trade_date'].iloc[-1], '%Y%m%d')
        actual_days = (end_date - start_date).days + 1
        print(f"实际跨越：{actual_days} 个自然日")
        print(f"⚠️  注意：30个交易日 ≈ {actual_days} 个自然日（约{actual_days/30:.1f}个月）")
    
    print("\n" + "="*70)
    print("结论：")
    print("="*70)
    print("1. '最近一个月'通常指自然月30天，而非30个交易日")
    print("2. 30个交易日可能跨越40-45个自然日（因为周末和节假日休市）")
    print("3. 正确做法：先查最新日期，再减去30天作为起始日期")
    print("="*70)
    
    print("\n✅ 推荐的SQL写法：")
    print("""
    -- 步骤1：在应用层计算起始日期（推荐）
    latest_date = get_latest_trade_date()  # 如 '20260424'
    start_date = calculate_date_minus_days(latest_date, 30)  # 如 '20260325'
    
    -- 步骤2：使用具体日期查询
    SELECT trade_date, close_price 
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date >= '20260325'  -- 动态计算的起始日期
    ORDER BY trade_date ASC
    
    -- 或者使用子查询方式（如果必须在SQL中处理）
    SELECT trade_date, close_price 
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date >= (
          SELECT DATE(MAX(trade_date), '-30 days') 
          FROM stock_history 
          WHERE stock_code = '600519.SH'
      )
    ORDER BY trade_date ASC
    """)


if __name__ == '__main__':
    test_recent_month_definition()
