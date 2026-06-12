"""
快速测试：验证FAQ和system_prompt的修复效果
模拟LLM可能生成的SQL，检查是否正确
"""

def test_sql_patterns():
    """测试常见SQL模式的正确性"""
    
    print("="*70)
    print("SQL模式验证测试")
    print("="*70)
    
    # ❌ 错误的SQL模式
    wrong_patterns = [
        "WHERE trade_date >= MAX(trade_date) - 30",
        "WHERE trade_date >= (SELECT MAX(trade_date) - 30 FROM stock_history)",
        "WHERE trade_date >= trade_date - 7",
    ]
    
    # ✅ 正确的SQL模式
    correct_patterns = [
        "ORDER BY trade_date DESC LIMIT 30",
        "SELECT * FROM (SELECT ... ORDER BY trade_date DESC LIMIT 30) ORDER BY trade_date ASC",
        "WHERE trade_date >= '20240101' AND trade_date <= '20240131'",
    ]
    
    print("\n❌ 禁止的SQL模式（应该避免）：")
    for i, pattern in enumerate(wrong_patterns, 1):
        print(f"{i}. {pattern}")
    
    print("\n✅ 推荐的SQL模式（应该使用）：")
    for i, pattern in enumerate(correct_patterns, 1):
        print(f"{i}. {pattern}")
    
    print("\n" + "="*70)
    print("修复要点总结：")
    print("="*70)
    print("1. trade_date 是 VARCHAR 类型，不能进行算术运算")
    print("2. 相对时间查询使用：ORDER BY trade_date DESC LIMIT N")
    print("3. 需要升序展示时使用子查询嵌套")
    print("4. 具体日期范围使用字符串比较：>= 'YYYYMMDD' AND <= 'YYYYMMDD'")
    print("="*70)


if __name__ == '__main__':
    test_sql_patterns()
