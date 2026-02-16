#!/usr/bin/env python
"""
重新爬取缺失系列的数据
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage
from scrapers.jp_official import JapanOfficialScraper
from loguru import logger


def save_cards_to_db(cards, series_code, official_series_id):
    """将爬取的卡片保存到数据库"""
    app = create_app()
    
    with app.app_context():
        # 获取或创建系列
        series = Series.query.filter_by(code=series_code, language='jp').first()
        
        if not series:
            series = Series(
                code=series_code,
                language='jp',
                name=f"Series {series_code}",
                official_series_id=official_series_id
            )
            db.session.add(series)
            db.session.flush()
            logger.info(f"创建系列: {series_code}")
        
        saved = 0
        updated = 0
        
        for card_data in cards:
            # 查找现有卡片
            card = Card.query.filter_by(
                card_number=card_data.card_number,
                language='jp'
            ).first()
            
            if not card:
                # 创建新卡片
                card = Card(
                    card_number=card_data.card_number,
                    language='jp',
                    series_id=series.id,
                    name=card_data.name,
                    card_type=card_data.card_type,
                    rarity=card_data.rarity,
                    colors=card_data.colors,
                    cost=card_data.cost,
                    life=card_data.life,
                    power=card_data.power,
                    counter=card_data.counter,
                    attribute=card_data.attribute,
                    traits=card_data.traits,
                    effect_text=card_data.effect_text,
                    trigger_text=card_data.trigger_text,
                    source_info=card_data.source_info,
                    block_icon=card_data.block_icon
                )
                db.session.add(card)
                db.session.flush()
                saved += 1
                
                # 创建默认版本
                version_type = 'alt_art' if card_data.version_index > 0 else 'normal'
                version = CardVersion(
                    card_id=card.id,
                    version_type=version_type,
                    version_suffix=f'_v{card_data.version_index}' if card_data.version_index > 0 else ''
                )
                db.session.add(version)
                db.session.flush()
                
                # 创建图片记录
                if card_data.image_url:
                    image = CardImage(
                        version_id=version.id,
                        image_type='front',
                        original_url=card_data.image_url
                    )
                    db.session.add(image)
            else:
                # 卡片已存在，检查是否需要添加新版本
                if card_data.version_index > 0:
                    existing_versions = card.versions.count()
                    if card_data.version_index >= existing_versions:
                        version = CardVersion(
                            card_id=card.id,
                            version_type='alt_art',
                            version_suffix=f'_v{card_data.version_index}'
                        )
                        db.session.add(version)
                        db.session.flush()
                        
                        if card_data.image_url:
                            image = CardImage(
                                version_id=version.id,
                                image_type='front',
                                original_url=card_data.image_url
                            )
                            db.session.add(image)
                        updated += 1
        
        db.session.commit()
        logger.info(f"{series_code}: 新增 {saved} 张, 更新 {updated} 个版本")
        return saved, updated


def rescrape_missing_series(limit=None):
    """重新爬取缺失的系列"""
    
    # 需要重新爬取的系列 (code, official_series_id, expected_count)
    SERIES_TO_SCRAPE = [
        # Booster Packs
        ('OP-01', '550101', 121),
        ('OP-02', '550102', 121),
        ('OP-03', '550103', 122),
        ('OP-04', '550104', 121),
        ('OP-05', '550105', 120),
        ('OP-06', '550106', 129),
        ('OP-07', '550107', 142),
        ('OP-08', '550108', 142),
        ('OP-09', '550109', 137),
        ('OP-10', '550110', 144),
        ('OP-11', '550111', 144),
        ('OP-12', '550112', 144),
        ('OP-13', '550113', 144),
        ('OP-14', '550114', 156),
        # Extra Boosters
        ('EB-01', '550201', 88),
        ('EB-02', '550202', 173),
        ('EB-03', '550203', 124),
        ('EB-04', '550204', 96),
        # Premium Boosters
        ('PRB-01', '550301', 216),
        ('PRB-02', '550302', 347),
        # Starter Decks (只爬有问题的)
        ('ST-11', '550011', 15),
        ('ST-15', '550015', 17),
        ('ST-17', '550017', 17),
        ('ST-18', '550018', 17),
        ('ST-19', '550019', 17),
        ('ST-20', '550020', 17),
        ('ST-21', '550021', 26),
        ('ST-23', '550023', 17),
        ('ST-24', '550024', 17),
        ('ST-25', '550025', 17),
        ('ST-26', '550026', 17),
        ('ST-27', '550027', 17),
        ('ST-28', '550028', 17),
    ]
    
    if limit:
        SERIES_TO_SCRAPE = SERIES_TO_SCRAPE[:limit]
    
    scraper = JapanOfficialScraper()
    total_saved = 0
    total_updated = 0
    
    try:
        scraper.start_browser()
        
        for series_code, series_id, expected in SERIES_TO_SCRAPE:
            logger.info(f"\n=== 爬取 {series_code} (预期 {expected} 张) ===")
            
            try:
                cards = scraper.scrape_series(series_id, download_images=False)
                logger.info(f"获取 {len(cards)} 张卡片")
                
                # 过滤只保留属于该系列的卡片
                series_prefix = series_code.replace('-', '')  # OP-14 -> OP14
                own_cards = [c for c in cards if c.card_number.startswith(series_prefix)]
                reprint_cards = [c for c in cards if not c.card_number.startswith(series_prefix)]
                
                logger.info(f"  本系列卡片: {len(own_cards)}")
                logger.info(f"  再录卡片: {len(reprint_cards)}")
                
                # 只保存本系列的卡片
                saved, updated = save_cards_to_db(own_cards, series_code, series_id)
                total_saved += saved
                total_updated += updated
                
                time.sleep(2)  # 避免请求过快
                
            except Exception as e:
                logger.error(f"爬取 {series_code} 失败: {e}")
                continue
    
    finally:
        scraper.close_browser()
    
    logger.info(f"\n=== 完成 ===")
    logger.info(f"总计新增: {total_saved} 张")
    logger.info(f"总计更新: {total_updated} 个版本")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='限制爬取系列数量')
    parser.add_argument('--series', type=str, help='只爬取指定系列')
    
    args = parser.parse_args()
    
    if args.series:
        # 单系列爬取
        scraper = JapanOfficialScraper()
        try:
            scraper.start_browser()
            
            app = create_app()
            with app.app_context():
                series = Series.query.filter_by(code=args.series, language='jp').first()
                if series:
                    cards = scraper.scrape_series(series.official_series_id, download_images=False)
                    
                    series_prefix = args.series.replace('-', '')
                    own_cards = [c for c in cards if c.card_number.startswith(series_prefix)]
                    
                    save_cards_to_db(own_cards, args.series, series.official_series_id)
                else:
                    logger.error(f"系列 {args.series} 不存在")
        finally:
            scraper.close_browser()
    else:
        rescrape_missing_series(limit=args.limit)
