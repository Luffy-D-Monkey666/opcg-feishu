"""
OPCG TCG 图鉴网站 - Flask 应用工厂
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from urllib.parse import quote
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def cdn_image(url, width=None):
    """通过 CDN 代理加速图片加载"""
    if not url:
        return url
    # 使用 wsrv.nl 免费图片 CDN
    # 文档: https://wsrv.nl/docs/
    cdn_url = f"https://wsrv.nl/?url={quote(url, safe='')}"
    if width:
        cdn_url += f"&w={width}"
    # 添加质量优化
    cdn_url += "&output=webp&q=85"
    return cdn_url


def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    # 注册 Jinja2 过滤器
    app.jinja_env.filters['cdn_image'] = cdn_image
    
    # 注册蓝图
    from app.routes import main, cards, auth, user, api, prices
    
    app.register_blueprint(main.bp)
    app.register_blueprint(cards.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(prices.bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        # DON 卡数据现在从官方 PDF 导入，使用 scripts/import_don_from_pdf.py
    
    return app
