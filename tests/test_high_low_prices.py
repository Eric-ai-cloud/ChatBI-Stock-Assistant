"""
测试：验证贵州茅台最近30天的最高价和最低价
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os

def test_high_low_prices():
    """测试最高价和最低价查询"""
    
    # 连接数据库
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    print("="*70)
    print("测试：贵州茅台最近30个交易日的最高价和最低价")
    print("="*70)
    
    # ✅ 正确的SQL：先获取最近30天数据，再找最高/最低价
    correct_sql = """
    SELECT * FROM (
        SELECT trade_date, high_price, low_price, close_price
        FROM stock_history 
        WHERE stock_code = '600519.SH' 
        ORDER BY trade_date DESC 
        LIMIT 30
    ) ORDER BY trade_date ASC
    """
    
    print("\n✅ 步骤1：获取最近30天的完整数据")
    df = pd.read_sql(text(correct_sql), engine)
    print(f"返回 {len(df)} 条记录")
    print(f"\n日期范围：{df['trade_date'].iloc[0]} 至 {df['trade_date'].iloc[-1]}")
    
    # 找到最高价和最低价
    max_high_idx = df['high_price'].idxmax()
    min_low_idx = df['low_price'].idxmin()
    
    max_high_row = df.loc[max_high_idx]
    min_low_row = df.loc[min_low_idx]
    
    print(f"\n📊 最高价分析：")
    print(f"  最高价: {max_high_row['high_price']} 元")
    print(f"  日期: {max_high_row['trade_date']}")
    print(f"  收盘价: {max_high_row['close_price']} 元")
    
    print(f"\n📊 最低价分析：")
    print(f"  最低价: {min_low_row['low_price']} 元")
    print(f"  日期: {min_low_row['trade_date']}")
    print(f"  收盘价: {min_low_row['close_price']} 元")
    
    # ❌ LLM生成的错误SQL
    wrong_sql = """
    SELECT trade_date, close_price 
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND (close_price = (SELECT MAX(close_price) FROM stock_history WHERE stock_code = '600519.SH' ORDER BY trade_date DESC LIMIT 30) 
           OR close_price = (SELECT MIN(close_price) FROM stock_history WHERE stock_code = '600519.SH' ORDER BY trade_date DESC LIMIT 30)) 
    ORDER BY close_price ASC, trade_date ASC
    """
    
    print("\n" + "="*70)
    print("❌ LLM生成的错误SQL分析：")
    print("="*70)
    print("\n错误1：使用 close_price 而不是 high_price/low_price")
    print("错误2：子查询中的 ORDER BY LIMIT 位置错误")
    print("错误3：应该先筛选最近30天，再在其中找最高/最低")
    
    try:
        df_wrong = pd.read_sql(text(wrong_sql), engine)
        print(f"\n错误SQL返回 {len(df_wrong)} 条记录：")
        print(df_wrong)
    except Exception as e:
        print(f"错误SQL执行失败：{str(e)}")
    
    print("\n" + "="*70)
    print("✅ 正确的SQL写法：")
    print("="*70)
    
    # 方法1：分步查询（推荐）
    method1_sql = """
    -- 步骤1：获取最近30天数据
    WITH recent_30_days AS (
        SELECT trade_date, high_price, low_price, close_price
        FROM stock_history 
        WHERE stock_code = '600519.SH' 
        ORDER BY trade_date DESC 
        LIMIT 30
    )
    -- 步骤2：分别查询最高价和最低价
    SELECT '最高价' as type, trade_date, high_price as price
    FROM recent_30_days 
    WHERE high_price = (SELECT MAX(high_price) FROM recent_30_days)
    UNION ALL
    SELECT '最低价' as type, trade_date, low_price as price
    FROM recent_30_days 
    WHERE low_price = (SELECT MIN(low_price) FROM recent_30_days)
    ORDER BY type
    """
    
    print("\n方法1：使用CTE（公共表表达式）")
    try:
        df_method1 = pd.read_sql(text(method1_sql), engine)
        print(df_method1.to_markdown(index=False))
    except Exception as e:
        print(f"SQLite可能不支持WITH，尝试方法2")
    
    # 方法2：子查询方式
    method2_sql = """
    SELECT '最高价' as type, trade_date, high_price as price
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date IN (
          SELECT trade_date FROM (
              SELECT trade_date FROM stock_history 
              WHERE stock_code = '600519.SH' 
              ORDER BY trade_date DESC 
              LIMIT 30
          )
      )
      AND high_price = (
          SELECT MAX(high_price) FROM (
              SELECT high_price FROM stock_history 
              WHERE stock_code = '600519.SH' 
              ORDER BY trade_date DESC 
              LIMIT 30
          )
      )
    UNION ALL
    SELECT '最低价' as type, trade_date, low_price as price
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date IN (
          SELECT trade_date FROM (
              SELECT trade_date FROM stock_history 
              WHERE stock_code = '600519.SH' 
              ORDER BY trade_date DESC 
              LIMIT 30
          )
      )
      AND low_price = (
          SELECT MIN(low_price) FROM (
              SELECT low_price FROM stock_history 
              WHERE stock_code = '600519.SH' 
              ORDER BY trade_date DESC 
              LIMIT 30
          )
      )
    ORDER BY type
    """
    
    print("\n方法2：使用子查询")
    try:
        df_method2 = pd.read_sql(text(method2_sql), engine)
        print(df_method2.to_markdown(index=False))
    except Exception as e:
        print(f"执行失败：{str(e)}")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    test_high_low_prices()
