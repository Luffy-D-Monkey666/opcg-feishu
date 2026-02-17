"""
爬虫测试 (单元测试，不实际请求网络)
"""
import pytest
from scrapers.jp_official import JapanOfficialScraper, CardData


class TestCardData:
    """CardData 数据类测试"""
    
    def test_create_card_data(self):
        """测试创建卡片数据"""
        card = CardData(
            card_number='OP14-001',
            name='トラファルガー・ロー',
            card_type='LEADER',
            rarity='L',
            colors='赤',
            life=5,
            power=5000
        )
        
        assert card.card_number == 'OP14-001'
        assert card.card_type == 'LEADER'
        assert card.version_index == 0
        assert card.has_star_mark == False
    
    def test_card_data_defaults(self):
        """测试默认值"""
        card = CardData(
            card_number='TEST-001',
            name='Test',
            card_type='CHARACTER',
            rarity='C',
            colors='青'
        )
        
        assert card.cost is None
        assert card.life is None
        assert card.illustration_type is None


class TestJapanOfficialScraper:
    """日文爬虫测试"""
    
    def test_series_type_keywords(self):
        """测试系列类型关键词映射"""
        scraper = JapanOfficialScraper()
        
        assert 'ブースターパック' in scraper.SERIES_TYPE_KEYWORDS
        assert scraper.SERIES_TYPE_KEYWORDS['ブースターパック'] == 'booster'
        assert scraper.SERIES_TYPE_KEYWORDS['スタートデッキ'] == 'starter'
    
    def test_parse_int(self):
        """测试整数解析"""
        scraper = JapanOfficialScraper()
        
        assert scraper._parse_int('5000') == 5000
        assert scraper._parse_int('-') is None
        assert scraper._parse_int(None) is None
        assert scraper._parse_int('') is None
        assert scraper._parse_int('1000+') == 1000
    
    def test_image_dir_exists(self):
        """测试图片目录路径"""
        scraper = JapanOfficialScraper()
        
        # 应该是相对路径，不是硬编码
        assert 'data' in str(scraper.IMAGE_DIR)
        assert 'images' in str(scraper.IMAGE_DIR)
