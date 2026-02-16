"""
价格历史模型
"""
from app import db
from datetime import datetime


class PriceHistory(db.Model):
    """
    价格历史记录
    用于存储价格走势数据
    """
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 所属卡片版本
    version_id = db.Column(db.Integer, db.ForeignKey('card_versions.id'), nullable=False, index=True)
    
    # 价格来源: snkrdunk_jp / snkrdunk_en / tcgplayer / other
    source = db.Column(db.String(30), nullable=False, index=True)
    
    # 货币: JPY / USD
    currency = db.Column(db.String(5), nullable=False, default='JPY')
    
    # 价格
    price = db.Column(db.Float, nullable=False)
    
    # 卡片状态: unsealed (未开封) / psa10 / psa9 / nm (near mint) / played
    condition = db.Column(db.String(20), default='unsealed')
    
    # 价格类型: lowest (最低价) / average (均价) / listing (挂牌价)
    price_type = db.Column(db.String(20), default='lowest')
    
    # 出品数量 (如果来源提供)
    listing_count = db.Column(db.Integer)
    
    # 原始URL (方便溯源)
    source_url = db.Column(db.String(500))
    
    # 记录时间
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 联合索引用于快速查询价格走势
    __table_args__ = (
        db.Index('idx_price_version_source_time', 'version_id', 'source', 'recorded_at'),
    )
    
    def __repr__(self):
        return f'<PriceHistory {self.version_id} {self.price} {self.currency}>'
    
    @property
    def display_price(self):
        """格式化显示价格"""
        if self.currency == 'JPY':
            return f'¥{self.price:,.0f}'
        elif self.currency == 'USD':
            return f'${self.price:,.2f}'
        return f'{self.price} {self.currency}'
