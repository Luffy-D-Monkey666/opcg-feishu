#!/usr/bin/env python3
"""
更新卡片版本的入手情报 (source_description)
从官网重新爬取数据并更新数据库
"""
import sys
sys.path.insert(0, '/workspace/opcg-tcg')

import time
from loguru import logger
from scrapers.jp_official import JapanOfficialScraper
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion

# 配置日志
logger.add("/workspace/opcg-tcg/logs/update_source_{time:YYYY-MM-DD}.log", rotation="1 day")


def update_source_info_for_series(series_code: str = None):
    """更新系列的入手情报"""
    app = create_app()
    
    with app.app_context():
        scraper = JapanOfficialScraper()
        
        try:
            scraper.start_browser()
            
            # 获取要处理的系列
            if series_code:
                series_list = Series.query.filter_by(code=series_code, language='jp').all()
            else:
                series_list = Series.query.filter_by(language='jp').all()
            
            if not series_list:
                logger.error(f"未找到系列")
                return
            
            # 获取官网系列ID映射
            official_series = scraper.get_series_list()
            series_id_map = {s['code']: s['official_series_id'] for s in official_series}
            
            total_updated = 0
            
            for series in series_list:
                if series.code not in series_id_map:
                    logger.warning(f"系列 {series.code} 在官网未找到，跳过")
                    continue
                
                logger.info(f"处理系列: {series.code}")
                
                # 爬取系列卡片
                official_id = series_id_map[series.code]
                cards_data = scraper.scrape_series(official_id, download_images=False)
                
                # 建立卡号到入手情报的映射
                # key: (card_number, version_index) -> source_info
                source_map = {}
                for card in cards_data:
                    key = (card.card_number, card.version_index)
                    source_map[key] = card.source_info
                
                # 更新数据库中的版本
                versions = CardVersion.query.filter_by(series_id=series.id).all()
                updated = 0
                
                for version in versions:
                    card = version.card
                    # 确定 version_index
                    if version.version_suffix:
                        try:
                            version_index = int(version.version_suffix.replace('_v', ''))
                        except:
                            version_index = 0
                    else:
                        version_index = 0
                    
                    key = (card.card_number, version_index)
                    if key in source_map and source_map[key]:
                        if version.source_description != source_map[key]:
                            version.source_description = source_map[key]
                            updated += 1
                
                db.session.commit()
                total_updated += updated
                logger.info(f"系列 {series.code}: 更新 {updated} 个版本的入手情报")
                
                # 避免请求过快
                time.sleep(1)
            
            logger.info(f"\n=== 更新完成 ===")
            logger.info(f"总计更新 {total_updated} 个版本")
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='更新卡片入手情报')
    parser.add_argument('--series', type=str, help='指定系列代码 (如 OP-14)')
    parser.add_argument('--all', action='store_true', help='更新所有系列')
    
    args = parser.parse_args()
    
    if args.series:
        update_source_info_for_series(args.series)
    elif args.all:
        update_source_info_for_series()
    else:
        print("请指定 --series <代码> 或 --all")
        print("示例:")
        print("  python update_source_info.py --series OP-14")
        print("  python update_source_info.py --all")
