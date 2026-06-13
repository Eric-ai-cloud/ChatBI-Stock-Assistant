"""日期处理工具"""
from datetime import datetime, timedelta


def calculate_date_range(latest_date_str: str, days: int = 30) -> tuple[str, str]:
    """
    计算日期范围
    
    Args:
        latest_date_str: 最新日期字符串 (YYYYMMDD)
        days: 往前推的天数
    
    Returns:
        (start_date_str, end_date_str)
    """
    latest_date = datetime.strptime(str(latest_date_str), '%Y%m%d')
    start_date = latest_date - timedelta(days=days)
    
    return start_date.strftime('%Y%m%d'), latest_date.strftime('%Y%m%d')
