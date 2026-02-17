"""
路由测试
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
        # 创建测试数据
        _create_test_data()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


def _create_test_data():
    """创建测试数据"""
    series = Series(
        code='OP-14',
        language='jp',
        name='ブースターパック 蒼海の七傑【OP-14】',
        series_type='booster'
    )
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
        power=5000,
        effect_text='测试效果文本'
    )
    db.session.add(card)
    db.session.commit()
    
    version = CardVersion(
        card_id=card.id,
        series_id=series.id,
        version_type='normal'
    )
    db.session.add(version)
    
    image = CardImage(
        version_id=1,
        original_url='https://example.com/card.png'
    )
    db.session.add(image)
    db.session.commit()


class TestMainRoutes:
    """主页路由测试"""
    
    def test_index(self, client):
        """测试首页"""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_search_page(self, client):
        """测试搜索页"""
        response = client.get('/search')
        assert response.status_code == 200


class TestCardRoutes:
    """卡片路由测试"""
    
    def test_card_list(self, client):
        """测试卡片列表"""
        response = client.get('/cards/')
        assert response.status_code == 200
    
    def test_card_list_with_lang(self, client):
        """测试带语言参数的卡片列表"""
        response = client.get('/cards/?lang=jp')
        assert response.status_code == 200
    
    def test_card_detail(self, client):
        """测试卡片详情"""
        response = client.get('/cards/OP14-001?lang=jp')
        assert response.status_code == 200
    
    def test_card_not_found(self, client):
        """测试不存在的卡片"""
        response = client.get('/cards/NOTEXIST-999?lang=jp')
        assert response.status_code == 404
    
    def test_series_list(self, client):
        """测试系列列表"""
        response = client.get('/cards/series')
        assert response.status_code == 200


class TestAPIRoutes:
    """API 路由测试"""
    
    def test_search_api(self, client):
        """测试搜索 API"""
        response = client.get('/api/cards/search?q=ロー')
        assert response.status_code == 200
        data = response.get_json()
        assert 'results' in data
    
    def test_search_api_empty(self, client):
        """测试空搜索"""
        response = client.get('/api/cards/search?q=')
        assert response.status_code == 200


class TestAuthRoutes:
    """认证路由测试"""
    
    def test_login_page(self, client):
        """测试登录页"""
        response = client.get('/auth/login')
        assert response.status_code == 200
    
    def test_register_page(self, client):
        """测试注册页"""
        response = client.get('/auth/register')
        assert response.status_code == 200
