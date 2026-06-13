"""布林带检测工具 - NanoBot版本"""
import json
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import text

from nanobot.agent.tools.base import Tool
from app.utils.database import get_db_engine


class BollDetectionTool(Tool):
    """布林带异常点检测工具"""

    def __init__(self):
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

    @property
    def name(self) -> str:
        return "boll_detection"

    @property
    def description(self) -> str:
        return (
            "Detect overbought and oversold points using Bollinger Bands. "
            "Default detection range is the past year. Uses 20-day moving average ± 2 standard deviations."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ts_code": {
                    "type": "string",
                    "description": "Stock code (required), e.g., 600519.SH"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date (optional, YYYYMMDD format), defaults to one year ago"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (optional, YYYYMMDD format), defaults to today"
                }
            },
            "required": ["ts_code"]
        }

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        ts_code = kwargs.get("ts_code")
        start_date = kwargs.get("start_date", None)
        end_date = kwargs.get("end_date", None)

        if not ts_code:
            return "❌ 错误：股票代码(ts_code)是必填参数！"

        print(f"\n📊 开始布林带异常点检测: {ts_code}")

        engine = get_db_engine()
        
        try:
            # 确定日期范围
            if not start_date or not end_date:
                today = datetime.now()
                if not end_date:
                    end_date = today.strftime('%Y%m%d')
                if not start_date:
                    one_year_ago = today - timedelta(days=365)
                    start_date = one_year_ago.strftime('%Y%m%d')
                print(f"   检测范围: 默认过去一年 ({start_date} 至 {end_date})")
            else:
                print(f"   检测范围: {start_date} 至 {end_date}")
            
            # 查询数据
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
                return f"❌ 错误：未找到股票 {ts_code} 在指定时间范围内的历史数据！"
            
            print(f"   获取到 {len(df_history)} 条历史数据")
            
            # 准备数据
            df_history['trade_date_dt'] = pd.to_datetime(df_history['trade_date'], format='%Y%m%d')
            df_history.set_index('trade_date_dt', inplace=True)
            
            close_prices = df_history['close_price']
            
            # 计算布林带
            window = 20
            num_std = 2
            
            middle_band = close_prices.rolling(window=window).mean()
            std_dev = close_prices.rolling(window=window).std()
            upper_band = middle_band + (std_dev * num_std)
            lower_band = middle_band - (std_dev * num_std)
            
            # 检测异常点
            overbought = close_prices > upper_band
            oversold = close_prices < lower_band
            
            df_overbought = df_history[overbought].copy()
            df_oversold = df_history[oversold].copy()
            
            df_overbought['signal_type'] = '超买'
            df_oversold['signal_type'] = '超卖'
            
            df_anomalies = pd.concat([df_overbought, df_oversold], ignore_index=False)
            df_anomalies = df_anomalies.sort_index()
            
            print(f"   ✅ 检测完成！超买:{len(df_overbought)}, 超卖:{len(df_oversold)}, 总计:{len(df_anomalies)}")
            
            # 构建输出
            md_parts = []
            md_parts.append(f"## 📊 布林带异常点检测结果")
            md_parts.append(f"**股票代码**: {ts_code}")
            md_parts.append(f"**检测范围**: {start_date} 至 {end_date}")
            md_parts.append(f"**数据点数**: {len(df_history)}个交易日")
            md_parts.append(f"**布林带参数**: 20日周期 + 2σ\n")
            
            md_parts.append("### 📈 检测统计")
            md_parts.append(f"- **超买点**（收盘价突破上轨）: {len(df_overbought)} 个")
            md_parts.append(f"- **超卖点**（收盘价跌破下轨）: {len(df_oversold)} 个")
            md_parts.append(f"- **总异常点**: {len(df_anomalies)} 个\n")
            
            # 显示异常点详情
            if len(df_anomalies) > 0:
                md_parts.append("### 🔍 异常点详情")
                
                df_display = df_anomalies.reset_index()
                df_display.rename(columns={'trade_date_dt': '交易日期'}, inplace=True)
                df_display['交易日期'] = df_display['交易日期'].dt.strftime('%Y-%m-%d')
                
                display_cols = ['交易日期', 'close_price', 'signal_type']
                df_show = df_display[display_cols].rename(columns={
                    'close_price': '收盘价',
                    'signal_type': '信号类型'
                })
                
                md_parts.append(df_show.to_markdown(index=False))
                md_parts.append("")
            
            # 生成图表
            img_path = self._plot_bollinger(close_prices, middle_band, upper_band, lower_band,
                                          df_overbought, df_oversold, ts_code, start_date, end_date)
            img_md = f'![布林带检测图]({img_path})'
            
            md_parts.append(img_md)
            md_parts.append("\n**说明**:")
            md_parts.append("- 蓝色线：收盘价")
            md_parts.append("- 红色线：中轨（20日移动平均线）")
            md_parts.append("- 橙色虚线：上轨和下轨（中轨 ± 2倍标准差）")
            md_parts.append("- 红色三角▲：超买点（收盘价突破上轨）")
            md_parts.append("- 绿色三角▼：超卖点（收盘价跌破下轨）")
            md_parts.append("- ⚠️ 检测结果仅供参考，不构成投资建议")
            
            return '\n'.join(md_parts)
            
        except Exception as e:
            error_msg = f"❌ 布林带检测失败: {str(e)}"
            print(error_msg)
            return error_msg

    def _plot_bollinger(self, close_prices, middle_band, upper_band, lower_band,
                       df_overbought, df_oversold, ts_code, start_date, end_date):
        """绘制布林带图表"""
        output_dir = Path(__file__).parent.parent.parent / "data" / "image_show"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f'boll_detection_{ts_code.replace(".", "_")}_{int(time.time() * 1000)}.png'
        save_path = output_dir / filename
        
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # 绘制收盘价
        ax.plot(close_prices.index, close_prices.values, 
               label='收盘价', color='#2E86AB', linewidth=1.5)
        
        # 绘制布林带（移除NaN值）
        middle_band_valid = middle_band.dropna()
        ax.plot(middle_band_valid.index, middle_band_valid.values, 
               label='中轨(20日均线)', color='#FF6B6B', linewidth=2)
        
        upper_band_valid = upper_band.dropna()
        lower_band_valid = lower_band.dropna()
        
        ax.plot(upper_band_valid.index, upper_band_valid.values, 
               label='上轨(中轨+2σ)', color='#FFA500', linewidth=1.5, linestyle='--')
        ax.plot(lower_band_valid.index, lower_band_valid.values, 
               label='下轨(中轨-2σ)', color='#FFA500', linewidth=1.5, linestyle='--')
        
        # 填充区域
        ax.fill_between(upper_band_valid.index, upper_band_valid.values, lower_band_valid.values, 
                       alpha=0.1, color='#FFA500', label='布林带区间')
        
        # 标记异常点
        if len(df_overbought) > 0:
            ax.scatter(df_overbought.index, df_overbought['close_price'], 
                      color='red', marker='^', s=100, zorder=5, label='超买点')
        
        if len(df_oversold) > 0:
            ax.scatter(df_oversold.index, df_oversold['close_price'], 
                      color='green', marker='v', s=100, zorder=5, label='超卖点')
        
        # 设置标题和标签
        ax.set_title(f'{ts_code} 布林带异常点检测\n({start_date} 至 {end_date})', 
                    fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('交易日期', fontsize=13)
        ax.set_ylabel('价格 (元)', fontsize=13)
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 格式化日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return f'data/image_show/{filename}'
