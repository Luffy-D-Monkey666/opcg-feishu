"""
收藏和愿望单模型
"""
from app import db
from datetime import datetime


class UserCollection(db.Model):
    """
    用户收藏 - 已拥有的卡片
    """
    __tablename__ = 'user_collections'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 所属用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 收藏的卡片版本
    version_id = db.Column(db.Integer, db.ForeignKey('card_versions.id'), nullable=False, index=True)
    
    # 拥有数量
    quantity = db.Column(db.Integer, default=1)
    
    # 卡片状态: mint / near_mint / played / damaged
    condition = db.Column(db.String(20), default='near_mint')
    
    # PSA/BGS评级 (如果有)
    grade = db.Column(db.String(20))
    
    # 购入价格 (可选)
    purchase_price = db.Column(db.Float)
    
    # 购入日期 (可选)
    purchase_date = db.Column(db.Date)
    
    # 备注
    notes = db.Column(db.Text)
    
    # 创建/更新时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    version = db.relationship('CardVersion', backref='collections')
    
    # 联合唯一约束: user_id + version_id + condition + grade
    __table_args__ = (
        db.UniqueConstraint('user_id', 'version_id', 'condition', 'grade', name='uq_user_collection'),
    )
    
    def __repr__(self):
        return f'<UserCollection user={self.user_id} version={self.version_id}>'


class Wishlist(db.Model):
    """
    愿望单 - 想要的卡片
    """
    __tablename__ = 'wishlists'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 所属用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 想要的卡片版本
    version_id = db.Column(db.Integer, db.ForeignKey('card_versions.id'), nullable=False, index=True)
    
    # 想要数量
    quantity = db.Column(db.Integer, default=1)
    
    # 期望价格上限 (可选，用于价格提醒)
    max_price = db.Column(db.Float)
    
    # 优先级: low / medium / high
    priority = db.Column(db.String(10), default='medium')
    
    # 备注
    notes = db.Column(db.Text)
    
    # 创建/更新时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    version = db.relationship('CardVersion', backref='wishlists')
    
    # 联合唯一约束
    __table_args__ = (
        db.UniqueConstraint('user_id', 'version_id', name='uq_wishlist'),
    )
    
    def __repr__(self):
        return f'<Wishlist user={self.user_id} version={self.version_id}>'
