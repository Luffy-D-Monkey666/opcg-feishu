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
    """卡牌列表"""
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
    
    q = Card.query.filter(Card.language == lang)
    
    if series_id:
        q = q.filter(Card.series_id == series_id)
    if card_type:
        q = q.filter(Card.card_type == card_type)
    if color:
        q = q.filter(Card.colors.contains(color))
    if rarity:
        q = q.filter(Card.rarity == rarity)
    
    pagination = q.order_by(Card.card_number).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    cards = pagination.items
    series_list = Series.query.filter_by(language=lang).order_by(Series.code).all()
    
    # 语言统计
    stats = {
        'jp_count': Card.query.filter_by(language='jp').count(),
        'en_count': Card.query.filter_by(language='en').count()
    }
    
    return render_template('cards/list.html', 
                          cards=cards, 
                          pagination=pagination,
                          series_list=series_list,
                          stats=stats,
                          current_lang=lang)


@bp.route('/<card_number>')
def card_detail(card_number):
    """カード詳細"""
    card = Card.query.filter_by(card_number=card_number).first_or_404()
    
    # 预加载版本数据
    versions = card.versions.all()
    for v in versions:
        v.images_list = v.images.all()
    card.versions_list = versions
    
    # 同じシリーズの他のカード
    same_series_cards = Card.query.filter(
        Card.series_id == card.series_id,
        Card.id != card.id
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
