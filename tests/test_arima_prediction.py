"""
测试：ARIMA股票预测功能
验证ARIMA工具能否正确预测股票价格
"""
import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import datetime, timedelta
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')
import matplotlib.pyplot as plt

def test_arima_prediction():
    """测试ARIMA预测功能"""
    
    print("="*70)
    print("测试：ARIMA股票预测功能")
    print("="*70)
    
    # 配置参数
    ts_code = '600519.SH'  # 贵州茅台
    n_days = 7  # 预测7天
    
    print(f"\n📊 测试参数：")
    print(f"   股票代码: {ts_code}")
    print(f"   预测天数: {n_days}天")
    
    # 从SQLite数据库获取过去一年的历史数据
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
            print(f"❌ 错误：未找到股票 {ts_code} 的历史数据！")
            return
        
        print(f"\n✅ 获取到 {len(df_history)} 条历史数据")
        print(f"   日期范围: {df_history['trade_date'].iloc[0]} 至 {df_history['trade_date'].iloc[-1]}")
        print(f"   价格范围: {df_history['close_price'].min():.2f} - {df_history['close_price'].max():.2f}")
        
        # 准备时间序列数据
        df_history['trade_date_dt'] = pd.to_datetime(df_history['trade_date'], format='%Y%m%d')
        df_history.set_index('trade_date_dt', inplace=True)
        
        # 处理缺失值：向前填充
        ts_data = df_history['close_price'].copy()
        ts_data = ts_data.asfreq('D', method='ffill')  # 按日频率重采样，向前填充
        
        print(f"\n🔧 数据预处理完成")
        print(f"   重采样后数据点数: {len(ts_data)}")
        
        # 训练ARIMA模型 (5,1,5)
        print(f"\n🔮 正在训练ARIMA(5,1,5)模型...")
        model = ARIMA(ts_data, order=(5, 1, 5))
        model_fit = model.fit()
        print(f"   ✅ 模型训练完成")
        
        # 预测未来N天
        print(f"   正在预测未来{n_days}天的价格...")
        forecast_result = model_fit.get_forecast(steps=n_days)
        forecast_mean = forecast_result.predicted_mean
        forecast_ci = forecast_result.conf_int()
        
        # 生成预测日期
        last_date = ts_data.index[-1]
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=n_days, freq='D')
        
        # 构建预测结果DataFrame
        df_forecast = pd.DataFrame({
            'forecast_date': forecast_dates.strftime('%Y%m%d'),
            'predicted_price': forecast_mean.values,
            'lower_ci': forecast_ci.iloc[:, 0].values,
            'upper_ci': forecast_ci.iloc[:, 1].values
        })
        
        print(f"\n✅ 预测完成！")
        print(f"\n📈 预测结果：")
        print(df_forecast.to_markdown(index=False))
        
        # 可视化
        print(f"\n📊 生成预测图表...")
        save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f'test_arima_{ts_code.replace(".", "_")}.png')
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # 绘制历史数据（最近60天）
        recent_history = ts_data.tail(60)
        ax.plot(recent_history.index, recent_history.values, 
               label='历史收盘价', color='#2E86AB', linewidth=2, marker='o', markersize=4)
        
        # 绘制预测数据
        ax.plot(forecast_dates, forecast_mean.values, 
               label='预测价格', color='#A23B72', linewidth=2, marker='s', markersize=5)
        
        # 绘制置信区间
        ax.fill_between(forecast_dates, 
                       forecast_ci.iloc[:, 0].values,
                       forecast_ci.iloc[:, 1].values,
                       alpha=0.2, color='#A23B72', label='95%置信区间')
        
        ax.set_title(f'{ts_code} 股票价格预测 (ARIMA模型)', fontsize=16, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价格 (元)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴日期
        import matplotlib.dates as mdates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"   ✅ 图表已保存: {save_path}")
        
        print("\n" + "="*70)
        print("测试总结：")
        print("="*70)
        print("1. ✅ 成功获取历史数据")
        print("2. ✅ 成功训练ARIMA(5,1,5)模型")
        print("3. ✅ 成功预测未来价格")
        print("4. ✅ 成功生成可视化图表")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_arima_prediction()
