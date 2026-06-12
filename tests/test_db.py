"""
股票助手数据库测试脚本
用于验证数据库连接和数据完整性
"""

import sqlite3
import pandas as pd
import os

def test_database():
    """测试数据库连接和数据"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    
    print("="*70)
    print("股票助手数据库测试")
    print("="*70)
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"✗ 错误: 数据库文件不存在: {db_path}")
        print("请先运行 import_to_sqlite.py 创建数据库")
        return False
    
    print(f"✓ 数据库文件存在: {db_path}")
    print(f"✓ 文件大小: {os.path.getsize(db_path) / 1024:.2f} KB\n")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        
        # 测试1: 查询总记录数
        print("测试1: 查询总记录数")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stock_history")
        total_count = cursor.fetchone()[0]
        print(f"  ✓ 总记录数: {total_count}\n")
        
        # 测试2: 查询各股票数据量
        print("测试2: 各股票数据统计")
        cursor.execute("""
            SELECT stock_name, stock_code, COUNT(*) as count, 
                   MIN(trade_date) as min_date, 
                   MAX(trade_date) as max_date
            FROM stock_history 
            GROUP BY stock_name, stock_code
            ORDER BY stock_name
        """)
        
        print(f"  {'股票名称':<10} {'股票代码':<12} {'记录数':<10} {'最早日期':<12} {'最晚日期':<12}")
        print("  " + "-"*60)
        for row in cursor.fetchall():
            print(f"  {row[0]:<10} {row[1]:<12} {row[2]:<10} {row[3]:<12} {row[4]:<12}")
        print()
        
        # 测试3: 查询示例数据
        print("测试3: 贵州茅台最近5天数据")
        df = pd.read_sql_query("""
            SELECT trade_date, open_price, high_price, low_price, 
                   close_price, change_pct, volume
            FROM stock_history
            WHERE stock_name = '贵州茅台'
            ORDER BY trade_date DESC
            LIMIT 5
        """, conn)
        
        print(df.to_string(index=False))
        print()
        
        # 测试4: 验证表结构
        print("测试4: 表结构验证")
        cursor.execute("PRAGMA table_info(stock_history)")
        columns = cursor.fetchall()
        print(f"  ✓ 字段数量: {len(columns)}")
        print(f"  字段列表: {', '.join([col[1] for col in columns])}\n")
        
        # 关闭连接
        conn.close()
        
        print("="*70)
        print("✓ 所有测试通过！数据库可以正常使用。")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_database()
