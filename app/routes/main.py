"""
メインルート
"""
from flask import Blueprint, render_template, request
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage
from app import db

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """ホームページ"""
    # 統計情報
    stats = {
        'series_count': Series.query.count(),
        'card_count': Card.query.count(),
        'leader_count': Card.query.filter_by(card_type='LEADER').count(),
        'version_count': CardVersion.query.count()
    }
    
    # 最新シリーズ（ブースターパック優先）
    recent_series = []
    for s in Series.query.filter_by(language='jp').order_by(Series.code.desc()).limit(20).all():
        card_count = Card.query.filter_by(series_id=s.id).count()
        recent_series.append({
            'id': s.id,
            'code': s.code,
            'name': s.name,
            'series_type': s.series_type,
            'card_count': card_count
        })
    
    # 上位6件のみ表示
    recent_series = recent_series[:6]
    
    return render_template('index.html', stats=stats, recent_series=recent_series)


@bp.route('/search')
def search():
    """検索ページ"""
    query = request.args.get('q', '').strip()
    color = request.args.get('color', '').strip()
    card_type = request.args.get('type', '').strip()
    rarity = request.args.get('rarity', '').strip()
    
    cards = []
    
    if query or color or card_type or rarity:
        q = Card.query
        
        if query:
            q = q.filter(
                db.or_(
                    Card.name.contains(query),
                    Card.card_number.contains(query),
                    Card.traits.contains(query)
                )
            )
        
        if color:
            q = q.filter(Card.colors.contains(color))
        
        if card_type:
            q = q.filter(Card.card_type == card_type)
        
        if rarity:
            q = q.filter(Card.rarity == rarity)
        
        cards = q.order_by(Card.card_number).limit(100).all()
    
    return render_template('search.html', cards=cards, query=query)
