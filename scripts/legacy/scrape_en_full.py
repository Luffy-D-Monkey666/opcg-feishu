#!/usr/bin/env python3
"""
完整爬取英文官网所有系列数据
"""
import sys
sys.path.insert(0, '/workspace/opcg-tcg')

import time
from loguru import logger
from scrapers.en_official import EnglishOfficialScraper, CardDataEN
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage

logger.add("/workspace/opcg-tcg/logs/scrape_en_full_{time:YYYY-MM-DD}.log", rotation="1 day")


def save_en_series(series_data: dict) -> Series:
    """保存英文系列"""
    series = Series.query.filter_by(code=series_data['code'], language='en').first()
    
    if not series:
        series = Series(
            code=series_data['code'],
            name=series_data['name'],
            official_series_id=series_data['official_series_id'],
            series_type=series_data['series_type'],
            language='en'
        )
        db.session.add(series)
        db.session.commit()
        logger.info(f"新增英文系列: {series.code}")
    else:
        # 更新名称
        if series.name != series_data['name']:
            series.name = series_data['name']
            db.session.commit()
    
    return series


def save_en_card(card_data: CardDataEN, series: Series):
    """保存英文卡片"""
    # 查找或创建卡片
    card = Card.query.filter_by(
        card_number=card_data.card_number,
        language='en'
    ).first()
    
    if not card:
        card = Card(
            card_number=card_data.card_number,
            series_id=series.id,
            language='en',
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
    
    # 创建版本
    version_suffix = f"_v{card_data.version_index}" if card_data.version_index > 0 else ""
    version = CardVersion.query.filter_by(
        card_id=card.id,
        series_id=series.id,
        version_suffix=version_suffix
    ).first()
    
    if not version:
        version = CardVersion(
            card_id=card.id,
            series_id=series.id,
            version_suffix=version_suffix,
            version_type='normal' if card_data.version_index == 0 else 'alt_art',
            source_description=card_data.source_info
        )
        db.session.add(version)
        db.session.flush()
    
    # 创建图片
    if card_data.image_url:
        image = CardImage.query.filter_by(version_id=version.id).first()
        if not image:
            image = CardImage(
                version_id=version.id,
                original_url=card_data.image_url
            )
            db.session.add(image)


def scrape_all_en_series():
    """爬取所有英文系列"""
    app = create_app()
    
    with app.app_context():
        scraper = EnglishOfficialScraper()
        
        try:
            scraper.start_browser()
            
            # 获取系列列表
            series_list = scraper.get_series_list()
            logger.info(f"共找到 {len(series_list)} 个英文系列")
            
            total_cards = 0
            
            for i, series_data in enumerate(series_list):
                logger.info(f"\n[{i+1}/{len(series_list)}] 处理系列: {series_data['code']}")
                
                # 保存系列
                series = save_en_series(series_data)
                
                # 检查是否已爬取
                existing_count = CardVersion.query.filter_by(series_id=series.id).count()
                if existing_count > 0:
                    logger.info(f"系列 {series.code} 已有 {existing_count} 张卡片，跳过")
                    total_cards += existing_count
                    continue
                
                # 爬取卡片
                try:
                    cards = scraper.scrape_series(
                        series_data['official_series_id'],
                        download_images=False
                    )
                    
                    # 保存卡片
                    for card_data in cards:
                        save_en_card(card_data, series)
                    
                    db.session.commit()
                    total_cards += len(cards)
                    logger.info(f"系列 {series.code} 保存 {len(cards)} 张卡片")
                    
                except Exception as e:
                    logger.error(f"爬取系列 {series_data['code']} 失败: {e}")
                    db.session.rollback()
                    continue
                
                time.sleep(2)
            
            logger.info(f"\n=== 爬取完成 ===")
            logger.info(f"总计 {total_cards} 张卡片")
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='爬取英文OPCG卡片数据')
    parser.add_argument('--all', action='store_true', help='爬取所有系列')
    
    args = parser.parse_args()
    
    if args.all:
        scrape_all_en_series()
    else:
        print("请指定 --all")
        print("示例:")
        print("  python scrape_en_full.py --all")
