"""
从 CSV 导入数据到 PostgreSQL
"""
import os
import sys
import csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

POSTGRES_URL = os.environ.get('DATABASE_URL')
if not POSTGRES_URL:
    print("请设置 DATABASE_URL")
    sys.exit(1)

engine = create_engine(POSTGRES_URL)

def import_csv(table_name, csv_path):
    """导入 CSV 到表"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print(f"  {table_name}: 空文件")
        return
    
    columns = list(rows[0].keys())
    
    with engine.connect() as conn:
        # 清空表
        conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
        conn.commit()
        
        # 批量插入
        col_names = ', '.join(columns)
        placeholders = ', '.join([f':{c}' for c in columns])
        sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        
        count = 0
        for row in rows:
            # 处理空值和类型转换
            clean_row = {}
            int_cols = {'id', 'cost', 'life', 'power', 'counter', 'block_icon', 'series_id', 
                        'card_id', 'card_count', 'is_reprint', 'has_star_mark', 'version_id', 'listing_count'}
            for k, v in row.items():
                if v == '' or v == 'None':
                    clean_row[k] = None
                elif k in int_cols and v is not None:
                    # 转换为整数（处理 '1.0' 这样的浮点数字符串）
                    try:
                        clean_row[k] = int(float(v))
                    except:
                        clean_row[k] = None
                else:
                    clean_row[k] = v
            try:
                conn.execute(text(sql), clean_row)
                count += 1
            except Exception as e:
                print(f"  错误: {e}")
                break
        
        conn.commit()
        
        # 重置序列
        try:
            conn.execute(text(f"""
                SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), 
                       COALESCE((SELECT MAX(id) FROM {table_name}), 1))
            """))
            conn.commit()
        except:
            pass
        
        print(f"  {table_name}: {count} 行")

def main():
    print("导入数据...\n")
    
    tables = [
        ('series', 'data/series.csv'),
        ('cards', 'data/cards.csv'),
        ('card_series', 'data/card_series.csv'),
        ('card_versions', 'data/card_versions.csv'),
    ]
    
    for table, csv_path in tables:
        if os.path.exists(csv_path):
            import_csv(table, csv_path)
        else:
            print(f"  {table}: CSV 不存在")
    
    print("\n完成!")

if __name__ == '__main__':
    main()
