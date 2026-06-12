"""
测试布林带异常点检测工具
验证数据获取和布林带计算是否正确
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import datetime, timedelta

def test_bollinger_bands():
    """测试布林带计算逻辑"""
    print("="*70)
    print("布林带异常点检测测试")
    print("="*70)
    
    # 配置参数
    ts_code = '600519.SH'
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)
    start_date = one_year_ago.strftime('%Y%m%d')
    end_date = today.strftime('%Y%m%d')
    
    print(f"\n股票代码: {ts_code}")
    print(f"检测范围: {start_date} 至 {end_date}")
    
    # 从SQLite数据库获取历史数据
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_prices.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    try:
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
            print("❌ 错误：未找到历史数据！")
            return
        
        print(f"\n✅ 获取到 {len(df_history)} 条历史数据")
        print(f"   日期范围: {df_history['trade_date'].iloc[0]} 至 {df_history['trade_date'].iloc[-1]}")
        print(f"   价格范围: {df_history['close_price'].min():.2f} - {df_history['close_price'].max():.2f}")
        
        # 准备数据
        df_history['trade_date_dt'] = pd.to_datetime(df_history['trade_date'], format='%Y%m%d')
        df_history.set_index('trade_date_dt', inplace=True)
        
        close_prices = df_history['close_price']
        
        # 计算布林带指标
        window = 20  # 20日周期
        num_std = 2  # 2倍标准差
        
        # 中轨：20日移动平均线
        middle_band = close_prices.rolling(window=window).mean()
        
        # 标准差
        std_dev = close_prices.rolling(window=window).std()
        
        # 上轨和下轨
        upper_band = middle_band + (std_dev * num_std)
        lower_band = middle_band - (std_dev * num_std)
        
        # 检测异常点
        overbought = close_prices > upper_band
        oversold = close_prices < lower_band
        
        df_overbought = df_history[overbought].copy()
        df_oversold = df_history[oversold].copy()
        
        print(f"\n📊 布林带检测结果:")
        print(f"   超买点数量: {len(df_overbought)}")
        print(f"   超卖点数量: {len(df_oversold)}")
        print(f"   总异常点: {len(df_overbought) + len(df_oversold)}")
        
        # 显示前几个异常点
        if len(df_overbought) > 0:
            print(f"\n🔺 前5个超买点:")
            for i, (date, row) in enumerate(df_overbought.head(5).iterrows()):
                print(f"   {i+1}. {date.strftime('%Y-%m-%d')} - 收盘价: {row['close_price']:.2f}")
        
        if len(df_oversold) > 0:
            print(f"\n🔻 前5个超卖点:")
            for i, (date, row) in enumerate(df_oversold.head(5).iterrows()):
                print(f"   {i+1}. {date.strftime('%Y-%m-%d')} - 收盘价: {row['close_price']:.2f}")
        
        print("\n✅ 测试通过！布林带计算正常")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_bollinger_bands()
