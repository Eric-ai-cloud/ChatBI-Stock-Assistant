"""SQL查询工具 - NanoBot版本"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Any
from sqlalchemy import text

from nanobot.agent.tools.base import Tool
from app.utils.database import get_db_engine
from app.services.sql_preprocessor import SQLPreprocessor
from app.services.chart_generator import ChartGenerator


class ExcSQLTool(Tool):
    """SQL查询工具，执行SQL并自动可视化"""

    def __init__(self):
        self.preprocessor = SQLPreprocessor()
        self.chart_generator = ChartGenerator()

    @property
    def name(self) -> str:
        return "exc_sql"

    @property
    def description(self) -> str:
        return (
            "Execute SQL query against stock database and auto-generate visualization. "
            "Returns formatted data preview and chart image path."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql_input": {
                    "type": "string",
                    "description": "SQL query to execute (SELECT only)"
                }
            },
            "required": ["sql_input"]
        }

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        sql_input = kwargs.get("sql_input", "").strip()
        
        if not sql_input:
            return "Error: empty SQL query"

        print(f'原始sql_input: {sql_input}')

        # 智能SQL预处理
        sql_input = self.preprocessor.preprocess(sql_input)
        print(f'处理后sql_input: {sql_input}')

        engine = get_db_engine()
        
        try:
            # 执行SQL查询
            df = pd.read_sql(text(sql_input), engine)
            print(f'df shape: {df.shape}')

            # 如果只有一行数据，直接返回表格
            if len(df) == 1:
                return self._format_single_row(df)
            
            # 构建数据预览
            md_parts = []
            md_parts.append(f"**数据概览**: 共 {len(df)} 行, {len(df.columns)} 列")
            md_parts.append(f"**字段列表**: {', '.join(df.columns.tolist())}\n")
            
            # 前5行数据
            if len(df) > 0:
                md_parts.append("### 📋 前5行数据")
                head_df = df.head(5)
                md_parts.append(head_df.to_markdown(index=False))
                md_parts.append("")
            
            # 后5行数据（如果数据量大于10）
            if len(df) > 10:
                md_parts.append("### 📋 后5行数据")
                tail_df = df.tail(5)
                md_parts.append(tail_df.to_markdown(index=False))
                md_parts.append("")
            
            # 描述统计信息
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0 and len(df) > 1:
                md_parts.append("### 📊 数值列统计信息")
                desc_df = df[numeric_cols].describe().round(2)
                md_parts.append(desc_df.to_markdown())
                md_parts.append("")
                
                # 🔥 新增：显式标注极值信息，帮助LLM准确引用
                if 'trade_date' in df.columns:
                    extreme_info = self._extract_extreme_values(df, numeric_cols)
                    if extreme_info:
                        md_parts.append("### ⚠️ 关键极值点（请准确引用以下信息）")
                        md_parts.append(extreme_info)
                        md_parts.append("")
            
            md = '\n'.join(md_parts)
            
            # 生成图表
            img_path = self.chart_generator.generate_smart_chart(df)
            
            # 🔧 修复：将相对路径转换为绝对路径，确保 WebUI 能正确显示
            # Gradio 需要完整的文件路径或 base64 编码
            from pathlib import Path
            abs_img_path = Path(img_path).resolve()
            
            # 使用 file:// 协议或完整路径
            img_md = f'![股票走势图]({abs_img_path})'
            
            return f"{md}\n\n{img_md}"
            
        except Exception as e:
            error_msg = f"SQL执行错误: {str(e)}\n请检查SQL语句是否正确。"
            print(error_msg)
            return error_msg
    
    def _format_single_row(self, df: pd.DataFrame) -> str:
        """格式化单行数据"""
        md_parts = []
        md_parts.append("**查询结果** (1行数据)\n")
        md_parts.append(df.to_markdown(index=False))
        return '\n'.join(md_parts)

    def _extract_extreme_values(self, df: pd.DataFrame, numeric_cols: list) -> str:
        """提取并格式化极值信息，帮助LLM准确引用"""
        if 'trade_date' not in df.columns:
            return ""
        
        lines = []
        
        # 查找包含价格的列
        price_cols = [col for col in numeric_cols if 'price' in col.lower()]
        
        if price_cols:
            for col in price_cols:
                max_idx = df[col].idxmax()
                min_idx = df[col].idxmin()
                
                max_date = df.loc[max_idx, 'trade_date']
                max_val = df.loc[max_idx, col]
                min_date = df.loc[min_idx, 'trade_date']
                min_val = df.loc[min_idx, col]
                
                col_name_cn = {
                    'high_price': '最高价',
                    'low_price': '最低价',
                    'close_price': '收盘价',
                    'open_price': '开盘价'
                }.get(col, col)
                
                lines.append(f"- **{col_name_cn}最高值**: {max_val:.2f}元 (日期: {max_date})")
                lines.append(f"- **{col_name_cn}最低值**: {min_val:.2f}元 (日期: {min_date})")
        
        return '\n'.join(lines) if lines else ""
