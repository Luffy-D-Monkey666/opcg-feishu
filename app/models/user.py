"""
用户模型
"""
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    """用户"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 用户名 (唯一)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # 邮箱 (唯一)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # 密码哈希
    password_hash = db.Column(db.String(256), nullable=False)
    
    # 显示名称
    display_name = db.Column(db.String(100))
    
    # 头像URL
    avatar_url = db.Column(db.String(500))
    
    # 账号状态: active / inactive / banned
    status = db.Column(db.String(20), default='active')
    
    # 创建/更新时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    
    # 关系
    collections = db.relationship('UserCollection', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    wishlists = db.relationship('Wishlist', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    decks = db.relationship('Deck', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login 用户加载器"""
    return User.query.get(int(user_id))
