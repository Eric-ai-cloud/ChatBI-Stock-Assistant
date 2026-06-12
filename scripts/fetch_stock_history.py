import os
import tushare as ts
import pandas as pd
from datetime import datetime

# 设置tushare token
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 定义股票代码映射（使用tushare的股票代码格式）
stock_codes = {
    '贵州茅台': '600519.SH',
    '五粮液': '000858.SZ',
    '广发证券': '000776.SZ',
    '中芯国际': '688981.SH'
}

# 设置时间范围
start_date = '20200101'  # tushare使用YYYYMMDD格式
end_date = datetime.now().strftime('%Y%m%d')

print(f"正在获取股票数据，时间范围：{start_date} 至 {end_date}")
print("=" * 60)

# 创建空列表存储所有股票数据
all_data = []

# 遍历每只股票，获取历史行情
for stock_name, stock_code in stock_codes.items():
    try:
        print(f"\n正在获取 {stock_name} ({stock_code}) 的数据...")
        
        # 获取日线行情数据
        df = pro.daily(
            ts_code=stock_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is not None and not df.empty:
            # 添加股票名称列
            df['stock_name'] = stock_name
            
            # 重命名列以便更清晰
            df.rename(columns={
                'ts_code': '股票代码',
                'trade_date': '交易日期',
                'open': '开盘价',
                'high': '最高价',
                'low': '最低价',
                'close': '收盘价',
                'pre_close': '昨收价',
                'change': '涨跌额',
                'pct_chg': '涨跌幅',
                'vol': '成交量(手)',
                'amount': '成交额(千元)'
            }, inplace=True)
            
            all_data.append(df)
            print(f"  ✓ 成功获取 {len(df)} 条记录")
        else:
            print(f"  ✗ 未获取到 {stock_name} 的数据")
            
    except Exception as e:
        print(f"  ✗ 获取 {stock_name} 数据时出错: {str(e)}")

# 合并所有数据
if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # 按交易日期从小到大排序
    combined_df = combined_df.sort_values(by='交易日期', ascending=True)
    
    # 重置索引
    combined_df.reset_index(drop=True, inplace=True)
    
    # 保存到Excel文件
    output_file = '../data/stock_history_data.xlsx'
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            combined_df.to_excel(writer, sheet_name='股票历史数据', index=False)
        print(f"\n{'=' * 60}")
        print(f"✓ 数据已成功保存到: {output_file}")
        print(f"✓ 总记录数: {len(combined_df)} 条")
        print(f"✓ 包含股票: {', '.join(stock_codes.keys())}")
        print(f"✓ 时间范围: {combined_df['交易日期'].min()} 至 {combined_df['交易日期'].max()}")
        print(f"{'=' * 60}")
    except PermissionError:
        print(f"\n✗ 错误: 文件 '{output_file}' 正被其他程序占用，请关闭该文件后重试")
    except Exception as e:
        print(f"\n✗ 保存文件时出错: {str(e)}")
else:
    print("\n✗ 未能获取任何股票数据")
