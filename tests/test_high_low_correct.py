"""
测试：验证最高价和最低价查询的正确SQL写法
对比错误写法和正确写法的执行结果
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import datetime, timedelta

def test_high_low_price_queries():
    """测试最高价和最低价查询的不同SQL写法"""
    
    # 连接数据库
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    print("="*70)
    print("测试：最高价和最低价查询的正确SQL写法")
    print("="*70)
    
    # 计算起始日期（最近30天）
    latest_date_sql = "SELECT MAX(trade_date) as max_date FROM stock_history WHERE stock_code = '600519.SH'"
    df_latest = pd.read_sql(text(latest_date_sql), engine)
    latest_date_str = df_latest['max_date'].iloc[0]
    latest_date = datetime.strptime(latest_date_str, '%Y%m%d')
    start_date = latest_date - timedelta(days=30)
    start_date_str = start_date.strftime('%Y%m%d')
    
    print(f"\n📅 查询范围：{start_date_str} 至 {latest_date_str}")
    print(f"   （最近30个自然日）\n")
    
    # ❌ 错误写法：UNION ALL后按价格排序取前2条
    wrong_sql = f"""
    WITH recent_data AS (
        SELECT * FROM stock_history 
        WHERE stock_code = '600519.SH' 
          AND trade_date >= '{start_date_str}'
        ORDER BY trade_date DESC
    )
    SELECT trade_date, high_price AS price, 'high' AS price_type 
    FROM recent_data 
    UNION ALL 
    SELECT trade_date, low_price AS price, 'low' AS price_type 
    FROM recent_data 
    ORDER BY price DESC, price_type ASC 
    LIMIT 2
    """
    
    print("❌ 错误写法：UNION ALL后按价格排序取前2条")
    print(wrong_sql)
    
    try:
        df_wrong = pd.read_sql(text(wrong_sql), engine)
        print(f"\n返回 {len(df_wrong)} 条记录：")
        print(df_wrong.to_markdown(index=False))
        
        if len(df_wrong) == 2 and df_wrong['price_type'].unique().tolist() == ['high']:
            print("\n⚠️  问题：返回了两个最高价，没有最低价！")
            print("   原因：ORDER BY price DESC 会优先返回高价记录")
    except Exception as e:
        print(f"执行失败：{str(e)}")
    
    # ✅ 正确写法1：分别查询，各用LIMIT 1
    correct_sql_1 = f"""
    SELECT '最高价' as type, trade_date, high_price as price
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date >= '{start_date_str}'
      AND high_price = (
          SELECT MAX(high_price) 
          FROM stock_history 
          WHERE stock_code = '600519.SH' 
            AND trade_date >= '{start_date_str}'
      )
    LIMIT 1
    
    UNION ALL
    
    SELECT '最低价' as type, trade_date, low_price as price
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date >= '{start_date_str}'
      AND low_price = (
          SELECT MIN(low_price) 
          FROM stock_history 
          WHERE stock_code = '600519.SH' 
            AND trade_date >= '{start_date_str}'
      )
    LIMIT 1
    """
    
    print("\n" + "="*70)
    print("\n✅ 正确写法1：分别查询，各用LIMIT 1")
    print(correct_sql_1)
    
    try:
        df_correct_1 = pd.read_sql(text(correct_sql_1), engine)
        print(f"\n返回 {len(df_correct_1)} 条记录：")
        print(df_correct_1.to_markdown(index=False))
        
        if len(df_correct_1) == 2:
            types = df_correct_1['type'].unique().tolist()
            if '最高价' in types and '最低价' in types:
                print("\n✅ 成功：返回了一个最高价和一个最低价！")
    except Exception as e:
        print(f"执行失败：{str(e)}")
    
    # ✅ 正确写法2：使用子查询
    correct_sql_2 = f"""
    SELECT 
        (SELECT trade_date FROM stock_history 
         WHERE stock_code = '600519.SH' 
           AND trade_date >= '{start_date_str}'
         ORDER BY high_price DESC 
         LIMIT 1) as high_price_date,
        (SELECT MAX(high_price) FROM stock_history 
         WHERE stock_code = '600519.SH' 
           AND trade_date >= '{start_date_str}') as high_price,
        (SELECT trade_date FROM stock_history 
         WHERE stock_code = '600519.SH' 
           AND trade_date >= '{start_date_str}'
         ORDER BY low_price ASC 
         LIMIT 1) as low_price_date,
        (SELECT MIN(low_price) FROM stock_history 
         WHERE stock_code = '600519.SH' 
           AND trade_date >= '{start_date_str}') as low_price
    """
    
    print("\n" + "="*70)
    print("\n✅ 正确写法2：使用子查询")
    print(correct_sql_2)
    
    try:
        df_correct_2 = pd.read_sql(text(correct_sql_2), engine)
        print(f"\n返回结果：")
        print(df_correct_2.to_markdown(index=False))
        print("\n✅ 成功：一行中包含所有信息！")
    except Exception as e:
        print(f"执行失败：{str(e)}")
    
    # ✅ 正确写法3：先查完整数据，在应用层计算
    correct_sql_3 = f"""
    SELECT trade_date, high_price, low_price, close_price
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date >= '{start_date_str}'
    ORDER BY trade_date ASC
    """
    
    print("\n" + "="*70)
    print("\n✅ 正确写法3：先查完整数据，在应用层计算（推荐）")
    print(correct_sql_3)
    
    try:
        df_correct_3 = pd.read_sql(text(correct_sql_3), engine)
        print(f"\n返回 {len(df_correct_3)} 条记录")
        
        # 在应用层计算极值
        max_high_idx = df_correct_3['high_price'].idxmax()
        min_low_idx = df_correct_3['low_price'].idxmin()
        
        max_high_row = df_correct_3.loc[max_high_idx]
        min_low_row = df_correct_3.loc[min_low_idx]
        
        print(f"\n📊 最高价：{max_high_row['high_price']} 元，日期：{max_high_row['trade_date']}")
        print(f"📊 最低价：{min_low_row['low_price']} 元，日期：{min_low_row['trade_date']}")
        print("\n✅ 成功：应用层计算更灵活、更可靠！")
    except Exception as e:
        print(f"执行失败：{str(e)}")
    
    print("\n" + "="*70)
    print("总结：")
    print("="*70)
    print("1. ❌ 禁止：UNION ALL后统一排序取前N条（会返回重复类型）")
    print("2. ✅ 推荐：分别查询最高价和最低价，各用LIMIT 1")
    print("3. ✅ 推荐：先查完整数据，在应用层计算极值（最灵活）")
    print("4. ✅ 关键：确保每个极值只返回一条记录")
    print("="*70)


if __name__ == '__main__':
    test_high_low_price_queries()
