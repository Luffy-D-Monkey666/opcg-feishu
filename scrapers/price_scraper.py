"""
价格数据爬虫 - 从 OPTCG API 获取价格数据
数据源: https://optcgapi.com/
"""
import requests
import time
from datetime import datetime
from loguru import logger


class PriceScraper:
    """价格数据爬虫"""
    
    BASE_URL = "https://optcgapi.com/api"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OPCG-TCG-Manager/1.0'
        })
    
    def get_card_price(self, card_number: str) -> list:
        """
        获取单张卡片的价格
        
        Args:
            card_number: 卡片编号，如 'OP14-001'
            
        Returns:
            价格数据列表 (可能有多个版本)
        """
        url = f"{self.BASE_URL}/sets/card/{card_number}/"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data:
                results.append({
                    'card_number': item.get('card_set_id'),
                    'name': item.get('card_name'),
                    'market_price': item.get('market_price'),
                    'inventory_price': item.get('inventory_price'),
                    'is_alt_art': 'Alternate Art' in item.get('card_name', ''),
                    'image_id': item.get('card_image_id'),
                    'date_scraped': item.get('date_scraped')
                })
            
            return results
            
        except requests.RequestException as e:
            logger.error(f"Error fetching price for {card_number}: {e}")
            return []
    
    def get_prices_for_cards(self, card_numbers: list, delay: float = 0.5) -> list:
        """
        批量获取多张卡片的价格
        
        Args:
            card_numbers: 卡片编号列表
            delay: 每次请求间隔（秒）
            
        Returns:
            所有卡片的价格数据
        """
        results = []
        
        for i, card_number in enumerate(card_numbers):
            prices = self.get_card_price(card_number)
            results.extend(prices)
            
            if i % 50 == 0 and i > 0:
                logger.info(f"Progress: {i}/{len(card_numbers)} cards")
            
            time.sleep(delay)
        
        logger.info(f"Got {len(results)} price records for {len(card_numbers)} cards")
        return results


def update_prices_in_db(app, limit: int = None, series_code: str = None):
    """
    更新数据库中的价格数据
    
    Args:
        app: Flask 应用实例
        limit: 限制更新的卡片数量（用于测试）
        series_code: 指定系列代码，如 'OP-14'
    """
    from app import db
    from app.models.card import Card, CardVersion
    from app.models.price import PriceHistory
    from app.models.series import Series
    
    scraper = PriceScraper()
    
    with app.app_context():
        # 获取需要更新的卡片
        query = Card.query.filter_by(language='jp')
        
        if series_code:
            series = Series.query.filter_by(code=series_code).first()
            if series:
                query = query.filter_by(series_id=series.id)
        
        cards = query.all()
        
        if limit:
            cards = cards[:limit]
        
        card_numbers = [c.card_number for c in cards]
        logger.info(f"Fetching prices for {len(card_numbers)} cards...")
        
        # 批量获取价格
        prices = scraper.get_prices_for_cards(card_numbers, delay=0.3)
        
        total_updated = 0
        today = datetime.utcnow().date()
        
        for price_data in prices:
            card_number = price_data['card_number']
            market_price = price_data['market_price']
            
            if market_price is None or market_price == 0:
                continue
            
            # 查找对应的卡片
            card = Card.query.filter_by(card_number=card_number, language='jp').first()
            if not card:
                continue
            
            # 确定版本类型
            version_type = 'alt_art' if price_data['is_alt_art'] else 'normal'
            version = card.versions.filter_by(version_type=version_type).first()
            
            if not version:
                version = card.versions.first()
            
            if version:
                # 检查今天是否已有记录
                existing = PriceHistory.query.filter(
                    PriceHistory.version_id == version.id,
                    PriceHistory.source == 'optcg_api',
                    db.func.date(PriceHistory.recorded_at) == today
                ).first()
                
                if not existing:
                    price_record = PriceHistory(
                        version_id=version.id,
                        source='optcg_api',
                        currency='USD',
                        price=market_price,
                        condition='unsealed',
                        price_type='average'
                    )
                    db.session.add(price_record)
                    total_updated += 1
        
        db.session.commit()
        logger.info(f"Updated {total_updated} price records")
        return total_updated


if __name__ == '__main__':
    # 测试
    scraper = PriceScraper()
    
    # 测试获取单卡价格
    print("=== Single Card ===")
    prices = scraper.get_card_price('OP14-001')
    for p in prices:
        print(f"{p['name']}: ${p['market_price']}")
    
    # 测试获取系列价格
    print("\n=== Set Prices (OP14, first 5) ===")
    set_prices = scraper.get_set_prices('OP14')
    for p in set_prices[:5]:
        print(f"{p['card_number']} {p['name']}: ${p['market_price']}")
