#!/usr/bin/env python3
"""补爬缺失的系列"""
import sys
sys.path.insert(0, '/workspace/opcg-tcg')

import time
from loguru import logger
from scrapers.jp_official import JapanOfficialScraper, CardData
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage, card_series
from sqlalchemy import text

logger.add("/workspace/opcg-tcg/logs/rescrape_{time:YYYY-MM-DD}.log", rotation="1 day")


def save_card_with_series(card_data: CardData, series: Series):
    """保存卡片并建立与系列的关联"""
    card = Card.query.filter_by(
        card_number=card_data.card_number,
        language='jp'
    ).first()
    
    if not card:
        card = Card(
            card_number=card_data.card_number,
            series_id=series.id,
            language='jp',
            name=card_data.name,
            card_type=card_data.card_type,
            rarity=card_data.rarity,
            colors=card_data.colors or '',
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
    
    existing_link = db.session.execute(
        card_series.select().where(
            (card_series.c.card_id == card.id) & 
            (card_series.c.series_id == series.id)
        )
    ).first()
    
    if not existing_link:
        card_prefix = card_data.card_number.split('-')[0] if '-' in card_data.card_number else ''
        series_prefix = series.code.replace('-', '')
        is_reprint = card_prefix != series_prefix
        
        db.session.execute(
            card_series.insert().values(
                card_id=card.id,
                series_id=series.id,
                is_reprint=is_reprint,
                source_info=card_data.source_info
            )
        )
    
    version_suffix = f"_v{card_data.version_index}" if card_data.version_index > 0 else ""
    version = CardVersion.query.filter_by(
        card_id=card.id,
        version_suffix=version_suffix
    ).first()
    
    if not version:
        version = CardVersion(
            card_id=card.id,
            version_suffix=version_suffix,
            version_type='normal' if card_data.version_index == 0 else 'alt_art'
        )
        db.session.add(version)
        db.session.flush()
    
    if card_data.image_url:
        image = CardImage.query.filter_by(version_id=version.id).first()
        if not image:
            image = CardImage(
                version_id=version.id,
                original_url=card_data.image_url
            )
            db.session.add(image)
    
    return card


def get_missing_series():
    """获取没有关联记录的系列"""
    result = db.session.execute(text('''
        SELECT s.id, s.code, s.official_series_id
        FROM series s 
        LEFT JOIN card_series cs ON s.id = cs.series_id 
        WHERE s.language = 'jp'
        GROUP BY s.id
        HAVING COUNT(cs.card_id) = 0
        ORDER BY s.code
    ''')).fetchall()
    return result


def main():
    app = create_app()
    
    with app.app_context():
        missing = get_missing_series()
        logger.info(f"需要补爬 {len(missing)} 个系列")
        
        if not missing:
            logger.info("没有缺失的系列")
            return
        
        scraper = JapanOfficialScraper()
        
        try:
            scraper.start_browser()
            
            for i, (series_id, code, official_id) in enumerate(missing):
                logger.info(f"\n[{i+1}/{len(missing)}] 补爬系列: {code}")
                
                series = Series.query.get(series_id)
                
                try:
                    cards = scraper.scrape_series(official_id, download_images=False)
                    
                    for card_data in cards:
                        save_card_with_series(card_data, series)
                    
                    db.session.commit()
                    
                    link_count = db.session.execute(
                        text('SELECT COUNT(*) FROM card_series WHERE series_id = :sid'),
                        {'sid': series_id}
                    ).scalar()
                    
                    logger.info(f"系列 {code}: 爬取 {len(cards)} 张, 关联 {link_count} 条")
                    
                except Exception as e:
                    logger.error(f"爬取 {code} 失败: {e}")
                    db.session.rollback()
                    continue
                
                time.sleep(1)
            
            # 最终统计
            total_links = db.session.execute(text('SELECT COUNT(*) FROM card_series')).scalar()
            logger.info(f"\n=== 补爬完成，总关联数: {total_links} ===")
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    main()
