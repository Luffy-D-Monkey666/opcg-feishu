"""
从本地 SQLite 迁移数据到 PostgreSQL
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 源数据库 (SQLite)
SQLITE_URL = 'sqlite:///data/opcg_dev.db'

# 目标数据库 (PostgreSQL) - 从环境变量获取
POSTGRES_URL = os.environ.get('DATABASE_URL')
if not POSTGRES_URL:
    print("请设置 DATABASE_URL 环境变量")
    sys.exit(1)

print(f"源数据库: {SQLITE_URL}")
print(f"目标数据库: {POSTGRES_URL[:50]}...")

# 创建引擎
sqlite_engine = create_engine(SQLITE_URL)
postgres_engine = create_engine(POSTGRES_URL)

SqliteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

# 需要迁移的表（按依赖顺序）
TABLES = [
    'series',
    'cards',
    'card_series',
    'card_versions',
    'card_images',
    'users',
    'user_collections',
    'wishlists',
    'decks',
    'deck_cards',
    'price_history'
]

def migrate_table(table_name):
    """迁移单个表"""
    sqlite_session = SqliteSession()
    postgres_session = PostgresSession()
    
    try:
        # 获取源数据
        result = sqlite_session.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        columns = result.keys()
        
        if not rows:
            print(f"  {table_name}: 0 行 (跳过)")
            return 0
        
        # 清空目标表
        postgres_session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
        
        # 批量插入
        col_names = ', '.join(columns)
        placeholders = ', '.join([f':{col}' for col in columns])
        insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        
        batch_size = 100
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            for row in batch:
                row_dict = dict(zip(columns, row))
                postgres_session.execute(text(insert_sql), row_dict)
        
        postgres_session.commit()
        print(f"  {table_name}: {len(rows)} 行")
        return len(rows)
        
    except Exception as e:
        postgres_session.rollback()
        print(f"  {table_name}: 错误 - {e}")
        return 0
    finally:
        sqlite_session.close()
        postgres_session.close()

def reset_sequences():
    """重置 PostgreSQL 序列"""
    postgres_session = PostgresSession()
    try:
        for table in TABLES:
            try:
                postgres_session.execute(text(f"""
                    SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                           COALESCE((SELECT MAX(id) FROM {table}), 1))
                """))
            except:
                pass
        postgres_session.commit()
        print("\n序列已重置")
    finally:
        postgres_session.close()

def main():
    print("\n开始迁移数据...\n")
    
    total = 0
    for table in TABLES:
        count = migrate_table(table)
        total += count
    
    reset_sequences()
    print(f"\n迁移完成！共 {total} 条记录")

if __name__ == '__main__':
    main()
