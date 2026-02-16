"""
OPCG TCG 图鉴网站 - Flask 应用工厂
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
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
    
    return app
