#!/usr/bin/env python
"""
数据修复脚本
1. 分离日英卡片数据
2. 重新爬取缺失的系列
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage
from loguru import logger


def fix_english_cards():
    """
    修复英文卡片数据 - 将英文卡片移到正确的系列
    """
    app = create_app()
    
    with app.app_context():
        logger.info("=== 修复英文卡片数据 ===")
        
        # 获取所有日文系列
        jp_series = Series.query.filter_by(language='jp').all()
        
        for series in jp_series:
            # 检查该系列是否有英文卡片
            en_cards = Card.query.filter_by(series_id=series.id, language='en').all()
            
            if not en_cards:
                continue
            
            logger.info(f"{series.code}: 发现 {len(en_cards)} 张英文卡片")
            
            # 查找或创建对应的英文系列
            en_series = Series.query.filter_by(
                code=series.code,
                language='en'
            ).first()
            
            if not en_series:
                # 创建英文系列
                en_series = Series(
                    code=series.code,
                    language='en',
                    name=series.name.replace('【', ' [').replace('】', ']'),  # 简单转换
                    series_type=series.series_type,
                    official_series_id=series.official_series_id
                )
                db.session.add(en_series)
                db.session.flush()
                logger.info(f"  创建英文系列: {en_series.code} (ID: {en_series.id})")
            
            # 移动英文卡片到英文系列
            for card in en_cards:
                card.series_id = en_series.id
            
            logger.info(f"  已移动 {len(en_cards)} 张卡片到英文系列")
        
        db.session.commit()
        logger.info("英文卡片修复完成")


def get_series_to_rescrape():
    """
    获取需要重新爬取的系列列表
    """
    app = create_app()
    
    # 官网实际数量 (从浏览器验证)
    OFFICIAL_COUNTS = {
        'OP-01': 121, 'OP-02': 121, 'OP-03': 122, 'OP-04': 121,
        'OP-05': 120, 'OP-06': 129, 'OP-07': 142, 'OP-08': 142,
        'OP-09': 137, 'OP-10': 144, 'OP-11': 144, 'OP-12': 144,
        'OP-13': 144, 'OP-14': 156,
        'EB-01': 88, 'EB-02': 173, 'EB-03': 124, 'EB-04': 96,
        'PRB-01': 216, 'PRB-02': 347,
        'ST-01': 17, 'ST-02': 17, 'ST-03': 17, 'ST-04': 17,
        'ST-05': 17, 'ST-06': 17, 'ST-07': 17, 'ST-08': 17,
        'ST-09': 17, 'ST-10': 17, 'ST-11': 15, 'ST-12': 17,
        'ST-13': 17, 'ST-14': 17, 'ST-15': 17, 'ST-16': 17,
        'ST-17': 17, 'ST-18': 17, 'ST-19': 17, 'ST-20': 17,
        'ST-21': 26, 'ST-22': 17, 'ST-23': 17, 'ST-24': 17,
        'ST-25': 17, 'ST-26': 17, 'ST-27': 17, 'ST-28': 17,
        'ST-29': 17,
    }
    
    to_rescrape = []
    
    with app.app_context():
        for code, official_count in OFFICIAL_COUNTS.items():
            series = Series.query.filter_by(code=code, language='jp').first()
            if not series:
                to_rescrape.append((code, None, official_count, 0))
                continue
            
            db_count = Card.query.filter_by(series_id=series.id, language='jp').count()
            
            # 如果数量差距超过 10%，需要重新爬取
            if db_count < official_count * 0.9:
                to_rescrape.append((code, series.official_series_id, official_count, db_count))
    
    return to_rescrape


def show_status():
    """显示当前数据状态"""
    app = create_app()
    
    with app.app_context():
        print("\n=== 当前数据状态 ===")
        
        jp_cards = Card.query.filter_by(language='jp').count()
        en_cards = Card.query.filter_by(language='en').count()
        jp_series = Series.query.filter_by(language='jp').count()
        en_series = Series.query.filter_by(language='en').count()
        
        print(f"日文系列: {jp_series}")
        print(f"英文系列: {en_series}")
        print(f"日文卡片: {jp_cards}")
        print(f"英文卡片: {en_cards}")
        
        print("\n=== 需要重新爬取的系列 ===")
        to_rescrape = get_series_to_rescrape()
        
        if not to_rescrape:
            print("所有系列数据完整！")
        else:
            for code, series_id, official, db_count in to_rescrape:
                diff = official - db_count
                print(f"  {code}: 缺少 {diff} 张 (数据库 {db_count}/{official})")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据修复工具')
    parser.add_argument('--fix-english', action='store_true', help='修复英文卡片数据')
    parser.add_argument('--status', action='store_true', help='显示数据状态')
    parser.add_argument('--list-missing', action='store_true', help='列出缺失的系列')
    
    args = parser.parse_args()
    
    if args.fix_english:
        fix_english_cards()
    elif args.status:
        show_status()
    elif args.list_missing:
        to_rescrape = get_series_to_rescrape()
        for code, series_id, official, db_count in to_rescrape:
            print(f"{code},{series_id},{official},{db_count}")
    else:
        parser.print_help()
