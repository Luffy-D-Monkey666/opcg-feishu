"""
カードルート
"""
from flask import Blueprint, render_template, request, abort
from flask_login import current_user
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage
from app.models.collection import UserCollection, Wishlist
from app.models.price import PriceHistory
from app import db
from sqlalchemy import func

bp = Blueprint('cards', __name__, url_prefix='/cards')


@bp.route('/')
def card_list():
    """卡牌列表 - 基于版本展示，支持平行卡"""
    page = request.args.get('page', 1, type=int)
    per_page = 24
    
    # 语言过滤
    lang = request.args.get('lang', 'jp').strip()
    if lang not in ('jp', 'en'):
        lang = 'jp'
    
    # 其他过滤器
    series_id = request.args.get('series', type=int)
    card_type = request.args.get('type', '').strip()
    color = request.args.get('color', '').strip()
    rarity = request.args.get('rarity', '').strip()
    illustration = request.args.get('illustration', '').strip()
    
    # 当选择了系列时，基于 CardVersion 查询（包含平行卡/异画卡）
    # 当没有选择系列时，基于 Card 查询（每个卡号只显示一次）
    if series_id:
        # 基于版本查询 - 显示该系列所有版本（包括平行卡）
        q = CardVersion.query.filter(CardVersion.series_id == series_id)\
            .join(Card, CardVersion.card_id == Card.id)\
            .filter(Card.language == lang)
        
        if card_type:
            q = q.filter(Card.card_type == card_type)
        if color:
            q = q.filter(Card.colors.contains(color))
        if rarity:
            q = q.filter(Card.rarity == rarity)
        if illustration:
            q = q.filter(CardVersion.illustration_type == illustration)
        
        pagination = q.order_by(Card.card_number, CardVersion.version_suffix).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 将版本转换为统一的显示格式
        versions = pagination.items
        cards = []
        for v in versions:
            card = Card.query.get(v.card_id)
            # 创建一个包装对象，包含版本信息
            card_display = CardDisplay(card, v)
            cards.append(card_display)
    else:
        # 没有选择系列时，按卡片查询（每个卡号只显示一次）
        q = Card.query.filter(Card.language == lang)
        
        if card_type:
            q = q.filter(Card.card_type == card_type)
        if color:
            q = q.filter(Card.colors.contains(color))
        if rarity:
            q = q.filter(Card.rarity == rarity)
        
        # 插画类型筛选（需要 JOIN CardVersion）
        if illustration:
            q = q.join(CardVersion, Card.id == CardVersion.card_id)\
                 .filter(CardVersion.illustration_type == illustration)\
                 .distinct()
        
        pagination = q.order_by(Card.card_number).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        cards = [CardDisplay(c, None) for c in pagination.items]
    
    series_list = Series.query.filter_by(language=lang).order_by(Series.code).all()
    
    # 系列分组（用于侧边栏树形导航）
    series_groups = _get_series_groups(lang)
    
    # 当前选中的系列
    current_series = None
    if series_id:
        current_series = Series.query.get(series_id)
    
    # 语言统计
    stats = {
        'jp_count': Card.query.filter_by(language='jp').count(),
        'en_count': Card.query.filter_by(language='en').count()
    }
    
    return render_template('cards/list.html', 
                          cards=cards, 
                          pagination=pagination,
                          series_list=series_list,
                          series_groups=series_groups,
                          current_series=current_series,
                          stats=stats,
                          current_lang=lang)


class CardDisplay:
    """卡片显示包装类，统一卡片和版本的显示接口"""
    def __init__(self, card, version=None):
        self.card = card
        self.version = version
        self.card_number = card.card_number
        self.name = card.name
        self.card_type = card.card_type
        self.rarity = card.rarity
        self.colors = card.colors
        
    @property
    def versions(self):
        """兼容模板中的 card.versions.first() 调用"""
        return self
    
    def first(self):
        """返回指定版本或卡片的第一个版本"""
        if self.version:
            return self.version
        return self.card.versions.first()
    
    @property
    def display_version_id(self):
        """用于详情页链接的版本ID"""
        if self.version:
            return self.version.id
        return None
    
    @property
    def source_description(self):
        """获取入手情报（版本级别）"""
        if self.version:
            return self.version.source_description
        return None
    
    @property
    def illustration_type(self):
        """获取插画类型（版本级别）"""
        if self.version:
            return self.version.illustration_type
        return None


def _get_series_groups(lang: str) -> dict:
    """获取系列分组数据"""
    series_all = Series.query.filter_by(language=lang).order_by(Series.code.desc()).all()
    
    # 分组映射
    type_names = {
        'booster': '📦 补充包 (Booster)',
        'starter': '🎴 起始套牌 (Starter)',
        'extra': '✨ 额外补充 (Extra)',
        'premium': '👑 高级补充 (Premium)',
        'promo': '🎁 促销卡 (Promo)',
        'limited': '🔒 限定商品 (Limited)',
        'ultimate': '⚔️ 终极套牌 (Ultimate)',
        'family': '👨‍👩‍👧 家庭套牌 (Family)',
        'other': '📁 其他'
    }
    
    groups = {}
    for s in series_all:
        group_name = type_names.get(s.series_type, type_names['other'])
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(s)
    
    # 排序：按定义顺序
    ordered_groups = {}
    for type_key in ['booster', 'starter', 'extra', 'premium', 'promo', 'limited', 'ultimate', 'family', 'other']:
        group_name = type_names.get(type_key)
        if group_name and group_name in groups:
            ordered_groups[group_name] = groups[group_name]
    
    return ordered_groups


@bp.route('/<card_number>/all-versions')
def card_all_versions(card_number):
    """查看同一语种内所有系列中该卡号的全部版本"""
    lang = request.args.get('lang', 'jp').strip()
    if lang not in ('jp', 'en'):
        lang = 'jp'
    
    # 查找该语种的卡片
    card = Card.query.filter_by(card_number=card_number, language=lang).first_or_404()
    
    # 获取该语种所有系列中该卡号的版本
    # 通过 CardVersion.series_id 关联到 Series，筛选同语种
    versions = CardVersion.query.filter_by(card_id=card.id)\
        .join(Series, CardVersion.series_id == Series.id)\
        .filter(Series.language == lang)\
        .order_by(Series.code.desc(), CardVersion.version_suffix)\
        .all()
    
    # 按系列分组
    series_versions = {}
    for v in versions:
        series = Series.query.get(v.series_id)
        if series:
            if series.code not in series_versions:
                series_versions[series.code] = {
                    'series': series,
                    'versions': []
                }
            v.images_list = v.images.all()
            series_versions[series.code]['versions'].append(v)
    
    return render_template('cards/all_versions.html',
                          card=card,
                          series_versions=series_versions,
                          current_lang=lang)


@bp.route('/<card_number>')
def card_detail(card_number):
    """卡片详情"""
    # 支持语言参数
    lang = request.args.get('lang', 'jp').strip()
    if lang not in ('jp', 'en'):
        lang = 'jp'
    
    # 支持版本参数（用于显示特定版本的图片）
    target_version_id = request.args.get('version_id', type=int)
    
    # 先尝试查找指定语言的卡片
    card = Card.query.filter_by(card_number=card_number, language=lang).first()
    
    # 如果找不到，尝试另一种语言
    if not card:
        other_lang = 'en' if lang == 'jp' else 'jp'
        card = Card.query.filter_by(card_number=card_number, language=other_lang).first_or_404()
        lang = other_lang  # 更新实际语言
    
    # 预加载版本数据（只加载同语言系列的版本）
    versions = CardVersion.query.filter_by(card_id=card.id)\
        .join(Series, CardVersion.series_id == Series.id)\
        .filter(Series.language == lang)\
        .all()
    
    # 如果没有版本，回退到所有版本
    if not versions:
        versions = card.versions.all()
    
    # 如果指定了版本ID，把该版本移到第一位
    if target_version_id:
        target_version = None
        other_versions = []
        for v in versions:
            if v.id == target_version_id:
                target_version = v
            else:
                other_versions.append(v)
        if target_version:
            versions = [target_version] + other_versions
    
    for v in versions:
        v.images_list = v.images.all()
    card.versions_list = versions
    
    # 同系列的其他卡片（同语言）
    same_series_cards = Card.query.filter(
        Card.series_id == card.series_id,
        Card.id != card.id,
        Card.language == lang
    ).order_by(Card.card_number).limit(12).all()
    
    # コレクション/ウィッシュリスト状態をチェック
    in_collection = None
    in_wishlist = None
    if current_user.is_authenticated and versions:
        first_version_id = versions[0].id
        in_collection = UserCollection.query.filter_by(
            user_id=current_user.id,
            version_id=first_version_id
        ).first()
        in_wishlist = Wishlist.query.filter_by(
            user_id=current_user.id,
            version_id=first_version_id
        ).first()
    
    # 获取最新价格（每个版本取最新一条）
    prices = []
    for v in versions:
        latest_price = PriceHistory.query.filter_by(version_id=v.id)\
            .order_by(PriceHistory.recorded_at.desc()).first()
        if latest_price:
            latest_price.version = v
            prices.append(latest_price)
    
    return render_template('cards/detail.html', 
                          card=card, 
                          versions=versions,
                          same_series_cards=same_series_cards,
                          current_lang=lang,
                          in_collection=in_collection,
                          in_wishlist=in_wishlist,
                          prices=prices)


@bp.route('/series/')
def series_list():
    """系列列表"""
    series_type = request.args.get('type', '').strip()
    lang = request.args.get('lang', 'jp').strip()
    if lang not in ('jp', 'en'):
        lang = 'jp'
    
    q = Series.query.filter_by(language=lang)
    
    if series_type:
        q = q.filter(Series.series_type == series_type)
    
    series_all = q.order_by(Series.code.desc()).all()
    
    # 版本数统计
    series_list_data = []
    for s in series_all:
        version_count = CardVersion.query.filter_by(series_id=s.id).count()
        series_list_data.append({
            'id': s.id,
            'code': s.code,
            'name': s.name,
            'series_type': s.series_type,
            'card_count': version_count
        })
    
    # 语言统计
    stats = {
        'jp_count': Card.query.filter_by(language='jp').count(),
        'en_count': Card.query.filter_by(language='en').count()
    }
    
    return render_template('cards/series_list.html', 
                          series_list=series_list_data,
                          stats=stats,
                          current_lang=lang)


@bp.route('/series/<int:series_id>')
def series_detail(series_id):
    """シリーズ詳細 - 显示该系列的所有卡片版本（包括再录卡）"""
    series = Series.query.get_or_404(series_id)
    
    card_type = request.args.get('type', '').strip()
    
    # 新逻辑：按 series_id 获取该系列的所有版本，然后关联到卡片
    versions_query = CardVersion.query.filter_by(series_id=series_id)\
        .join(Card, CardVersion.card_id == Card.id)
    
    if card_type:
        versions_query = versions_query.filter(Card.card_type == card_type)
    
    versions = versions_query.order_by(Card.card_number, CardVersion.version_suffix).all()
    
    # 为每个版本加载卡片信息
    for v in versions:
        v.card_info = Card.query.get(v.card_id)
        v.images_list = v.images.all()
    
    # 统计（按版本所属卡片的类型统计）
    stats = {
        'leader': CardVersion.query.filter_by(series_id=series_id)\
            .join(Card).filter(Card.card_type == 'LEADER').count(),
        'character': CardVersion.query.filter_by(series_id=series_id)\
            .join(Card).filter(Card.card_type == 'CHARACTER').count(),
        'event': CardVersion.query.filter_by(series_id=series_id)\
            .join(Card).filter(Card.card_type == 'EVENT').count(),
        'stage': CardVersion.query.filter_by(series_id=series_id)\
            .join(Card).filter(Card.card_type == 'STAGE').count()
    }
    
    # 总版本数
    total_versions = CardVersion.query.filter_by(series_id=series_id).count()
    
    return render_template('cards/series_detail.html', 
                          series=series, 
                          versions=versions,
                          stats=stats,
                          total_versions=total_versions)
