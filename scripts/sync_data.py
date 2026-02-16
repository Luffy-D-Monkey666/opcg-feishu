#!/usr/bin/env python3
"""
数据同步脚本 - 用于 cron job 定期执行

功能:
1. 同步价格数据（每天）
2. 同步新卡片数据（每周）

用法:
    # 只更新价格（快速，约5-10分钟）
    python scripts/sync_data.py --prices
    
    # 检查新卡片（慢，约30分钟）
    python scripts/sync_data.py --cards
    
    # 完整同步（价格+新卡片）
    python scripts/sync_data.py --full

建议的 cron 配置:
    # 每天早上6点更新价格
    0 6 * * * cd /workspace/opcg-tcg && python scripts/sync_data.py --prices >> logs/sync.log 2>&1
    
    # 每周日凌晨2点检查新卡片
    0 2 * * 0 cd /workspace/opcg-tcg && python scripts/sync_data.py --cards >> logs/sync.log 2>&1
"""
import argparse
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

# 配置日志
log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'sync.log')
logger.add(log_path, rotation="1 week", retention="4 weeks")


def sync_prices(app, limit=None):
    """同步价格数据"""
    from scrapers.price_scraper import update_prices_in_db
    
    logger.info("=" * 50)
    logger.info(f"价格同步开始: {datetime.now()}")
    
    try:
        updated = update_prices_in_db(app, limit=limit)
        logger.info(f"价格同步完成: 更新了 {updated} 条记录")
        return True
    except Exception as e:
        logger.error(f"价格同步失败: {e}")
        return False


def sync_new_cards(app):
    """检查并同步新卡片"""
    from scrapers.jp_official import JapanOfficialScraper
    from app import db
    from app.models.series import Series
    from app.models.card import Card, CardVersion, CardImage, card_series
    
    logger.info("=" * 50)
    logger.info(f"卡片同步开始: {datetime.now()}")
    
    scraper = JapanOfficialScraper()
    
    try:
        scraper.start_browser()
        
        # 获取官网系列列表
        official_series = scraper.get_series_list()
        
        with app.app_context():
            # 检查是否有新系列
            existing_codes = set(s.code for s in Series.query.filter_by(language='jp').all())
            official_codes = set(s['code'] for s in official_series)
            
            new_series = official_codes - existing_codes
            
            if new_series:
                logger.info(f"发现 {len(new_series)} 个新系列: {new_series}")
                
                for series_data in official_series:
                    if series_data['code'] in new_series:
                        logger.info(f"爬取新系列: {series_data['code']}")
                        
                        # 创建系列
                        series = Series(
                            code=series_data['code'],
                            name=series_data['name'],
                            official_series_id=series_data['official_series_id'],
                            series_type=series_data['series_type'],
                            language='jp'
                        )
                        db.session.add(series)
                        db.session.flush()
                        
                        # 爬取卡片
                        cards = scraper.scrape_series(series_data['official_series_id'])
                        
                        for card_data in cards:
                            # 创建卡片和版本
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
                            
                            # 添加 card_series 关联
                            existing_link = db.session.execute(
                                card_series.select().where(
                                    (card_series.c.card_id == card.id) & 
                                    (card_series.c.series_id == series.id)
                                )
                            ).first()
                            
                            if not existing_link:
                                db.session.execute(
                                    card_series.insert().values(
                                        card_id=card.id,
                                        series_id=series.id,
                                        is_reprint=False
                                    )
                                )
                            
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
                                    version_type='normal' if card_data.version_index == 0 else 'alt_art'
                                )
                                db.session.add(version)
                                db.session.flush()
                            
                            # 图片
                            if card_data.image_url:
                                image = CardImage.query.filter_by(version_id=version.id).first()
                                if not image:
                                    db.session.add(CardImage(
                                        version_id=version.id,
                                        original_url=card_data.image_url
                                    ))
                        
                        db.session.commit()
                        logger.info(f"系列 {series_data['code']} 同步完成: {len(cards)} 张卡片")
            else:
                logger.info("没有发现新系列")
        
        return True
        
    except Exception as e:
        logger.error(f"卡片同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        scraper.close_browser()


def main():
    parser = argparse.ArgumentParser(description='Data sync script for OPCG TCG')
    parser.add_argument('--prices', action='store_true', help='Sync price data only')
    parser.add_argument('--cards', action='store_true', help='Check for new cards only')
    parser.add_argument('--full', action='store_true', help='Full sync (prices + cards)')
    parser.add_argument('--limit', type=int, help='Limit number of cards for price sync')
    
    args = parser.parse_args()
    
    from app import create_app
    app = create_app()
    
    results = []
    
    if args.prices or args.full:
        results.append(('prices', sync_prices(app, limit=args.limit)))
    
    if args.cards or args.full:
        results.append(('cards', sync_new_cards(app)))
    
    if not any([args.prices, args.cards, args.full]):
        parser.print_help()
        return
    
    # 打印结果
    logger.info("=" * 50)
    logger.info("同步结果:")
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        logger.info(f"  {name}: {status}")
    logger.info(f"完成时间: {datetime.now()}")


if __name__ == '__main__':
    main()
