#!/usr/bin/env python3
"""
完整重新爬取日文卡片数据

核心逻辑改动:
1. 每个 CardVersion 关联到具体的 Series（表示这个版本来自哪个补充包）
2. Card 可以出现在多个 Series（通过 card_series 多对多关系）
3. 图鉴展示时，按 series_id 筛选 CardVersion 即可得到该系列的完整卡片列表

这样：
- OP-14 图鉴会显示 156 个版本（包括本系列卡片的版本 + 再录卡在 OP-14 中的版本）
- 同一张再录卡在不同系列中会有独立的 CardVersion 记录
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

logger.add("/workspace/opcg-tcg/logs/full_rescrape_{time:YYYY-MM-DD}.log", rotation="1 day")


def clear_all_data():
    """清除所有日文卡片数据（保留英文）"""
    # 清除 card_series
    db.session.execute(text('DELETE FROM card_series'))
    
    # 获取所有日文卡片 ID
    jp_card_ids = db.session.execute(
        text("SELECT id FROM cards WHERE language = 'jp'")
    ).fetchall()
    jp_card_ids = [r[0] for r in jp_card_ids]
    
    if jp_card_ids:
        # 清除相关的图片
        db.session.execute(
            text(f'''
                DELETE FROM card_images WHERE version_id IN (
                    SELECT id FROM card_versions WHERE card_id IN ({','.join(map(str, jp_card_ids))})
                )
            ''')
        )
        
        # 清除版本
        db.session.execute(
            text(f"DELETE FROM card_versions WHERE card_id IN ({','.join(map(str, jp_card_ids))})")
        )
        
        # 清除卡片
        db.session.execute(
            text(f"DELETE FROM cards WHERE id IN ({','.join(map(str, jp_card_ids))})")
        )
    
    db.session.commit()
    logger.info("清除了所有日文卡片数据")


def save_card_version(card_data: CardData, series: Series):
    """
    保存卡片版本
    
    - Card: 按 card_number + language 唯一
    - CardVersion: 按 card_id + series_id + version_suffix 唯一
    """
    # 查找或创建基础卡片
    card = Card.query.filter_by(
        card_number=card_data.card_number,
        language='jp'
    ).first()
    
    if not card:
        # 确定主系列（卡号前缀匹配的系列）
        card_prefix = card_data.card_number.split('-')[0] if '-' in card_data.card_number else ''
        series_prefix = series.code.replace('-', '')
        primary_series_id = series.id if card_prefix == series_prefix else series.id
        
        card = Card(
            card_number=card_data.card_number,
            series_id=primary_series_id,
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
    
    # 添加 card_series 关联（如果不存在）
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
    
    # 创建卡片版本（按 card_id + series_id + version_suffix 唯一）
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
    
    return card, version


def main():
    app = create_app()
    
    with app.app_context():
        logger.info("开始完整重新爬取...")
        
        # 1. 清除现有日文数据
        logger.info("清除现有数据...")
        clear_all_data()
        
        scraper = JapanOfficialScraper()
        
        try:
            scraper.start_browser()
            
            # 2. 获取系列列表
            series_list = scraper.get_series_list()
            logger.info(f"共找到 {len(series_list)} 个系列")
            
            total_versions = 0
            
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
                
                # 3. 爬取该系列的所有卡片
                try:
                    cards = scraper.scrape_series(
                        series_data['official_series_id'],
                        download_images=False
                    )
                    
                    for card_data in cards:
                        save_card_version(card_data, series)
                    
                    db.session.commit()
                    
                    # 统计该系列的版本数
                    series_versions = CardVersion.query.filter_by(series_id=series.id).count()
                    total_versions += series_versions
                    
                    logger.info(f"系列 {series.code}: 爬取 {len(cards)} 条, 创建 {series_versions} 个版本")
                    
                except Exception as e:
                    logger.error(f"爬取 {series_data['code']} 失败: {e}")
                    db.session.rollback()
                    import traceback
                    traceback.print_exc()
                    continue
                
                time.sleep(1)
            
            # 4. 最终统计
            logger.info("\n" + "=" * 60)
            logger.info("爬取完成！")
            
            total_cards = Card.query.filter_by(language='jp').count()
            total_vers = CardVersion.query.join(Card).filter(Card.language == 'jp').count()
            total_links = db.session.execute(text('SELECT COUNT(*) FROM card_series')).scalar()
            
            logger.info(f"日文卡片: {total_cards}")
            logger.info(f"日文版本: {total_vers}")
            logger.info(f"卡片-系列关联: {total_links}")
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    main()
