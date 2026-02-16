"""
卡组模型
"""
from app import db
from datetime import datetime
import secrets
import string


def generate_share_code(length=8):
    """生成分享码 (大写字母+数字)"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Deck(db.Model):
    """
    用户卡组
    """
    __tablename__ = 'decks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 所属用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 卡组名称
    name = db.Column(db.String(100), nullable=False)
    
    # 卡组描述
    description = db.Column(db.Text)
    
    # 卡组格式: standard / limited
    format = db.Column(db.String(20), default='standard')
    
    # Leader卡片版本ID
    leader_version_id = db.Column(db.Integer, db.ForeignKey('card_versions.id'))
    
    # 是否公开
    is_public = db.Column(db.Boolean, default=False)
    
    # 分享码 (用于短链接分享)
    share_code = db.Column(db.String(20), unique=True, index=True)
    
    # 封面图片 (可选)
    cover_image = db.Column(db.String(500))
    
    # 创建/更新时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    leader = db.relationship('CardVersion', foreign_keys=[leader_version_id])
    cards = db.relationship('DeckCard', backref='deck', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Deck {self.name}>'
    
    @property
    def total_cards(self):
        """卡组总卡片数"""
        return sum(dc.quantity for dc in self.cards)
    
    @property
    def card_count(self):
        """兼容属性"""
        return self.total_cards
    
    def get_leader(self):
        """获取 LEADER 卡片"""
        for dc in self.cards:
            if dc.version.card.card_type == 'LEADER':
                return dc
        return None
    
    @property
    def estimated_price(self):
        """估算总价"""
        total = 0
        for dc in self.cards:
            if dc.version.prices.first():
                latest_price = dc.version.prices.order_by(
                    db.desc('recorded_at')
                ).first()
                if latest_price:
                    total += latest_price.price * dc.quantity
        return total
    
    def generate_share_code(self):
        """生成唯一分享码"""
        while True:
            code = generate_share_code()
            existing = Deck.query.filter_by(share_code=code).first()
            if not existing:
                self.share_code = code
                return code
    
    def to_export_dict(self):
        """导出为字典格式"""
        cards_data = []
        for dc in self.cards:
            card = dc.version.card
            cards_data.append({
                'card_number': card.card_number,
                'name': card.name,
                'card_type': card.card_type,
                'quantity': dc.quantity,
                'version_type': dc.version.version_type
            })
        return {
            'name': self.name,
            'description': self.description,
            'format': self.format,
            'cards': cards_data
        }


class DeckCard(db.Model):
    """
    卡组中的卡片
    """
    __tablename__ = 'deck_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 所属卡组
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False, index=True)
    
    # 卡片版本
    version_id = db.Column(db.Integer, db.ForeignKey('card_versions.id'), nullable=False, index=True)
    
    # 数量 (通常最多4张)
    quantity = db.Column(db.Integer, default=1)
    
    # 关系
    version = db.relationship('CardVersion', backref='deck_cards')
    
    # 联合唯一约束
    __table_args__ = (
        db.UniqueConstraint('deck_id', 'version_id', name='uq_deck_card'),
    )
    
    def __repr__(self):
        return f'<DeckCard deck={self.deck_id} version={self.version_id} x{self.quantity}>'
