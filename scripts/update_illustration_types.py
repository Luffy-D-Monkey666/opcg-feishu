#!/usr/bin/env python3
"""
更新卡片版本的插画类型 (illustration_type)
从官网爬取数据并更新数据库
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
logger.add("/workspace/opcg-tcg/logs/update_illust_{time:YYYY-MM-DD}.log", rotation="1 day")


def update_illustration_types(series_code: str = None):
    """更新系列的插画类型"""
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
                logger.error("未找到系列")
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
                
                # 爬取插画类型
                official_id = series_id_map[series.code]
                ill_types = scraper.scrape_illustration_types(official_id)
                
                if not ill_types:
                    logger.warning(f"系列 {series.code} 未获取到插画类型数据")
                    continue
                
                # 更新数据库中的版本
                versions = CardVersion.query.filter_by(series_id=series.id).all()
                updated = 0
                
                for version in versions:
                    card = version.card
                    # 构建 card_id (与官网 modal id 格式一致)
                    if version.version_suffix:
                        card_id = f"{card.card_number}{version.version_suffix.replace('_v', '_p')}"
                    else:
                        card_id = card.card_number
                    
                    # 尝试匹配
                    ill_type = ill_types.get(card_id)
                    
                    # 也尝试不带后缀的匹配
                    if not ill_type:
                        ill_type = ill_types.get(card.card_number)
                    
                    if ill_type and version.illustration_type != ill_type:
                        version.illustration_type = ill_type
                        updated += 1
                
                db.session.commit()
                total_updated += updated
                
                # 统计
                type_counts = {}
                for v in versions:
                    t = v.illustration_type or 'unknown'
                    type_counts[t] = type_counts.get(t, 0) + 1
                
                logger.info(f"系列 {series.code}: 更新 {updated} 个版本 | 分布: {type_counts}")
                
                # 避免请求过快
                time.sleep(1)
            
            logger.info(f"\n=== 更新完成 ===")
            logger.info(f"总计更新 {total_updated} 个版本")
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='更新卡片插画类型')
    parser.add_argument('--series', type=str, help='指定系列代码 (如 OP-14)')
    parser.add_argument('--all', action='store_true', help='更新所有系列')
    
    args = parser.parse_args()
    
    if args.series:
        update_illustration_types(args.series)
    elif args.all:
        update_illustration_types()
    else:
        print("请指定 --series <代码> 或 --all")
        print("示例:")
        print("  python update_illustration_types.py --series OP-14")
        print("  python update_illustration_types.py --all")
