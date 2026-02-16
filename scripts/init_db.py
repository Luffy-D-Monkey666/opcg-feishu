#!/usr/bin/env python3
"""
初始化数据库
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def init_database():
    """创建所有数据库表"""
    app = create_app()
    with app.app_context():
        db.create_all()
        print("✅ 数据库表创建完成")

if __name__ == '__main__':
    init_database()
