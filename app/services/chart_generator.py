"""图表生成服务"""
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd


class ChartGenerator:
    """智能图表生成器"""
    
    def __init__(self, output_dir: Path = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "data" / "image_show"
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
    
    def generate_smart_chart(self, df: pd.DataFrame) -> str:
        """
        智能生成图表
        
        Returns:
            图片的 Markdown 路径
        """
        filename = f'stock_chart_{int(time.time() * 1000)}.png'
        save_path = self.output_dir / filename
        
        columns = df.columns.tolist()
        data_len = len(df)
        
        has_date = 'trade_date' in columns or '交易日期' in columns
        has_close = 'close_price' in columns or '收盘价' in columns
        has_stock_name = 'stock_name' in columns or '股票名称' in columns
        
        fig, ax = plt.subplots(figsize=(12, 6))
        use_line_chart = data_len > 20
        
        if has_date and has_close:
            self._plot_stock_chart(ax, df, has_stock_name, use_line_chart)
        else:
            self._plot_generic_chart(ax, df, use_line_chart)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return f'data/image_show/{filename}'
    
    def _plot_stock_chart(self, ax, df, has_stock_name, use_line_chart):
        """绘制股票图表"""
        date_col = 'trade_date' if 'trade_date' in df.columns else '交易日期'
        close_col = 'close_price' if 'close_price' in df.columns else '收盘价'
        name_col = 'stock_name' if 'stock_name' in df.columns else '股票名称'
        
        if has_stock_name and df[name_col].nunique() > 1:
            # 多只股票对比
            for stock_name in df[name_col].unique():
                stock_data = df[df[name_col] == stock_name].sort_values(by=date_col)
                
                if use_line_chart and len(stock_data) > 10:
                    sample_indices = np.linspace(0, len(stock_data) - 1, 10, dtype=int)
                    stock_data = stock_data.iloc[sample_indices]
                
                dates = self._format_dates(stock_data[date_col])
                ax.plot(dates, stock_data[close_col], label=stock_name, linewidth=2, marker='o' if use_line_chart else None)
            
            ax.set_title(f"多股票收盘价对比", fontsize=14, fontweight='bold')
            ax.legend(loc='best')
        else:
            # 单只股票
            stock_data = df.sort_values(by=date_col)
            
            if use_line_chart and len(stock_data) > 10:
                sample_indices = np.linspace(0, len(stock_data) - 1, 10, dtype=int)
                stock_data = stock_data.iloc[sample_indices]
            
            dates = self._format_dates(stock_data[date_col])
            ax.plot(dates, stock_data[close_col], color='#FF6B6B', linewidth=2, label='收盘价', marker='o')
            
            stock_name_display = stock_data[name_col].iloc[0] if has_stock_name else '股票'
            ax.set_title(f"{stock_name_display}价格走势", fontsize=14, fontweight='bold')
            ax.legend(loc='best')
        
        ax.set_xlabel("交易日期")
        ax.set_ylabel("价格 (元)")
        plt.xticks(rotation=45)
    
    def _plot_generic_chart(self, ax, df, use_line_chart):
        """绘制通用统计图"""
        columns = df.columns.tolist()
        if len(columns) < 2:
            ax.text(0.5, 0.5, '数据不足以生成图表', ha='center', va='center', fontsize=16)
            return
        
        x_col = columns[0]
        y_cols = [col for col in columns[1:] if df[col].dtype in ['float64', 'int64']]
        
        if not y_cols:
            ax.text(0.5, 0.5, '无可视化数据', ha='center', va='center', fontsize=16)
            return
        
        if use_line_chart:
            x = np.arange(len(df))
            if len(df) > 10:
                sample_indices = np.linspace(0, len(df) - 1, 10, dtype=int)
                df_sampled = df.iloc[sample_indices]
                x_sampled = np.arange(len(df_sampled))
            else:
                df_sampled = df
                x_sampled = x
            
            for y_col in y_cols[:3]:
                ax.plot(x_sampled, df_sampled[y_col], label=str(y_col), linewidth=2, marker='o')
            
            plt.xticks(x_sampled, [str(v) for v in df_sampled[x_col]], rotation=45)
        else:
            x = np.arange(len(df))
            bottom = np.zeros(len(df))
            
            for y_col in y_cols[:3]:
                ax.bar(x, df[y_col], bottom=bottom, label=str(y_col), alpha=0.8)
                bottom += df[y_col]
            
            plt.xticks(x, [str(v) for v in df[x_col]], rotation=45)
        
        ax.set_title(f"数据统计", fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.set_xlabel(str(x_col))
        ax.set_ylabel("数值")
    
    def _format_dates(self, dates):
        """格式化日期"""
        return [str(d)[:4] + '-' + str(d)[4:6] + '-' + str(d)[6:8] for d in dates]
