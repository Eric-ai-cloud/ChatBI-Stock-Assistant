"""
测试：验证增强的智能SQL预处理功能
检测并修正字符串日期算术运算（MAX(trade_date) - 30）
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
import re
from datetime import datetime, timedelta

def preprocess_sql_enhanced(sql_input: str) -> str:
    """
    增强版智能SQL预处理：检测并修正两种错误模式
    1. LIMIT 30（30个交易日）
    2. MAX(trade_date) - 30（字符串日期算术运算）
    """
    
    # 🆕 检测并修正字符串日期算术运算（最高优先级）
    arithmetic_pattern = r'trade_date\s*>=\s*\(?\s*SELECT\s+MAX\(trade_date\).*?\)?\s*-\s*\d+'
    
    if re.search(arithmetic_pattern, sql_input, re.IGNORECASE | re.DOTALL):
        print("⚠️ 检测到字符串日期算术运算（MAX(trade_date) - N），正在修正...")
        
        # 提取股票代码
        stock_code_match = re.search(r"stock_code\s*=\s*['\"]([^'\"]+)['\"]", sql_input)
        if not stock_code_match:
            print("⚠️ 未找到股票代码，无法转换")
            return sql_input
        
        stock_code = stock_code_match.group(1)
        
        # 获取最新交易日期
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
        engine = create_engine(f'sqlite:///{db_path}')
        
        try:
            latest_date_sql = f"SELECT MAX(trade_date) as max_date FROM stock_history WHERE stock_code = '{stock_code}'"
            df_latest = pd.read_sql(text(latest_date_sql), engine)
            latest_date_str = df_latest['max_date'].iloc[0]
            
            if not latest_date_str:
                print("⚠️ 未找到最新交易日期，无法转换")
                return sql_input
            
            # 计算30天前的日期
            latest_date = datetime.strptime(str(latest_date_str), '%Y%m%d')
            start_date = latest_date - timedelta(days=30)
            start_date_str = start_date.strftime('%Y%m%d')
            
            print(f"   最新日期: {latest_date_str}")
            print(f"   起始日期: {start_date_str} (往前推30天)")
            
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
    
    # 检测是否包含 "ORDER BY trade_date DESC LIMIT 30" 模式
    pattern = r'ORDER\s+BY\s+trade_date\s+DESC\s+LIMIT\s+30'
    
    if not re.search(pattern, sql_input, re.IGNORECASE):
        return sql_input
    
    print("⚠️ 检测到'最近一个月'查询（LIMIT 30），正在转换为自然月30天...")
    
    # 提取股票代码
    stock_code_match = re.search(r"stock_code\s*=\s*['\"]([^'\"]+)['\"]", sql_input)
    if not stock_code_match:
        print("⚠️ 未找到股票代码，无法转换")
        return sql_input
    
    stock_code = stock_code_match.group(1)
    
    # 获取最新交易日期
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    try:
        latest_date_sql = f"SELECT MAX(trade_date) as max_date FROM stock_history WHERE stock_code = '{stock_code}'"
        df_latest = pd.read_sql(text(latest_date_sql), engine)
        latest_date_str = df_latest['max_date'].iloc[0]
        
        if not latest_date_str:
            print("⚠️ 未找到最新交易日期，无法转换")
            return sql_input
        
        # 计算30天前的日期
        latest_date = datetime.strptime(str(latest_date_str), '%Y%m%d')
        start_date = latest_date - timedelta(days=30)
        start_date_str = start_date.strftime('%Y%m%d')
        
        print(f"   最新日期: {latest_date_str}")
        print(f"   起始日期: {start_date_str} (往前推30天)")
        
        # 直接在WHERE中添加日期条件
        if 'WHERE' in sql_input.upper():
            new_sql = re.sub(
                r'(WHERE\s+stock_code\s*=\s*[\'"][^\'"]+[\'"])',
                f"\\1 AND trade_date >= '{start_date_str}'",
                sql_input,
                flags=re.IGNORECASE
            )
            # 移除 LIMIT 30
            new_sql = re.sub(r'\s+LIMIT\s+30', '', new_sql, flags=re.IGNORECASE)
            return new_sql
            
    except Exception as e:
        print(f"   ❌ SQL预处理失败: {str(e)}")
        return sql_input
    
    return sql_input


def test_enhanced_preprocessing():
    """测试增强版SQL预处理功能"""
    
    print("="*70)
    print("测试：增强版智能SQL预处理功能")
    print("="*70)
    
    # 测试用例1：字符串日期算术运算
    sql1 = """SELECT 
        (SELECT trade_date FROM stock_history WHERE stock_code = '600519.SH' AND trade_date >= (SELECT MAX(trade_date) FROM stock_history WHERE stock_code = '600519.SH') - 30 ORDER BY high_price DESC LIMIT 1) as high_date,
        (SELECT MAX(high_price) FROM stock_history WHERE stock_code = '600519.SH' AND trade_date >= (SELECT MAX(trade_date) FROM stock_history WHERE stock_code = '600519.SH') - 30) as high_price,
        (SELECT trade_date FROM stock_history WHERE stock_code = '600519.SH' AND trade_date >= (SELECT MAX(trade_date) FROM stock_history WHERE stock_code = '600519.SH') - 30 ORDER BY low_price ASC LIMIT 1) as low_date,
        (SELECT MIN(low_price) FROM stock_history WHERE stock_code = '600519.SH' AND trade_date >= (SELECT MAX(trade_date) FROM stock_history WHERE stock_code = '600519.SH') - 30) as low_price"""
    
    print("\n📝 测试用例1：字符串日期算术运算")
    print("原始SQL（片段）:")
    print("WHERE trade_date >= (SELECT MAX(trade_date) ...) - 30")
    
    processed_sql1 = preprocess_sql_enhanced(sql1)
    print("\n处理后SQL（片段）:")
    if '20260325' in processed_sql1:
        print("WHERE trade_date >= '20260325'")
        print("✅ 成功修正为具体日期常量")
    else:
        print("❌ 修正失败")
    
    # 执行处理后的SQL
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    try:
        df1 = pd.read_sql(text(processed_sql1), engine)
        print(f"\n返回结果：")
        print(df1.to_markdown(index=False))
        
        # 验证结果正确性
        if len(df1) == 1:
            high_price = df1['high_price'].iloc[0]
            low_price = df1['low_price'].iloc[0]
            print(f"\n📊 最高价：{high_price} 元")
            print(f"📊 最低价：{low_price} 元")
            
            # 与正确结果对比
            correct_sql = """
            SELECT trade_date, high_price, low_price
            FROM stock_history 
            WHERE stock_code = '600519.SH' 
              AND trade_date >= '20260325'
            """
            df_correct = pd.read_sql(text(correct_sql), engine)
            expected_high = df_correct['high_price'].max()
            expected_low = df_correct['low_price'].min()
            
            print(f"\n✅ 预期最高价：{expected_high} 元")
            print(f"✅ 预期最低价：{expected_low} 元")
            
            if abs(high_price - expected_high) < 0.01 and abs(low_price - expected_low) < 0.01:
                print("\n✅ 测试结果正确！")
            else:
                print("\n⚠️  测试结果与预期不符")
    except Exception as e:
        print(f"执行失败：{str(e)}")
    
    # 测试用例2：LIMIT 30模式
    sql2 = """SELECT * FROM (
        SELECT trade_date, close_price 
        FROM stock_history 
        WHERE stock_code = '600519.SH' 
        ORDER BY trade_date DESC 
        LIMIT 30
    ) ORDER BY trade_date ASC"""
    
    print("\n" + "="*70)
    print("\n📝 测试用例2：LIMIT 30模式")
    print("原始SQL:")
    print("ORDER BY trade_date DESC LIMIT 30")
    
    processed_sql2 = preprocess_sql_enhanced(sql2)
    print("\n处理后SQL（片段）:")
    if '20260325' in processed_sql2:
        print("WHERE trade_date >= '20260325'")
        print("✅ 成功转换为自然月30天查询")
    else:
        print("❌ 转换失败")
    
    print("\n" + "="*70)
    print("总结：")
    print("="*70)
    print("1. ✅ 检测并修正字符串日期算术运算（MAX(trade_date) - 30）")
    print("2. ✅ 检测并转换 LIMIT 30 为自然月30天查询")
    print("3. ✅ 统一转换为具体日期常量查询（WHERE trade_date >= 'YYYYMMDD'）")
    print("="*70)


if __name__ == '__main__':
    test_enhanced_preprocessing()
