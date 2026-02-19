#!/usr/bin/env python3
"""
重新爬取日文卡片数据，修复再录卡问题

修改逻辑:
1. 清除 card_series 关联表
2. 按系列顺序重新爬取，每个系列的所有卡片都会记录到 card_series
3. 同一卡号的卡片共享 Card 记录，但会关联到多个系列

这样每个系列的图鉴都会显示完整的卡片列表（包括再录卡）
"""
import sys
sys.path.insert(0, '/workspace/opcg-tcg')

import time
from loguru import logger
from scrapers.jp_official import JapanOfficialScraper, CardData
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage, card_series
from sqlalchemy import text

# 配置日志
logger.add("/workspace/opcg-tcg/logs/rescrape_{time:YYYY-MM-DD}.log", rotation="1 day")


def clear_card_series_links():
    """清除所有卡片-系列关联"""
    count = db.session.execute(text('DELETE FROM card_series')).rowcount
    db.session.commit()
    logger.info(f"清除了 {count} 条 card_series 关联")


def save_card_with_series(card_data: CardData, series: Series):
    """保存卡片并建立与系列的关联"""
    # 查找或创建基础卡片
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
    
    # 检查是否已关联到此系列
    existing_link = db.session.execute(
        card_series.select().where(
            (card_series.c.card_id == card.id) & 
            (card_series.c.series_id == series.id)
        )
    ).first()
    
    if not existing_link:
        # 判断是否为再录卡
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
    
    # 创建卡片版本（如果不存在）
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
    
    # 创建图片记录
    if card_data.image_url:
        image = CardImage.query.filter_by(version_id=version.id).first()
        if not image:
            image = CardImage(
                version_id=version.id,
                original_url=card_data.image_url
            )
            db.session.add(image)
    
    return card


def rescrape_all_jp():
    """重新爬取所有日文系列"""
    app = create_app()
    
    with app.app_context():
        # 1. 清除现有的 card_series 关联
        logger.info("清除现有 card_series 关联...")
        clear_card_series_links()
        
        scraper = JapanOfficialScraper()
        
        try:
            scraper.start_browser()
            
            # 2. 获取系列列表
            series_list = scraper.get_series_list()
            logger.info(f"共找到 {len(series_list)} 个系列")
            
            total_links = 0
            
            for i, series_data in enumerate(series_list):
                logger.info(f"\n[{i+1}/{len(series_list)}] 处理系列: {series_data['code']}")
                
                # 获取或创建系列
                series = Series.query.filter_by(
                    code=series_data['code'],
                    language='jp'
                ).first()
                
                if not series:
                    series = Series(
                        code=series_data['code'],
                        name=series_data['name'],
                        official_series_id=series_data['official_series_id'],
                        series_type=series_data['series_type'],
                        language='jp'
                    )
                    db.session.add(series)
                    db.session.commit()
                    logger.info(f"新增系列: {series.code}")
                
                # 3. 爬取该系列的所有卡片
                try:
                    cards = scraper.scrape_series(
                        series_data['official_series_id'],
                        download_images=False
                    )
                    
                    # 保存卡片并建立关联
                    for card_data in cards:
                        save_card_with_series(card_data, series)
                    
                    db.session.commit()
                    
                    # 统计该系列的关联数
                    series_links = db.session.execute(
                        text('SELECT COUNT(*) FROM card_series WHERE series_id = :sid'),
                        {'sid': series.id}
                    ).scalar()
                    
                    total_links += len(cards)
                    logger.info(f"系列 {series.code}: 爬取 {len(cards)} 张, 关联 {series_links} 条")
                    
                except Exception as e:
                    logger.error(f"爬取系列 {series_data['code']} 失败: {e}")
                    db.session.rollback()
                    continue
                
                time.sleep(1)  # 避免请求过快
            
            # 4. 统计结果
            logger.info("\n=== 爬取完成 ===")
            
            total_cards = Card.query.filter_by(language='jp').count()
            total_versions = CardVersion.query.join(Card).filter(Card.language == 'jp').count()
            total_card_series = db.session.execute(text('SELECT COUNT(*) FROM card_series')).scalar()
            
            logger.info(f"卡片数: {total_cards}")
            logger.info(f"版本数: {total_versions}")
            logger.info(f"卡片-系列关联数: {total_card_series}")
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    rescrape_all_jp()
