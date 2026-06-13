"""ARIMA股票预测工具 - NanoBot版本"""
import json
import os
import time
import warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import text
from statsmodels.tsa.arima.model import ARIMA

from nanobot.agent.tools.base import Tool
from app.utils.database import get_db_engine


class ArimaStockTool(Tool):
    """ARIMA股票价格预测工具"""

    def __init__(self):
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        warnings.filterwarnings('ignore')

    @property
    def name(self) -> str:
        return "arima_stock"

    @property
    def description(self) -> str:
        return (
            "Use ARIMA(5,1,5) model to predict future stock prices. "
            "Based on one year of historical data, predicts N days of closing prices."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ts_code": {
                    "type": "string",
                    "description": "Stock code (required), e.g., 600519.SH, 000858.SZ"
                },
                "n": {
                    "type": "integer",
                    "description": "Number of days to predict (optional, default 7)"
                }
            },
            "required": ["ts_code"]
        }

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        ts_code = kwargs.get("ts_code")
        n_days = kwargs.get("n", 7)

        if not ts_code:
            return "❌ 错误：股票代码(ts_code)是必填参数！"

        print(f"\n🔮 开始ARIMA预测: {ts_code}, 预测{n_days}天")

        engine = get_db_engine()
        
        try:
            # 获取历史数据
            today = datetime.now()
            one_year_ago = today - timedelta(days=365)
            start_date_str = one_year_ago.strftime('%Y%m%d')
            
            query_sql = f"""
            SELECT trade_date, close_price 
            FROM stock_history 
            WHERE stock_code = '{ts_code}' 
              AND trade_date >= '{start_date_str}'
            ORDER BY trade_date ASC
            """
            
            df_history = pd.read_sql(text(query_sql), engine)
            
            if len(df_history) == 0:
                return f"❌ 错误：未找到股票 {ts_code} 的历史数据！"
            
            print(f"   获取到 {len(df_history)} 条历史数据")
            
            # 准备时间序列数据
            df_history['trade_date_dt'] = pd.to_datetime(df_history['trade_date'], format='%Y%m%d')
            df_history.set_index('trade_date_dt', inplace=True)
            ts_data = df_history['close_price'].copy()
            
            print(f"   📊 时间序列数据点数: {len(ts_data)}")
            
            # 训练ARIMA模型
            print(f"   正在训练ARIMA(5,1,5)模型...")
            model = ARIMA(ts_data, order=(5, 1, 5))
            model_fit = model.fit()
            
            # 预测
            print(f"   正在预测未来{n_days}天的价格...")
            forecast_result = model_fit.get_forecast(steps=n_days)
            forecast_mean = forecast_result.predicted_mean
            forecast_ci = forecast_result.conf_int()
            
            # 生成预测日期
            last_date = ts_data.index[-1]
            forecast_dates = self._generate_trading_dates(last_date, n_days)
            
            print(f"   📅 预测日期范围: {forecast_dates[0].strftime('%Y-%m-%d')} 至 {forecast_dates[-1].strftime('%Y-%m-%d')}")
            
            # 构建预测结果
            df_forecast = pd.DataFrame({
                'forecast_date': forecast_dates.strftime('%Y%m%d'),
                'predicted_price': forecast_mean.values,
                'lower_ci': forecast_ci.iloc[:, 0].values,
                'upper_ci': forecast_ci.iloc[:, 1].values
            })
            
            print(f"   ✅ 预测完成！价格范围: {df_forecast['predicted_price'].min():.2f} - {df_forecast['predicted_price'].max():.2f}")
            
            # 构建输出
            md_parts = []
            md_parts.append(f"## 📈 ARIMA股票价格预测结果")
            md_parts.append(f"**股票代码**: {ts_code}")
            md_parts.append(f"**预测天数**: {n_days}天")
            md_parts.append(f"**历史数据**: {len(ts_data)}条（过去一年）")
            md_parts.append(f"**模型**: ARIMA(5,1,5)\n")
            
            md_parts.append("### 🔮 预测结果")
            md_parts.append(df_forecast.to_markdown(index=False))
            md_parts.append("")
            
            # 生成图表
            img_path = self._plot_forecast(ts_data, forecast_dates, forecast_mean, forecast_ci, n_days)
            img_md = f'![ARIMA预测图]({img_path})'
            
            md_parts.append(img_md)
            md_parts.append("\n**说明**:")
            md_parts.append("- 蓝色线：历史收盘价（最近60天）")
            md_parts.append("- 紫色线：预测价格")
            md_parts.append("- 紫色阴影：95%置信区间")
            md_parts.append("- ⚠️ 预测仅供参考，不构成投资建议")
            
            return '\n'.join(md_parts)
            
        except Exception as e:
            error_msg = f"❌ ARIMA预测失败: {str(e)}"
            print(error_msg)
            return error_msg

    def _generate_trading_dates(self, last_date, n_days):
        """生成未来交易日（排除周末和常见节假日）"""
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
            if month == 1 and day == 1:  # 元旦
                is_holiday = True
            elif month == 5 and day == 1:  # 劳动节
                is_holiday = True
            elif month == 10 and day <= 3:  # 国庆节
                is_holiday = True
            elif month == 2 and day <= 5:  # 春节（近似）
                is_holiday = True
            
            if not is_holiday:
                forecast_dates.append(current_date)
            
            current_date += pd.Timedelta(days=1)
        
        return pd.DatetimeIndex(forecast_dates)

    def _plot_forecast(self, ts_data, forecast_dates, forecast_mean, forecast_ci, n_days):
        """绘制ARIMA预测图表"""
        output_dir = Path(__file__).parent.parent.parent / "data" / "image_show"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f'arima_forecast_{ts_data.name or "stock"}_{int(time.time() * 1000)}.png'
        save_path = output_dir / filename
        
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # 绘制历史数据
        ax.plot(ts_data.index, ts_data.values, 
               label='历史收盘价', color='#2E86AB', linewidth=1.5, alpha=0.7)
        
        # 突出显示最近60天
        recent_history = ts_data.tail(60)
        ax.plot(recent_history.index, recent_history.values, 
               color='#2E86AB', linewidth=2.5, marker='o', markersize=4, alpha=1.0)
        
        # 添加连接点
        last_history_date = recent_history.index[-1]
        last_history_price = recent_history.values[-1]
        
        connected_dates = [last_history_date] + list(forecast_dates)
        connected_prices = [last_history_price] + list(forecast_mean.values)
        
        # 绘制预测线
        ax.plot(connected_dates, connected_prices, 
               label='预测价格', color='#A23B72', linewidth=2.5, marker='s', markersize=6, linestyle='--')
        
        # 绘制置信区间
        connected_lower = [last_history_price] + list(forecast_ci.iloc[:, 0].values)
        connected_upper = [last_history_price] + list(forecast_ci.iloc[:, 1].values)
        ax.fill_between(connected_dates, 
                       connected_lower,
                       connected_upper,
                       alpha=0.15, color='#A23B72', label='95%置信区间')
        
        # 添加分隔线
        ax.axvline(x=last_history_date, color='gray', linestyle=':', linewidth=1.5, alpha=0.5)
        
        # 设置标题和标签
        ax.set_title(f'{ts_data.name or "股票"} 价格预测 (ARIMA模型)', 
                    fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('交易日期', fontsize=13)
        ax.set_ylabel('收盘价 (元)', fontsize=13)
        ax.legend(loc='best', fontsize=11, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 格式化日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.xticks(rotation=45, ha='right')
        
        # 添加标注
        ax.text(last_history_date, last_history_price * 1.02, 
               f'今天\n{last_history_date.strftime("%Y-%m-%d")}',
               ha='center', va='bottom', fontsize=9, 
               bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3))
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return f'data/image_show/{filename}'
