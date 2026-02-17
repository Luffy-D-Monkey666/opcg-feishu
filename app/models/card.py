"""
卡片模型 - 核心数据结构
"""
from app import db
from datetime import datetime


# 多对多关系表: 卡片 <-> 系列
# 允许同一张卡片出现在多个系列的图鉴中（如再录卡）
card_series = db.Table('card_series',
    db.Column('card_id', db.Integer, db.ForeignKey('cards.id'), primary_key=True),
    db.Column('series_id', db.Integer, db.ForeignKey('series.id'), primary_key=True),
    db.Column('is_reprint', db.Boolean, default=False),  # 是否为再录卡
    db.Column('source_info', db.String(500)),  # 该系列中的入手情報
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)


class Card(db.Model):
    """
    卡片基础信息
    一张卡片可能有多个版本 (普通、异画、漫画版等)
    """
    __tablename__ = 'cards'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 卡片编号 (如: OP09-119, ST01-012, P-001)
    card_number = db.Column(db.String(20), nullable=False, index=True)
    
    # 语言版本: jp / en
    language = db.Column(db.String(5), nullable=False, index=True)
    
    # 所属系列ID
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=False, index=True)
    
    # 卡片名称 (原文)
    name = db.Column(db.String(200), nullable=False)
    
    # 卡片类型: LEADER / CHARACTER / EVENT / STAGE
    card_type = db.Column(db.String(20), nullable=False, index=True)
    
    # 稀有度: L / C / UC / R / SR / SEC
    rarity = db.Column(db.String(10), nullable=False, index=True)
    
    # 颜色 (可多色，用逗号分隔): 赤,緑,青,紫,黄,黒
    colors = db.Column(db.String(50), nullable=False, index=True)
    
    # 费用 (CHARACTER/EVENT/STAGE)
    cost = db.Column(db.Integer)
    
    # 生命值 (LEADER)
    life = db.Column(db.Integer)
    
    # 力量/战力
    power = db.Column(db.Integer)
    
    # Counter值
    counter = db.Column(db.Integer)
    
    # 属性 (斬/打/特/知)
    attribute = db.Column(db.String(20))
    
    # 特征/种族 (用斜杠分隔)
    traits = db.Column(db.String(500))
    
    # 效果文本
    effect_text = db.Column(db.Text)
    
    # 触发效果
    trigger_text = db.Column(db.Text)
    
    # 来源信息 (官网显示的"入手情報")
    source_info = db.Column(db.String(500))
    
    # Block图标数量
    block_icon = db.Column(db.Integer)
    
    # 创建/更新时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    versions = db.relationship('CardVersion', backref='card', lazy='dynamic', cascade='all, delete-orphan')
    
    # 多对多关系：卡片可以属于多个系列
    in_series = db.relationship('Series', secondary='card_series', backref=db.backref('all_cards', lazy='dynamic'))
    
    # 联合唯一约束: card_number + language
    __table_args__ = (
        db.UniqueConstraint('card_number', 'language', name='uq_card_number_language'),
    )
    
    def __repr__(self):
        return f'<Card {self.card_number} {self.name} ({self.language})>'
    
    @property
    def color_list(self):
        """返回颜色列表"""
        return self.colors.split(',') if self.colors else []
    
    @property
    def trait_list(self):
        """返回特征列表"""
        return self.traits.split('/') if self.traits else []


class CardVersion(db.Model):
    """
    卡片版本
    同一编号的卡片可能有多个版本: 普通版、异画版、漫画版、特别版等
    
    重要: 每个版本关联到一个特定的系列，表示这个版本来自哪个补充包
    """
    __tablename__ = 'card_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 所属卡片
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False, index=True)
    
    # 来源系列 (这个版本来自哪个补充包)
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), index=True)
    
    # 版本类型: normal / alt_art / comic / special / promo
    version_type = db.Column(db.String(20), nullable=False, default='normal')
    
    # 版本后缀 (用于区分，如: _p1, _sp)
    version_suffix = db.Column(db.String(10), default='')
    
    # 是否有星星标记 (OP04+的异画卡)
    has_star_mark = db.Column(db.Boolean, default=False)
    
    # 稀有度后缀 (如 SR-P, SEC-SP, SEC-SPC)
    rarity_variant = db.Column(db.String(20))
    
    # 来源描述 (如: "フラッグシップバトル 優勝記念品")
    source_description = db.Column(db.String(500))
    
    # 插画类型: 原作/アニメ/オリジナル/その他
    illustration_type = db.Column(db.String(20))
    
    # 创建/更新时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    series = db.relationship('Series', backref=db.backref('versions', lazy='dynamic'))
    images = db.relationship('CardImage', backref='version', lazy='dynamic', cascade='all, delete-orphan')
    prices = db.relationship('PriceHistory', backref='version', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CardVersion {self.card.card_number} {self.version_type}>'
    
    @property
    def display_name(self):
        """显示名称"""
        type_names = {
            'normal': '普通版',
            'alt_art': '异画版',
            'comic': '漫画版',
            'special': '特别版',
            'promo': 'Promo'
        }
        return type_names.get(self.version_type, self.version_type)


class CardImage(db.Model):
    """
    卡片图片
    一个版本可能有多张图片 (正面、背面等，但OPCG一般只有正面)
    """
    __tablename__ = 'card_images'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 所属版本
    version_id = db.Column(db.Integer, db.ForeignKey('card_versions.id'), nullable=False, index=True)
    
    # 图片类型: front / back
    image_type = db.Column(db.String(10), default='front')
    
    # 本地存储路径 (相对于 static/images/cards/)
    local_path = db.Column(db.String(500))
    
    # 原始URL (官网)
    original_url = db.Column(db.String(500))
    
    # 图片宽高
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    
    # 创建时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CardImage {self.local_path}>'
