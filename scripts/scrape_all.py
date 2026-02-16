#!/usr/bin/env python3
"""
爬取所有系列卡片并存入数据库
"""
import sys
sys.path.insert(0, '/workspace/opcg-tcg')

import time
from loguru import logger
from scrapers.jp_official import JapanOfficialScraper, CardData
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage

# 配置日志
logger.add("/workspace/opcg-tcg/logs/scrape_{time:YYYY-MM-DD}.log", rotation="1 day")


def save_series_to_db(series_data: dict) -> Series:
    """保存系列到数据库"""
    series = Series.query.filter_by(code=series_data['code']).first()
    
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
    
    return series


def save_card_to_db(card_data: CardData, series: Series):
    """保存卡片到数据库
    
    数据模型说明:
    - Card: 唯一标识一张卡片（card_number + language）
    - card_series: 多对多关系，记录卡片在哪些系列中出现
    - CardVersion: 同一卡片的不同版本（普通、异画等）
    
    这样设计允许:
    1. 再录卡可以同时出现在多个系列的图鉴中
    2. 每个系列的图鉴展示该系列包含的所有卡片
    """
    from app.models.card import card_series
    
    # 查找或创建基础卡片
    card = Card.query.filter_by(
        card_number=card_data.card_number,
        language='jp'
    ).first()
    
    is_new_card = False
    if not card:
        is_new_card = True
        card = Card(
            card_number=card_data.card_number,
            series_id=series.id,  # 主系列（第一次创建时的系列）
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
        db.session.flush()  # 获取 card.id
    
    # 检查卡片是否已经关联到此系列
    existing_link = db.session.execute(
        card_series.select().where(
            (card_series.c.card_id == card.id) & 
            (card_series.c.series_id == series.id)
        )
    ).first()
    
    if not existing_link:
        # 判断是否为再录卡：卡号前缀与系列代码不匹配
        card_prefix = card_data.card_number.split('-')[0] if '-' in card_data.card_number else ''
        series_prefix = series.code.replace('-', '')
        is_reprint = card_prefix != series_prefix
        
        # 添加卡片与系列的关联
        db.session.execute(
            card_series.insert().values(
                card_id=card.id,
                series_id=series.id,
                is_reprint=is_reprint,
                source_info=card_data.source_info
            )
        )
    
    # 创建卡片版本
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
        image = CardImage.query.filter_by(
            version_id=version.id
        ).first()
        
        if not image:
            image = CardImage(
                version_id=version.id,
                original_url=card_data.image_url
            )
            db.session.add(image)


def scrape_all_series(download_images: bool = False):
    """爬取所有系列"""
    app = create_app()
    
    with app.app_context():
        scraper = JapanOfficialScraper()
        
        try:
            scraper.start_browser()
            
            # 获取系列列表
            series_list = scraper.get_series_list()
            logger.info(f"共找到 {len(series_list)} 个系列")
            
            total_cards = 0
            
            for i, series_data in enumerate(series_list):
                logger.info(f"\n[{i+1}/{len(series_list)}] 处理系列: {series_data['code']}")
                
                # 保存系列
                series = save_series_to_db(series_data)
                
                # 检查是否已爬取
                existing_count = Card.query.filter_by(series_id=series.id).count()
                if existing_count > 0:
                    logger.info(f"系列 {series.code} 已有 {existing_count} 张卡片，跳过")
                    total_cards += existing_count
                    continue
                
                # 爬取卡片
                try:
                    cards = scraper.scrape_series(
                        series_data['official_series_id'],
                        download_images=download_images
                    )
                    
                    # 保存卡片
                    for card_data in cards:
                        save_card_to_db(card_data, series)
                    
                    db.session.commit()
                    total_cards += len(cards)
                    logger.info(f"系列 {series.code} 保存 {len(cards)} 张卡片")
                    
                except Exception as e:
                    logger.error(f"爬取系列 {series_data['code']} 失败: {e}")
                    db.session.rollback()
                    continue
                
                # 避免请求过快
                time.sleep(2)
            
            logger.info(f"\n=== 爬取完成 ===")
            logger.info(f"总计 {total_cards} 张卡片")
            
        finally:
            scraper.close_browser()


def scrape_single_series(series_code: str, download_images: bool = False):
    """爬取单个系列"""
    app = create_app()
    
    with app.app_context():
        scraper = JapanOfficialScraper()
        
        try:
            scraper.start_browser()
            
            # 获取系列列表找到对应ID
            series_list = scraper.get_series_list()
            series_data = None
            
            for s in series_list:
                if s['code'] == series_code:
                    series_data = s
                    break
            
            if not series_data:
                logger.error(f"未找到系列: {series_code}")
                return
            
            # 保存系列
            series = save_series_to_db(series_data)
            
            # 爬取卡片
            cards = scraper.scrape_series(
                series_data['official_series_id'],
                download_images=download_images
            )
            
            # 保存卡片
            for card_data in cards:
                save_card_to_db(card_data, series)
            
            db.session.commit()
            logger.info(f"系列 {series.code} 保存 {len(cards)} 张卡片")
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='爬取OPCG卡片数据')
    parser.add_argument('--series', type=str, help='指定系列代码 (如 OP-14)')
    parser.add_argument('--images', action='store_true', help='下载图片')
    parser.add_argument('--all', action='store_true', help='爬取所有系列')
    
    args = parser.parse_args()
    
    if args.series:
        scrape_single_series(args.series, download_images=args.images)
    elif args.all:
        scrape_all_series(download_images=args.images)
    else:
        print("请指定 --series <代码> 或 --all")
        print("示例:")
        print("  python scrape_all.py --series OP-14")
        print("  python scrape_all.py --all")
        print("  python scrape_all.py --all --images")
