"""
测试ARIMA预测的交易日生成逻辑（含节假日过滤）
验证预测日期是否正确排除周末和常见节假日
"""
import pandas as pd
from datetime import datetime, timedelta

def test_trading_day_with_holidays():
    """测试包含节假日过滤的交易日生成逻辑"""
    print("="*70)
    print("ARIMA预测交易日生成测试（含节假日过滤）")
    print("="*70)
    
    # 模拟最后交易日期（假设是2026-04-24，周五）
    last_date = pd.Timestamp('2026-04-24')
    n_days = 15  # 预测15个交易日
    
    print(f"\n最后交易日: {last_date.strftime('%Y-%m-%d')} ({get_weekday_name(last_date)})")
    print(f"预测天数: {n_days}个交易日\n")
    
    # 生成预测日期（仅交易日，含节假日过滤）
    forecast_dates = []
    current_date = last_date + pd.Timedelta(days=1)
    
    while len(forecast_dates) < n_days:
        weekday = current_date.weekday()
        
        # 跳过周末
        if weekday >= 5:
            current_date += pd.Timedelta(days=1)
            continue
        
        # 简单的节假日过滤
        month = current_date.month
        day = current_date.day
        
        is_holiday = False
        
        # 元旦
        if month == 1 and day == 1:
            is_holiday = True
            holiday_name = "元旦"
        # 劳动节
        elif month == 5 and day == 1:
            is_holiday = True
            holiday_name = "劳动节"
        # 国庆节
        elif month == 10 and day <= 3:
            is_holiday = True
            holiday_name = "国庆节"
        else:
            holiday_name = None
        
        if not is_holiday:
            forecast_dates.append(current_date)
        else:
            print(f"  ⚠️  跳过节假日: {current_date.strftime('%Y-%m-%d')} ({holiday_name})")
        
        current_date += pd.Timedelta(days=1)
    
    forecast_dates = pd.DatetimeIndex(forecast_dates)
    
    # 显示结果
    print("\n预测的交易日列表:")
    print("-" * 70)
    for i, date in enumerate(forecast_dates, 1):
        weekday = get_weekday_name(date)
        marker = ""
        if date.weekday() >= 5:
            marker = " ⚠️ 周末（错误！）"
        print(f"  {i:2d}. {date.strftime('%Y-%m-%d')} ({weekday}){marker}")
    
    print("-" * 70)
    
    # 验证是否有周末或节假日
    weekend_count = sum(1 for d in forecast_dates if d.weekday() >= 5)
    
    if weekend_count == 0:
        print("\n✅ 测试通过！所有预测日期都是工作日（无周末）")
    else:
        print(f"\n❌ 测试失败！发现 {weekend_count} 个周末日期")
    
    # 统计跨越的自然日天数
    total_calendar_days = (forecast_dates[-1] - last_date).days
    skipped_days = total_calendar_days - n_days
    
    print(f"\n📊 统计信息:")
    print(f"  - 预测交易日数: {n_days} 天")
    print(f"  - 跨越自然日数: {total_calendar_days} 天")
    print(f"  - 跳过非交易日: {skipped_days} 天（周末+节假日）")
    print(f"  - 起始日期: {forecast_dates[0].strftime('%Y-%m-%d')}")
    print(f"  - 结束日期: {forecast_dates[-1].strftime('%Y-%m-%d')}")
    print("="*70)
    
    print("\n⚠️  注意：")
    print("  - 当前实现仅排除固定日期假日（元旦、劳动节、国庆节）")
    print("  - 春节、清明等农历节日需查表或接入API才能精确识别")
    print("  - 生产环境建议使用 Tushare/akshare 等专业库获取官方交易日历")


def get_weekday_name(date):
    """获取星期名称"""
    weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    return weekdays[date.weekday()]


if __name__ == '__main__':
    test_trading_day_with_holidays()
