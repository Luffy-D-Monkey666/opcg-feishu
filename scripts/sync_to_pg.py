#!/usr/bin/env python3
"""
快速同步本地 SQLite 到 PostgreSQL
使用 pandas 和 SQLAlchemy 批量插入
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import create_engine, text

POSTGRES_URL = os.environ.get('DATABASE_URL')
if not POSTGRES_URL:
    print("请设置 DATABASE_URL")
    sys.exit(1)

# SQLite 数据库
SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'opcg_dev.db')
sqlite_engine = create_engine(f'sqlite:///{SQLITE_PATH}')

# PostgreSQL 数据库
pg_engine = create_engine(POSTGRES_URL)

def sync_table(table_name):
    """同步单个表"""
    print(f"同步 {table_name}...")
    
    # 从 SQLite 读取
    df = pd.read_sql_table(table_name, sqlite_engine)
    print(f"  读取 {len(df)} 行")
    
    if len(df) == 0:
        print("  空表，跳过")
        return
    
    # 清空 PostgreSQL 表
    with pg_engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
        conn.commit()
    
    # 批量插入到 PostgreSQL
    df.to_sql(table_name, pg_engine, if_exists='append', index=False, method='multi', chunksize=500)
    
    # 重置序列（如果有 id 列）
    if 'id' in df.columns:
        with pg_engine.connect() as conn:
            try:
                conn.execute(text(f"""
                    SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), 
                           COALESCE((SELECT MAX(id) FROM {table_name}), 1))
                """))
                conn.commit()
            except:
                pass
    
    print(f"  完成")

def main():
    print("开始同步数据到 PostgreSQL...\n")
    
    # 按顺序同步（先父表后子表）
    tables = [
        'series',
        'cards',
        'card_series',
        'card_versions',
        'card_images',
    ]
    
    for table in tables:
        try:
            sync_table(table)
        except Exception as e:
            print(f"  错误: {e}")
    
    print("\n同步完成!")

if __name__ == '__main__':
    main()
