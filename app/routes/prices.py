"""
価格ルート - 価格追跡と走勢図表
"""
from flask import Blueprint, render_template, request, jsonify
from app.models.card import Card, CardVersion, CardImage
from app.models.series import Series
from app.models.price import PriceHistory
from app import db
from sqlalchemy import func, desc
from datetime import datetime, timedelta

bp = Blueprint('prices', __name__, url_prefix='/prices')


@bp.route('/')
def price_list():
    """価格一覧ページ - 価格変動が大きいカードなどを表示"""
    # 最新価格があるカードを取得
    subq = db.session.query(
        PriceHistory.version_id,
        func.max(PriceHistory.recorded_at).label('latest')
    ).group_by(PriceHistory.version_id).subquery()
    
    latest_prices = db.session.query(PriceHistory)\
        .join(subq, (PriceHistory.version_id == subq.c.version_id) & 
              (PriceHistory.recorded_at == subq.c.latest))\
        .order_by(desc(PriceHistory.price))\
        .limit(50).all()
    
    # 各価格にカード情報を付加
    for p in latest_prices:
        version = CardVersion.query.get(p.version_id)
        if version:
            p.version = version
            p.card = Card.query.get(version.card_id)
            p.image = version.images.first()
    
    return render_template('prices/list.html', prices=latest_prices)


@bp.route('/card/<card_number>')
def card_price_history(card_number):
    """カード価格履歴ページ - グラフ表示"""
    card = Card.query.filter_by(card_number=card_number).first_or_404()
    versions = card.versions.all()
    
    # 各バージョンの画像を取得
    for v in versions:
        v.image = v.images.first()
    
    return render_template('prices/card_history.html', card=card, versions=versions)


@bp.route('/api/history/<int:version_id>')
def api_price_history(version_id):
    """価格履歴APIエンドポイント - グラフデータ用"""
    days = request.args.get('days', 30, type=int)
    source = request.args.get('source', None)
    
    since = datetime.utcnow() - timedelta(days=days)
    
    q = PriceHistory.query.filter(
        PriceHistory.version_id == version_id,
        PriceHistory.recorded_at >= since
    )
    
    if source:
        q = q.filter(PriceHistory.source == source)
    
    prices = q.order_by(PriceHistory.recorded_at).all()
    
    data = [{
        'date': p.recorded_at.isoformat(),
        'price': p.price,
        'currency': p.currency,
        'source': p.source,
        'condition': p.condition
    } for p in prices]
    
    return jsonify({
        'version_id': version_id,
        'count': len(data),
        'data': data
    })


@bp.route('/api/compare')
def api_compare_prices():
    """複数カードの価格比較API"""
    version_ids = request.args.getlist('ids', type=int)
    days = request.args.get('days', 30, type=int)
    
    if not version_ids or len(version_ids) > 10:
        return jsonify({'error': 'Please provide 1-10 version IDs'}), 400
    
    since = datetime.utcnow() - timedelta(days=days)
    
    result = {}
    for vid in version_ids:
        prices = PriceHistory.query.filter(
            PriceHistory.version_id == vid,
            PriceHistory.recorded_at >= since
        ).order_by(PriceHistory.recorded_at).all()
        
        version = CardVersion.query.get(vid)
        card = Card.query.get(version.card_id) if version else None
        
        result[vid] = {
            'card_number': card.card_number if card else None,
            'card_name': card.name if card else None,
            'data': [{
                'date': p.recorded_at.isoformat(),
                'price': p.price,
                'currency': p.currency
            } for p in prices]
        }
    
    return jsonify(result)


@bp.route('/trending')
def trending():
    """価格上昇/下落トレンドページ"""
    # TODO: 実装 - 価格変動が大きいカードを表示
    return render_template('prices/trending.html')
