"""
数据模型测试
"""
import pytest
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestSeries:
    """系列模型测试"""
    
    def test_create_series(self, app):
        """测试创建系列"""
        with app.app_context():
            series = Series(
                code='OP-14',
                language='jp',
                name='ブースターパック 蒼海の七傑【OP-14】',
                series_type='booster'
            )
            db.session.add(series)
            db.session.commit()
            
            assert series.id is not None
            assert series.code == 'OP-14'
            assert series.language == 'jp'
    
    def test_series_unique_code_language(self, app):
        """测试系列代码+语言唯一性"""
        with app.app_context():
            s1 = Series(code='OP-01', language='jp', name='JP Series')
            s2 = Series(code='OP-01', language='en', name='EN Series')
            db.session.add_all([s1, s2])
            db.session.commit()
            
            # 同代码不同语言应该都能创建
            assert s1.id != s2.id


class TestCard:
    """卡片模型测试"""
    
    def test_create_card(self, app):
        """测试创建卡片"""
        with app.app_context():
            series = Series(code='OP-14', language='jp', name='Test')
            db.session.add(series)
            db.session.commit()
            
            card = Card(
                card_number='OP14-001',
                language='jp',
                series_id=series.id,
                name='トラファルガー・ロー',
                card_type='LEADER',
                rarity='L',
                colors='赤',
                life=5,
                power=5000
            )
            db.session.add(card)
            db.session.commit()
            
            assert card.id is not None
            assert card.card_number == 'OP14-001'
            assert card.card_type == 'LEADER'
    
    def test_card_color_list(self, app):
        """测试颜色列表属性"""
        with app.app_context():
            series = Series(code='TEST', language='jp', name='Test')
            db.session.add(series)
            db.session.commit()
            
            card = Card(
                card_number='TEST-001',
                language='jp',
                series_id=series.id,
                name='Multi Color Card',
                card_type='CHARACTER',
                rarity='SR',
                colors='赤,青'
            )
            
            assert card.color_list == ['赤', '青']
    
    def test_card_trait_list(self, app):
        """测试特征列表属性"""
        with app.app_context():
            series = Series(code='TEST', language='jp', name='Test')
            db.session.add(series)
            db.session.commit()
            
            card = Card(
                card_number='TEST-002',
                language='jp',
                series_id=series.id,
                name='Test Card',
                card_type='CHARACTER',
                rarity='R',
                colors='赤',
                traits='海賊/超新星/麦わらの一味'
            )
            
            assert card.trait_list == ['海賊', '超新星', '麦わらの一味']


class TestCardVersion:
    """卡片版本测试"""
    
    def test_create_version(self, app):
        """测试创建版本"""
        with app.app_context():
            series = Series(code='OP-14', language='jp', name='Test')
            db.session.add(series)
            db.session.commit()
            
            card = Card(
                card_number='OP14-001',
                language='jp',
                series_id=series.id,
                name='Test',
                card_type='LEADER',
                rarity='L',
                colors='赤'
            )
            db.session.add(card)
            db.session.commit()
            
            version = CardVersion(
                card_id=card.id,
                series_id=series.id,
                version_type='normal',
                illustration_type='オリジナル'
            )
            db.session.add(version)
            db.session.commit()
            
            assert version.id is not None
            assert version.display_name == '普通版'
    
    def test_alt_art_version(self, app):
        """测试异画版本"""
        with app.app_context():
            series = Series(code='OP-14', language='jp', name='Test')
            db.session.add(series)
            db.session.commit()
            
            card = Card(
                card_number='OP14-001',
                language='jp',
                series_id=series.id,
                name='Test',
                card_type='LEADER',
                rarity='L',
                colors='赤'
            )
            db.session.add(card)
            db.session.commit()
            
            version = CardVersion(
                card_id=card.id,
                series_id=series.id,
                version_type='alt_art',
                version_suffix='_p1'
            )
            db.session.add(version)
            db.session.commit()
            
            assert version.display_name == '异画版'
