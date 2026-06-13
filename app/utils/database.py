"""数据库连接工具"""
import os
from pathlib import Path
from sqlalchemy import create_engine


def get_db_engine(db_path: Path = None):
    """获取数据库连接引擎"""
    if db_path is None:
        db_path = Path(__file__).parent.parent.parent / "data" / "stock_prices.db"
    
    return create_engine(f'sqlite:///{db_path}')
