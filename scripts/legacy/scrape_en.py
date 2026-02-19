#!/usr/bin/env python3
"""
爬取英文官网数据，更新现有卡片的英文名称和效果
"""
import sys
sys.path.insert(0, '/workspace/opcg-tcg')

import time
from loguru import logger
from scrapers.en_official import EnglishOfficialScraper, CardDataEN
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage

logger.add("/workspace/opcg-tcg/logs/scrape_en_{time:YYYY-MM-DD}.log", rotation="1 day")


def update_card_with_en_data(card_data: CardDataEN):
    """用英文数据更新现有卡片"""
    # 查找日文卡片
    card = Card.query.filter_by(
        card_number=card_data.card_number,
        language='jp'
    ).first()
    
    if not card:
        logger.debug(f"未找到日文卡片: {card_data.card_number}")
        return False
    
    # 创建或更新英文版本卡片
    en_card = Card.query.filter_by(
        card_number=card_data.card_number,
        language='en'
    ).first()
    
    if not en_card:
        en_card = Card(
            card_number=card_data.card_number,
            series_id=card.series_id,
            language='en',
            name=card_data.name,
            card_type=card_data.card_type,
            rarity=card_data.rarity,
            colors=card_data.colors or card.colors,
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
        db.session.add(en_card)
        db.session.flush()
        
        # 创建版本
        version_suffix = f"_v{card_data.version_index}" if card_data.version_index > 0 else ""
        version = CardVersion(
            card_id=en_card.id,
            version_suffix=version_suffix,
            version_type='normal' if card_data.version_index == 0 else 'alt_art'
        )
        db.session.add(version)
        db.session.flush()
        
        # 创建图片
        if card_data.image_url:
            image = CardImage(
                version_id=version.id,
                original_url=card_data.image_url
            )
            db.session.add(image)
        
        return True
    else:
        # 更新现有英文卡片
        en_card.name = card_data.name
        en_card.effect_text = card_data.effect_text
        en_card.trigger_text = card_data.trigger_text
        en_card.traits = card_data.traits
        return False


def scrape_all_en_series():
    """爬取所有英文系列"""
    app = create_app()
    
    with app.app_context():
        scraper = EnglishOfficialScraper()
        
        try:
            scraper.start_browser()
            
            series_list = scraper.get_series_list()
            logger.info(f"共找到 {len(series_list)} 个英文系列")
            
            total_new = 0
            total_updated = 0
            
            for i, series_data in enumerate(series_list):
                logger.info(f"\n[{i+1}/{len(series_list)}] 处理英文系列: {series_data['code']}")
                
                try:
                    cards = scraper.scrape_series(series_data['official_series_id'])
                    
                    new_count = 0
                    for card_data in cards:
                        if update_card_with_en_data(card_data):
                            new_count += 1
                    
                    db.session.commit()
                    total_new += new_count
                    total_updated += len(cards) - new_count
                    
                    logger.info(f"系列 {series_data['code']}: 新增 {new_count}, 更新 {len(cards) - new_count}")
                    
                except Exception as e:
                    logger.error(f"爬取英文系列 {series_data['code']} 失败: {e}")
                    db.session.rollback()
                    continue
                
                time.sleep(2)
            
            logger.info(f"\n=== 英文爬取完成 ===")
            logger.info(f"新增: {total_new}, 更新: {total_updated}")
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    scrape_all_en_series()
