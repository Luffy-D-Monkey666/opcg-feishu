"""
系列/补充包模型
"""
from app import db
from datetime import datetime


class Series(db.Model):
    """系列/补充包"""
    __tablename__ = 'series'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 系列标识 (如: OP-14, ST-01, PRB-01)
    code = db.Column(db.String(20), nullable=False, index=True)
    
    # 语言版本: jp / en
    language = db.Column(db.String(5), nullable=False, index=True)
    
    # 系列名称 (原文)
    name = db.Column(db.String(200), nullable=False)
    
    # 系列类型: booster / starter / extra / premium / promo / limited
    series_type = db.Column(db.String(20), nullable=False)
    
    # 官网的 series 参数值 (用于爬取)
    official_series_id = db.Column(db.String(20))
    
    # 发售日期
    release_date = db.Column(db.Date)
    
    # 卡片数量 (官方公布)
    card_count = db.Column(db.Integer)
    
    # 封面图片
    cover_image = db.Column(db.String(500))
    
    # 创建/更新时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    cards = db.relationship('Card', backref='series', lazy='dynamic')
    
    # 联合唯一约束: code + language
    __table_args__ = (
        db.UniqueConstraint('code', 'language', name='uq_series_code_language'),
    )
    
    def __repr__(self):
        return f'<Series {self.code} ({self.language})>'
