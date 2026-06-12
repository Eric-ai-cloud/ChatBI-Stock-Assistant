import pandas as pd
from sqlalchemy import create_engine, text
import os
import sqlite3

# 数据库文件路径
DB_FILE = '../data/stock_prices.db'
EXCEL_FILE = '../data/stock_history_data.xlsx'

def create_database():
    """创建数据库和表结构"""
    print("正在创建数据库和表结构...")
    
    # 读取SQL建表语句
    with open('../data/create_stock_table.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # 连接到SQLite数据库（如果不存在则自动创建）
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 执行建表SQL
        cursor.executescript(sql_script)
        conn.commit()
        print(f"✓ 数据库 '{DB_FILE}' 创建成功")
        print("✓ 表结构 'stock_history' 已建立")
    except Exception as e:
        print(f"✗ 创建数据库时出错: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def import_data_from_excel():
    """从Excel文件导入数据到SQLite数据库"""
    print(f"\n正在从 '{EXCEL_FILE}' 读取数据...")
    
    # 检查Excel文件是否存在
    if not os.path.exists(EXCEL_FILE):
        print(f"✗ 错误: 找不到文件 '{EXCEL_FILE}'")
        print("请先运行 fetch_stock_history.py 生成Excel文件")
        return
    
    try:
        # 读取Excel文件
        df = pd.read_excel(EXCEL_FILE, sheet_name='股票历史数据')
        print(f"✓ 成功读取 {len(df)} 条记录")
        
        # 显示数据预览
        print("\n数据预览（前5行）:")
        print(df.head())
        print(f"\n数据列: {', '.join(df.columns.tolist())}")
        
    except Exception as e:
        print(f"✗ 读取Excel文件时出错: {str(e)}")
        return
    
    # 导入到SQLite数据库
    print(f"\n正在将数据导入到 '{DB_FILE}'...")
    
    try:
        # 创建数据库引擎
        engine = create_engine(f'sqlite:///{DB_FILE}')
        
        # 数据预处理：确保列名与数据库字段匹配
        df_import = df.copy()
        df_import.rename(columns={
            '股票代码': 'stock_code',
            '股票名称': 'stock_name',
            '交易日期': 'trade_date',
            '开盘价': 'open_price',
            '最高价': 'high_price',
            '最低价': 'low_price',
            '收盘价': 'close_price',
            '昨收价': 'pre_close',
            '涨跌额': 'change_amount',
            '涨跌幅': 'change_pct',
            '成交量(手)': 'volume',
            '成交额(千元)': 'amount'
        }, inplace=True)
        
        # 转换数据类型
        df_import['trade_date'] = df_import['trade_date'].astype(str)
        df_import['volume'] = df_import['volume'].astype(int)
        
        # 使用to_sql导入数据，如果存在则替换
        # method='multi'可以提高插入效率
        rows_inserted = df_import.to_sql(
            'stock_history', 
            engine, 
            if_exists='replace',  # 如果表存在则替换
            index=False,
            chunksize=1000  # 分批插入，每批1000条
        )
        
        print(f"✓ 成功导入 {rows_inserted} 条记录到数据库")
        
        # 验证数据
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 查询总记录数
        cursor.execute("SELECT COUNT(*) FROM stock_history")
        total_count = cursor.fetchone()[0]
        print(f"✓ 数据库中总记录数: {total_count}")
        
        # 查询每只股票的记录数
        cursor.execute("""
            SELECT stock_name, COUNT(*) as count, 
                   MIN(trade_date) as min_date, 
                   MAX(trade_date) as max_date
            FROM stock_history 
            GROUP BY stock_name
            ORDER BY stock_name
        """)
        
        print("\n各股票数据统计:")
        print("-" * 70)
        print(f"{'股票名称':<10} {'记录数':<10} {'最早日期':<12} {'最晚日期':<12}")
        print("-" * 70)
        for row in cursor.fetchall():
            print(f"{row[0]:<10} {row[1]:<10} {row[2]:<12} {row[3]:<12}")
        print("-" * 70)
        
        # 查询示例数据
        print("\n示例数据（最近5条记录）:")
        cursor.execute("""
            SELECT stock_name, trade_date, close_price, change_pct
            FROM stock_history
            ORDER BY trade_date DESC
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            print(f"  {row[0]} | {row[1]} | 收盘价: {row[2]:.2f} | 涨跌幅: {row[3]:.2f}%")
        
        conn.close()
        
        print(f"\n{'=' * 70}")
        print(f"✓ 数据导入完成！")
        print(f"✓ 数据库文件: {DB_FILE}")
        print(f"✓ 可以使用 SQLite 客户端或 Python 脚本查询数据")
        print(f"{'=' * 70}")
        
    except PermissionError:
        print(f"\n✗ 错误: 数据库文件 '{DB_FILE}' 正被其他程序占用，请关闭后重试")
    except Exception as e:
        print(f"\n✗ 导入数据时出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 70)
    print("股票历史数据导入工具")
    print("=" * 70)
    
    # 第一步：创建数据库和表结构
    create_database()
    
    # 第二步：从Excel导入数据
    import_data_from_excel()
