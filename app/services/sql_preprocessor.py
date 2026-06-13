"""SQL预处理服务"""
import re
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import text
from app.utils.database import get_db_engine


class SQLPreprocessor:
    """SQL智能预处理器"""
    
    def preprocess(self, sql_input: str) -> str:
        """
        预处理SQL：检测并修正常见问题
        
        1. 字符串日期算术运算
        2. LIMIT 30 转换为自然月30天
        """
        # 检测并修正字符串日期算术运算
        arithmetic_pattern = r'trade_date\s*>=\s*\(?\s*SELECT\s+MAX\(trade_date\).*?\)?\s*-\s*\d+'
        
        if re.search(arithmetic_pattern, sql_input, re.IGNORECASE | re.DOTALL):
            print("⚠️ 检测到字符串日期算术运算，正在修正...")
            return self._fix_arithmetic_date(sql_input)
        
        # 检测 LIMIT 30 模式
        pattern = r'ORDER\s+BY\s+trade_date\s+DESC\s+LIMIT\s+30'
        
        if re.search(pattern, sql_input, re.IGNORECASE):
            print("⚠️ 检测到'最近一个月'查询（LIMIT 30），正在转换...")
            return self._convert_limit_to_date_range(sql_input)
        
        return sql_input
    
    def _fix_arithmetic_date(self, sql_input: str) -> str:
        """修正字符串日期算术运算"""
        stock_code_match = re.search(r"stock_code\s*=\s*['\"]([^'\"]+)['\"]", sql_input)
        if not stock_code_match:
            return sql_input
        
        stock_code = stock_code_match.group(1)
        engine = get_db_engine()
        
        try:
            latest_date_sql = f"SELECT MAX(trade_date) as max_date FROM stock_history WHERE stock_code = '{stock_code}'"
            df_latest = pd.read_sql(text(latest_date_sql), engine)
            latest_date_str = df_latest['max_date'].iloc[0]
            
            if not latest_date_str:
                return sql_input
            
            start_date_str, _ = self._calculate_date_range(latest_date_str, 30)
            
            # 替换所有出现的地方
            pattern1 = r"trade_date\s*>=\s*\(?\s*SELECT\s+MAX\(trade_date\)\s+FROM\s+stock_history\s+WHERE\s+stock_code\s*=\s*['\"][^'\"]+['\"]\s*\)?\s*-\s*\d+"
            new_sql = re.sub(pattern1, f"trade_date >= '{start_date_str}'", sql_input, flags=re.IGNORECASE | re.DOTALL)
            
            if new_sql == sql_input:
                pattern2 = r"trade_date\s*>=\s*\(?.*?MAX\(trade_date\).*?\)?\s*-\s*\d+"
                new_sql = re.sub(pattern2, f"trade_date >= '{start_date_str}'", sql_input, flags=re.IGNORECASE | re.DOTALL)
            
            print(f"   ✅ SQL已修正为具体日期范围查询")
            return new_sql
                
        except Exception as e:
            print(f"   ❌ SQL预处理失败: {str(e)}")
            return sql_input
    
    def _convert_limit_to_date_range(self, sql_input: str) -> str:
        """将LIMIT 30转换为具体日期范围"""
        stock_code_match = re.search(r"stock_code\s*=\s*['\"]([^'\"]+)['\"]", sql_input)
        if not stock_code_match:
            return sql_input
        
        stock_code = stock_code_match.group(1)
        engine = get_db_engine()
        
        try:
            latest_date_sql = f"SELECT MAX(trade_date) as max_date FROM stock_history WHERE stock_code = '{stock_code}'"
            df_latest = pd.read_sql(text(latest_date_sql), engine)
            latest_date_str = df_latest['max_date'].iloc[0]
            
            if not latest_date_str:
                return sql_input
            
            start_date_str, _ = self._calculate_date_range(latest_date_str, 30)
            
            # 匹配子查询模式
            subquery_pattern = r'FROM\s*\(\s*SELECT\s+(.*?)\s+FROM\s+stock_history\s+WHERE\s+stock_code\s*=\s*[\'"][^\'"]+[\'"]\s+ORDER\s+BY\s+trade_date\s+DESC\s+LIMIT\s+30\s*\)\s*ORDER\s+BY\s+trade_date\s+ASC'
            
            match = re.search(subquery_pattern, sql_input, re.IGNORECASE | re.DOTALL)
            if match:
                select_fields = match.group(1).strip()
                new_sql = f"""SELECT {select_fields} 
FROM stock_history 
WHERE stock_code = '{stock_code}' 
  AND trade_date >= '{start_date_str}'
ORDER BY trade_date ASC"""
                
                print(f"   ✅ SQL已修正为自然月30天查询")
                return new_sql
            else:
                # 备选方案
                if 'WHERE' in sql_input.upper():
                    new_sql = re.sub(
                        r'(WHERE\s+stock_code\s*=\s*[\'"][^\'"]+[\'"])',
                        f"\\1 AND trade_date >= '{start_date_str}'",
                        sql_input,
                        flags=re.IGNORECASE
                    )
                    new_sql = re.sub(r'\s+LIMIT\s+30', '', new_sql, flags=re.IGNORECASE)
                    return new_sql
                
        except Exception as e:
            print(f"   ❌ SQL预处理失败: {str(e)}")
            return sql_input
        
        return sql_input
    
    def _calculate_date_range(self, latest_date_str: str, days: int) -> tuple[str, str]:
        """计算日期范围"""
        from app.utils.date_utils import calculate_date_range
        return calculate_date_range(latest_date_str, days)
