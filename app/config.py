"""
配置文件 - 开发/生产环境分离
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'opcg-tcg-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 每页显示的卡片数量
    CARDS_PER_PAGE = 24
    
    # 图片存储路径
    CARD_IMAGES_PATH = os.path.join(basedir, 'static', 'images', 'cards')


class DevelopmentConfig(BaseConfig):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '..', 'data', 'opcg_dev.db')


class ProductionConfig(BaseConfig):
    """生产环境配置"""
    DEBUG = False
    
    # Handle Render's postgres:// vs SQLAlchemy's postgresql://
    _db_uri = os.environ.get('DATABASE_URL', '')
    if _db_uri.startswith('postgres://'):
        _db_uri = _db_uri.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_uri or 'sqlite:///' + os.path.join(basedir, '..', 'data', 'opcg.db')


class TestingConfig(BaseConfig):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
