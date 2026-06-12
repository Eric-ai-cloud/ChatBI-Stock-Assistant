"""
ARIMA股票预测工具测试脚本
测试 arima_stock 工具的功能
"""
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

def test_arima_tool():
    """测试ARIMA预测工具"""
    print("="*70)
    print("ARIMA股票预测工具测试")
    print("="*70)
    
    # 测试参数
    ts_code = "600519.SH"  # 贵州茅台
    n_days = 7  # 预测7天
    
    print(f"\n测试参数:")
    print(f"  股票代码: {ts_code}")
    print(f"  预测天数: {n_days}天")
    
    # 首先检查是否有历史数据
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
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
            print(f"\n❌ 错误：未找到股票 {ts_code} 的历史数据！")
            return False
        
        print(f"\n✓ 获取到 {len(df_history)} 条历史数据")
        print(f"  日期范围: {df_history['trade_date'].iloc[0]} 至 {df_history['trade_date'].iloc[-1]}")
        print(f"  价格范围: {df_history['close_price'].min():.2f} - {df_history['close_price'].max():.2f}")
        
        # 显示最近5条数据
        print(f"\n最近5条历史数据:")
        print(df_history.tail(5).to_string(index=False))
        
        print("\n" + "="*70)
        print("数据检查通过！可以运行 stock_assistant-2.py 测试ARIMA预测功能")
        print("="*70)
        print("\n使用方法:")
        print("1. 启动程序: python stock_assistant-2.py")
        print(f"2. 在Web界面中输入: 预测{ts_code}未来{n_days}天的价格走势")
        print("3. 或在终端模式中输入相同问题")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    test_arima_tool()
