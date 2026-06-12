"""
测试智能可视化功能
验证不同数据量下的图表类型选择
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
from datetime import datetime, timedelta

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

def generate_test_data(num_rows):
    """生成测试数据"""
    dates = []
    start_date = datetime(2024, 1, 1)
    for i in range(num_rows):
        date = start_date + timedelta(days=i)
        dates.append(date.strftime('%Y%m%d'))
    
    df = pd.DataFrame({
        'trade_date': dates,
        'stock_name': ['贵州茅台'] * num_rows,
        'close_price': np.random.uniform(1400, 1500, num_rows).round(2),
        'open_price': np.random.uniform(1390, 1490, num_rows).round(2),
        'volume': np.random.randint(20000, 60000, num_rows)
    })
    
    return df

def generate_smart_chart_png(df_sql, save_path):
    """
    智能生成股票数据图表
    根据数据量自动选择图表类型：
    - 数据量 <= 20: 柱状图
    - 数据量 > 20: 折线图（横坐标采样至最多10个点）
    """
    columns = df_sql.columns.tolist()
    data_len = len(df_sql)
    
    # 检查是否有日期和收盘价列
    has_date = 'trade_date' in columns or '交易日期' in columns
    has_close = 'close_price' in columns or '收盘价' in columns
    has_stock_name = 'stock_name' in columns or '股票名称' in columns
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 确定是否使用折线图（数据量较大时）
    use_line_chart = data_len > 20
    
    if has_date and has_close:
        # 确定列名
        date_col = 'trade_date' if 'trade_date' in columns else '交易日期'
        close_col = 'close_price' if 'close_price' in columns else '收盘价'
        name_col = 'stock_name' if 'stock_name' in columns else '股票名称'
        
        if has_stock_name and df_sql[name_col].nunique() > 1:
            # 多只股票对比图
            for stock_name in df_sql[name_col].unique():
                stock_data = df_sql[df_sql[name_col] == stock_name].sort_values(by=date_col)
                
                # 如果数据量大，进行采样
                if use_line_chart and len(stock_data) > 10:
                    sample_indices = np.linspace(0, len(stock_data) - 1, 10, dtype=int)
                    stock_data = stock_data.iloc[sample_indices]
                
                # 转换日期格式
                dates = [str(d)[:4] + '-' + str(d)[4:6] + '-' + str(d)[6:8] for d in stock_data[date_col]]
                ax.plot(dates, stock_data[close_col], label=stock_name, linewidth=2, marker='o' if use_line_chart else None, markersize=4)
            
            chart_type = "折线图" if use_line_chart else "柱状图"
            ax.set_title(f"多股票收盘价对比 ({chart_type}, {data_len}条数据)", fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.set_xlabel("交易日期")
            ax.set_ylabel("收盘价 (元)")
            plt.xticks(rotation=45)
        else:
            # 单只股票走势图
            stock_data = df_sql.sort_values(by=date_col)
            
            # 如果数据量大，进行采样
            if use_line_chart and len(stock_data) > 10:
                sample_indices = np.linspace(0, len(stock_data) - 1, 10, dtype=int)
                stock_data_sampled = stock_data.iloc[sample_indices]
            else:
                stock_data_sampled = stock_data
            
            # 转换日期格式
            dates = [str(d)[:4] + '-' + str(d)[4:6] + '-' + str(d)[6:8] for d in stock_data_sampled[date_col]]
            
            if use_line_chart:
                # 折线图
                ax.plot(dates, stock_data_sampled[close_col], color='#FF6B6B', linewidth=2, label='收盘价', marker='o', markersize=5)
                
                # 如果有开盘价，也绘制
                if 'open_price' in columns or '开盘价' in columns:
                    open_col = 'open_price' if 'open_price' in columns else '开盘价'
                    ax.plot(dates, stock_data_sampled[open_col], color='#4ECDC4', linewidth=1.5, label='开盘价', linestyle='--', marker='s', markersize=4)
            else:
                # 柱状图
                x = np.arange(len(stock_data_sampled))
                ax.bar(x, stock_data_sampled[close_col], color='#FF6B6B', alpha=0.7, label='收盘价')
                
                # 如果有开盘价，也绘制
                if 'open_price' in columns or '开盘价' in columns:
                    open_col = 'open_price' if 'open_price' in columns else '开盘价'
                    ax.bar(x + 0.35, stock_data_sampled[open_col], width=0.35, color='#4ECDC4', alpha=0.7, label='开盘价')
                    plt.xticks(x + 0.175, dates, rotation=45, ha='right')
                else:
                    plt.xticks(x, dates, rotation=45, ha='right')
            
            stock_name_display = stock_data[name_col].iloc[0] if has_stock_name else '股票'
            chart_type = "折线图" if use_line_chart else "柱状图"
            ax.set_title(f"{stock_name_display}价格走势 ({chart_type}, {data_len}条数据)", 
                        fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.set_xlabel("交易日期")
            ax.set_ylabel("价格 (元)")
            if use_line_chart:
                plt.xticks(rotation=45)
    else:
        # 通用统计图
        if len(columns) >= 2:
            x_col = columns[0]
            y_cols = [col for col in columns[1:] if df_sql[col].dtype in ['float64', 'int64']]
            
            if y_cols:
                if use_line_chart:
                    # 数据量大时使用折线图
                    x = np.arange(len(df_sql))
                    
                    # 采样至最多10个点
                    if len(df_sql) > 10:
                        sample_indices = np.linspace(0, len(df_sql) - 1, 10, dtype=int)
                        df_sampled = df_sql.iloc[sample_indices]
                        x_sampled = np.arange(len(df_sampled))
                        x_labels = [str(val).replace('%', '%%') for val in df_sampled[x_col]]
                    else:
                        df_sampled = df_sql
                        x_sampled = x
                        x_labels = [str(val).replace('%', '%%') for val in df_sql[x_col]]
                    
                    for y_col in y_cols[:3]:  # 最多显示3个指标
                        safe_label = str(y_col).replace('%', '%%')
                        ax.plot(x_sampled, df_sampled[y_col], label=safe_label, linewidth=2, marker='o', markersize=5)
                    
                    plt.xticks(x_sampled, x_labels, rotation=45, ha='right')
                    chart_type = "折线图"
                else:
                    # 数据量小时使用柱状图
                    x = np.arange(len(df_sql))
                    bottom = np.zeros(len(df_sql))
                    
                    for y_col in y_cols[:3]:  # 最多显示3个指标
                        safe_label = str(y_col).replace('%', '%%')
                        ax.bar(x, df_sql[y_col], bottom=bottom, label=safe_label, alpha=0.8)
                        bottom += df_sql[y_col]
                    
                    safe_xtick_labels = [str(val).replace('%', '%%') for val in df_sql[x_col]]
                    plt.xticks(x, safe_xtick_labels, rotation=45, ha='right')
                    chart_type = "柱状图"
                
                ax.set_title(f"数据统计 ({chart_type}, {data_len}条数据)", fontsize=14, fontweight='bold')
                ax.legend(loc='best')
                ax.set_xlabel(str(x_col))
                ax.set_ylabel("数值")
            else:
                ax.text(0.5, 0.5, '无可视化数据', ha='center', va='center', fontsize=16)
        else:
            ax.text(0.5, 0.5, '数据不足以生成图表', ha='center', va='center', fontsize=16)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

def test_smart_visualization():
    """测试智能可视化功能"""
    print("="*70)
    print("智能可视化功能测试")
    print("="*70)
    
    # 创建输出目录
    output_dir = os.path.join(os.path.dirname(__file__), 'test_charts')
    os.makedirs(output_dir, exist_ok=True)
    
    # 测试场景1: 小数据量 (10条) - 应该使用柱状图
    print("\n测试1: 小数据量 (10条) - 预期: 柱状图")
    df_small = generate_test_data(10)
    save_path = os.path.join(output_dir, 'test_small_10.png')
    
    # 调用智能可视化函数
    generate_smart_chart_png(df_small, save_path)
    print(f"  ✓ 已生成: {save_path}")
    print(f"  ✓ 数据量: {len(df_small)} 条")
    
    # 测试场景2: 中等数据量 (30条) - 应该使用折线图
    print("\n测试2: 中等数据量 (30条) - 预期: 折线图（采样至10点）")
    df_medium = generate_test_data(30)
    save_path = os.path.join(output_dir, 'test_medium_30.png')
    generate_smart_chart_png(df_medium, save_path)
    print(f"  ✓ 已生成: {save_path}")
    print(f"  ✓ 数据量: {len(df_medium)} 条")
    
    # 测试场景3: 大数据量 (100条) - 应该使用折线图
    print("\n测试3: 大数据量 (100条) - 预期: 折线图（采样至10点）")
    df_large = generate_test_data(100)
    save_path = os.path.join(output_dir, 'test_large_100.png')
    generate_smart_chart_png(df_large, save_path)
    print(f"  ✓ 已生成: {save_path}")
    print(f"  ✓ 数据量: {len(df_large)} 条")
    
    # 测试场景4: 多股票对比 (50条)
    print("\n测试4: 多股票对比 (50条，2只股票) - 预期: 折线图")
    dates = []
    start_date = datetime(2024, 1, 1)
    for i in range(25):
        date = start_date + timedelta(days=i)
        dates.append(date.strftime('%Y%m%d'))
    
    df_multi = pd.DataFrame({
        'trade_date': dates * 2,
        'stock_name': ['贵州茅台'] * 25 + ['五粮液'] * 25,
        'close_price': np.concatenate([
            np.random.uniform(1400, 1500, 25).round(2),
            np.random.uniform(100, 110, 25).round(2)
        ])
    })
    save_path = os.path.join(output_dir, 'test_multi_50.png')
    generate_smart_chart_png(df_multi, save_path)
    print(f"  ✓ 已生成: {save_path}")
    print(f"  ✓ 数据量: {len(df_multi)} 条")
    print(f"  ✓ 股票数: {df_multi['stock_name'].nunique()} 只")
    
    print("\n" + "="*70)
    print("✓ 所有测试完成！")
    print(f"✓ 图表保存在: {output_dir}")
    print("="*70)
    print("\n请查看生成的图表文件，验证：")
    print("  1. 小数据量 (≤20) 使用柱状图")
    print("  2. 大数据量 (>20) 使用折线图")
    print("  3. 大数据量的横坐标采样至最多10个点")
    print("="*70)

if __name__ == '__main__':
    try:
        test_smart_visualization()
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
