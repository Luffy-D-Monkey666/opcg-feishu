#!/usr/bin/env python3
"""
爬取所有系列卡片并存入数据库
支持日文和英文官网
"""
import sys
import os

# 动态设置路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)

import time
from loguru import logger

# 配置日志
log_dir = os.path.join(project_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
logger.add(os.path.join(log_dir, "scrape_{time:YYYY-MM-DD}.log"), rotation="1 day")


def get_scraper(lang: str):
    """获取对应语言的爬虫"""
    if lang == 'jp':
        from scrapers.jp_official import JapanOfficialScraper
        return JapanOfficialScraper()
    else:
        from scrapers.en_official import EnglishOfficialScraper
        return EnglishOfficialScraper()


def save_series_to_db(series_data: dict, lang: str):
    """保存系列到数据库"""
    from app.models.series import Series
    from app import db
    
    series = Series.query.filter_by(code=series_data['code'], language=lang).first()
    
    if not series:
        series = Series(
            code=series_data['code'],
            name=series_data['name'],
            official_series_id=series_data['official_series_id'],
            series_type=series_data['series_type'],
            language=lang
        )
        db.session.add(series)
        db.session.commit()
        logger.info(f"新增系列: {series.code} ({lang})")
    
    return series


def save_card_to_db(card_data, series, lang: str):
    """保存卡片到数据库"""
    from app.models.card import Card, CardVersion, CardImage, card_series
    from app import db
    
    # 查找或创建基础卡片
    card = Card.query.filter_by(
        card_number=card_data.card_number,
        language=lang
    ).first()
    
    if not card:
        card = Card(
            card_number=card_data.card_number,
            series_id=series.id,
            language=lang,
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
    
    # 检查卡片是否已经关联到此系列
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
    
    # 创建卡片版本
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
            source_description=card_data.source_info,
            illustration_type=getattr(card_data, 'illustration_type', None),
            has_star_mark=getattr(card_data, 'has_star_mark', False)
        )
        db.session.add(version)
        db.session.flush()
    else:
        # 更新已有版本的插画类型和星标（如果之前没有）
        updated = False
        if not version.illustration_type and getattr(card_data, 'illustration_type', None):
            version.illustration_type = card_data.illustration_type
            updated = True
        if not version.has_star_mark and getattr(card_data, 'has_star_mark', False):
            version.has_star_mark = True
            updated = True
    
    # 创建图片记录
    if card_data.image_url:
        image = CardImage.query.filter_by(version_id=version.id).first()
        if not image:
            image = CardImage(
                version_id=version.id,
                original_url=card_data.image_url
            )
            db.session.add(image)


def scrape_all_series(lang: str = 'jp', download_images: bool = False):
    """爬取所有系列"""
    from app import create_app, db
    from app.models.card import Card
    
    app = create_app()
    
    with app.app_context():
        scraper = get_scraper(lang)
        
        try:
            scraper.start_browser()
            series_list = scraper.get_series_list()
            logger.info(f"共找到 {len(series_list)} 个系列 ({lang})")
            
            total_cards = 0
            
            for i, series_data in enumerate(series_list):
                logger.info(f"\n[{i+1}/{len(series_list)}] 处理系列: {series_data['code']}")
                
                series = save_series_to_db(series_data, lang)
                
                # 检查是否已爬取
                existing_count = Card.query.filter_by(series_id=series.id).count()
                if existing_count > 0:
                    logger.info(f"系列 {series.code} 已有 {existing_count} 张卡片，跳过")
                    total_cards += existing_count
                    continue
                
                try:
                    cards = scraper.scrape_series(
                        series_data['official_series_id'],
                        download_images=download_images
                    )
                    
                    for card_data in cards:
                        save_card_to_db(card_data, series, lang)
                    
                    db.session.commit()
                    total_cards += len(cards)
                    logger.info(f"系列 {series.code} 保存 {len(cards)} 张卡片")
                    
                except Exception as e:
                    logger.error(f"爬取系列 {series_data['code']} 失败: {e}")
                    db.session.rollback()
                    continue
                
                time.sleep(2)
            
            logger.info(f"\n=== 爬取完成 ({lang}) ===")
            logger.info(f"总计 {total_cards} 张卡片")
            
        finally:
            scraper.close_browser()


def scrape_single_series(series_code: str, lang: str = 'jp', download_images: bool = False):
    """爬取单个系列"""
    from app import create_app, db
    
    app = create_app()
    
    with app.app_context():
        scraper = get_scraper(lang)
        
        try:
            scraper.start_browser()
            series_list = scraper.get_series_list()
            series_data = None
            
            for s in series_list:
                if s['code'] == series_code:
                    series_data = s
                    break
            
            if not series_data:
                logger.error(f"未找到系列: {series_code} ({lang})")
                return
            
            series = save_series_to_db(series_data, lang)
            
            cards = scraper.scrape_series(
                series_data['official_series_id'],
                download_images=download_images
            )
            
            for card_data in cards:
                save_card_to_db(card_data, series, lang)
            
            db.session.commit()
            logger.info(f"系列 {series.code} ({lang}) 保存 {len(cards)} 张卡片")
            
        finally:
            scraper.close_browser()


def check_new_series(lang: str = 'jp'):
    """检查并爬取新系列"""
    from app import create_app, db
    from app.models.series import Series
    
    app = create_app()
    
    with app.app_context():
        scraper = get_scraper(lang)
        
        try:
            scraper.start_browser()
            series_list = scraper.get_series_list()
            
            # 获取已有系列
            existing_codes = set(
                s.code for s in Series.query.filter_by(language=lang).all()
            )
            
            # 找出新系列
            new_series = [s for s in series_list if s['code'] not in existing_codes]
            
            if not new_series:
                logger.info(f"没有发现新系列 ({lang})")
                return
            
            logger.info(f"发现 {len(new_series)} 个新系列 ({lang})")
            
            for series_data in new_series:
                logger.info(f"爬取新系列: {series_data['code']}")
                
                series = save_series_to_db(series_data, lang)
                
                try:
                    cards = scraper.scrape_series(series_data['official_series_id'])
                    
                    for card_data in cards:
                        save_card_to_db(card_data, series, lang)
                    
                    db.session.commit()
                    logger.info(f"系列 {series.code} 保存 {len(cards)} 张卡片")
                    
                except Exception as e:
                    logger.error(f"爬取系列 {series_data['code']} 失败: {e}")
                    db.session.rollback()
                
                time.sleep(2)
            
        finally:
            scraper.close_browser()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='爬取OPCG卡片数据')
    parser.add_argument('--series', type=str, help='指定系列代码 (如 OP-14)')
    parser.add_argument('--lang', type=str, default='jp', choices=['jp', 'en'], help='语言 (jp/en)')
    parser.add_argument('--images', action='store_true', help='下载图片')
    parser.add_argument('--all', action='store_true', help='爬取所有系列')
    parser.add_argument('--check-new', action='store_true', help='检查并爬取新系列')
    
    args = parser.parse_args()
    
    if args.series:
        scrape_single_series(args.series, lang=args.lang, download_images=args.images)
    elif args.check_new:
        check_new_series(lang=args.lang)
    elif args.all:
        scrape_all_series(lang=args.lang, download_images=args.images)
    else:
        print("用法:")
        print("  python scrape_all.py --series OP-15 --lang jp   # 爬取指定系列")
        print("  python scrape_all.py --all --lang jp            # 爬取所有系列")
        print("  python scrape_all.py --check-new --lang jp      # 检查新系列")
        print("  python scrape_all.py --check-new --lang en      # 检查英文新系列")
