"""
测试修复后的"最近一个月股价走势"查询
验证使用子查询 + LIMIT 的正确性
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os

def test_recent_month_query():
    """测试最近一个月的股价走势查询"""
    
    # 连接数据库
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    print("="*70)
    print("测试：贵州茅台最近30个交易日的股价走势")
    print("="*70)
    
    # ✅ 正确的SQL写法
    correct_sql = """
    SELECT * FROM (
        SELECT trade_date, open_price, high_price, low_price, close_price 
        FROM stock_history 
        WHERE stock_code = '600519.SH' 
        ORDER BY trade_date DESC 
        LIMIT 30
    ) ORDER BY trade_date ASC
    """
    
    print("\n✅ 正确的SQL查询：")
    print(correct_sql)
    
    try:
        df = pd.read_sql(text(correct_sql), engine)
        print(f"\n✓ 查询成功！返回 {len(df)} 条记录")
        print(f"\n📊 数据预览：")
        print(df.head(10))
        print(f"\n📊 数据尾部：")
        print(df.tail(5))
        
        # 验证日期顺序
        dates = df['trade_date'].tolist()
        print(f"\n📅 日期范围：{dates[0]} 至 {dates[-1]}")
        
        # 检查是否按升序排列
        is_ascending = all(dates[i] <= dates[i+1] for i in range(len(dates)-1))
        print(f"✓ 日期是否升序排列：{is_ascending}")
        
        if is_ascending:
            print("\n✅ 测试通过！日期按升序排列，适合可视化展示")
        else:
            print("\n❌ 测试失败！日期未按升序排列")
            
    except Exception as e:
        print(f"\n❌ 查询失败：{str(e)}")
    
    print("\n" + "="*70)
    
    # ❌ 错误的SQL写法（对比）
    wrong_sql = """
    SELECT trade_date, open_price, high_price, low_price, close_price 
    FROM stock_history 
    WHERE stock_code = '600519.SH' 
      AND trade_date >= (SELECT MAX(trade_date) - 30 FROM stock_history WHERE stock_code = '600519.SH')
    ORDER BY trade_date
    """
    
    print("\n❌ 错误的SQL查询（对字符串日期进行算术运算）：")
    print(wrong_sql)
    
    try:
        df_wrong = pd.read_sql(text(wrong_sql), engine)
        print(f"\n⚠️  意外成功：返回 {len(df_wrong)} 条记录")
        print("注意：虽然SQLite可能执行了这个查询，但结果不正确！")
        print("因为 '20240101' - 30 不等于期望的日期计算")
    except Exception as e:
        print(f"\n✓ 预期错误：{str(e)}")
        print("这个错误提醒我们不能对字符串日期进行算术运算")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    test_recent_month_query()
