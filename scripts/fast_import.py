"""
使用 COPY 命令快速导入数据到 PostgreSQL
"""
import os
import sys
import io
import csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

POSTGRES_URL = os.environ.get('DATABASE_URL')
if not POSTGRES_URL:
    print("请设置 DATABASE_URL")
    sys.exit(1)

conn = psycopg2.connect(POSTGRES_URL)
cur = conn.cursor()

def process_value(v, col, int_cols):
    """处理值"""
    if v == '' or v == 'None' or v is None:
        return ''  # NULL in COPY format
    if col in int_cols:
        try:
            return str(int(float(v)))
        except:
            return ''
    # 转义特殊字符
    return str(v).replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')

def import_table(table_name, csv_path, int_cols):
    """使用 COPY 导入表"""
    if not os.path.exists(csv_path):
        print(f"  {table_name}: CSV 不存在")
        return 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print(f"  {table_name}: 空文件")
        return 0
    
    columns = list(rows[0].keys())
    
    # 清空表
    cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
    conn.commit()
    
    # 准备 COPY 数据 (tab-separated)
    output = io.StringIO()
    for row in rows:
        values = []
        for col in columns:
            v = process_value(row.get(col), col, int_cols)
            if v == '':
                values.append('\\N')  # NULL
            else:
                values.append(v)
        output.write('\t'.join(values) + '\n')
    
    output.seek(0)
    
    # 使用 COPY 导入
    try:
        cur.copy_from(output, table_name, columns=columns, null='\\N')
        conn.commit()
        
        # 重置序列
        try:
            cur.execute(f"""
                SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), 
                       COALESCE((SELECT MAX(id) FROM {table_name}), 1))
            """)
            conn.commit()
        except:
            pass
        
        print(f"  {table_name}: {len(rows)} 行 ✓")
        return len(rows)
    except Exception as e:
        conn.rollback()
        print(f"  {table_name}: 错误 - {e}")
        return 0

def main():
    print("快速导入数据...\n")
    
    int_cols = {'id', 'cost', 'life', 'power', 'counter', 'block_icon', 'series_id', 
                'card_id', 'card_count', 'is_reprint', 'has_star_mark', 'version_id', 'listing_count'}
    
    tables = [
        ('series', 'data/series.csv'),
        ('cards', 'data/cards.csv'),
        ('card_series', 'data/card_series.csv'),
        ('card_versions', 'data/card_versions.csv'),
    ]
    
    total = 0
    for table, csv_path in tables:
        count = import_table(table, csv_path, int_cols)
        total += count
    
    print(f"\n完成！共导入 {total} 条记录")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
