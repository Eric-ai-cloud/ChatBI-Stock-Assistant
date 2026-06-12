-- 股票历史数据表
CREATE TABLE IF NOT EXISTS stock_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code VARCHAR(20) NOT NULL,      -- 股票代码
    stock_name VARCHAR(50) NOT NULL,      -- 股票名称
    trade_date VARCHAR(10) NOT NULL,      -- 交易日期 (YYYYMMDD格式)
    open_price DECIMAL(10,2),             -- 开盘价
    high_price DECIMAL(10,2),             -- 最高价
    low_price DECIMAL(10,2),              -- 最低价
    close_price DECIMAL(10,2),            -- 收盘价
    pre_close DECIMAL(10,2),              -- 昨收价
    change_amount DECIMAL(10,2),          -- 涨跌额
    change_pct DECIMAL(10,4),             -- 涨跌幅(%)
    volume INTEGER,                       -- 成交量(手)
    amount DECIMAL(15,2),                 -- 成交额(千元)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)        -- 确保同一股票同一天只有一条记录
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_stock_code ON stock_history(stock_code);
CREATE INDEX IF NOT EXISTS idx_trade_date ON stock_history(trade_date);
CREATE INDEX IF NOT EXISTS idx_stock_name ON stock_history(stock_name);
CREATE INDEX IF NOT EXISTS idx_trade_date_desc ON stock_history(trade_date DESC);
