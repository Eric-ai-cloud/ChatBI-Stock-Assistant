"""
测试ARIMA预测的交易日生成逻辑
验证预测日期是否只包含交易日（排除周末）
"""
import pandas as pd
from datetime import datetime, timedelta

def test_trading_day_generation():
    """测试交易日生成逻辑"""
    print("="*70)
    print("ARIMA预测交易日生成测试")
    print("="*70)
    
    # 模拟最后交易日期（假设是2026-04-24，周五）
    last_date = pd.Timestamp('2026-04-24')
    n_days = 10  # 预测10个交易日
    
    print(f"\n最后交易日: {last_date.strftime('%Y-%m-%d')} ({get_weekday_name(last_date)})")
    print(f"预测天数: {n_days}个交易日\n")
    
    # 生成预测日期（仅交易日）
    forecast_dates = []
    current_date = last_date + pd.Timedelta(days=1)
    
    while len(forecast_dates) < n_days:
        if current_date.weekday() < 5:  # 工作日 (0-4: 周一到周五)
            forecast_dates.append(current_date)
        current_date += pd.Timedelta(days=1)
    
    forecast_dates = pd.DatetimeIndex(forecast_dates)
    
    # 显示结果
    print("预测的交易日列表:")
    print("-" * 70)
    for i, date in enumerate(forecast_dates, 1):
        weekday = get_weekday_name(date)
        marker = " ⚠️ 周末" if date.weekday() >= 5 else ""
        print(f"  {i:2d}. {date.strftime('%Y-%m-%d')} ({weekday}){marker}")
    
    print("-" * 70)
    
    # 验证是否有周末
    weekend_count = sum(1 for d in forecast_dates if d.weekday() >= 5)
    
    if weekend_count == 0:
        print("\n✅ 测试通过！所有预测日期都是交易日（无周末）")
    else:
        print(f"\n❌ 测试失败！发现 {weekend_count} 个周末日期")
    
    # 统计跨越的自然日天数
    total_calendar_days = (forecast_dates[-1] - last_date).days
    print(f"\n统计信息:")
    print(f"  - 预测交易日数: {n_days} 天")
    print(f"  - 跨越自然日数: {total_calendar_days} 天")
    print(f"  - 跳过周末天数: {total_calendar_days - n_days} 天")
    print("="*70)


def get_weekday_name(date):
    """获取星期名称"""
    weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    return weekdays[date.weekday()]


if __name__ == '__main__':
    test_trading_day_generation()
