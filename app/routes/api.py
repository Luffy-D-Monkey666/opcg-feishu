"""
JSON API 路由 - 用于前端异步调用
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.card import Card, CardVersion
from app.models.collection import UserCollection, Wishlist
from app.models.deck import Deck, DeckCard
from app.models.price import PriceHistory
from app import db

# 用于卡组编辑的卡片搜索
from sqlalchemy import and_

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/cards/<int:card_id>/versions')
def get_card_versions(card_id):
    """获取卡片的所有版本"""
    card = Card.query.get_or_404(card_id)
    versions = []
    
    for v in card.versions:
        image = v.images.first()
        versions.append({
            'id': v.id,
            'type': v.version_type,
            'display_name': v.display_name,
            'has_star': v.has_star_mark,
            'image_url': image.local_path if image else None
        })
    
    return jsonify(versions)


@bp.route('/versions/<int:version_id>/prices')
def get_version_prices(version_id):
    """获取版本的价格历史"""
    version = CardVersion.query.get_or_404(version_id)
    
    # 获取最近90天的价格记录
    prices = version.prices.order_by(PriceHistory.recorded_at.desc()).limit(90).all()
    
    result = []
    for p in prices:
        result.append({
            'date': p.recorded_at.strftime('%Y-%m-%d'),
            'price': p.price,
            'currency': p.currency,
            'condition': p.condition,
            'source': p.source
        })
    
    return jsonify(result)


@bp.route('/collection/add', methods=['POST'])
@login_required
def add_to_collection():
    """添加到收藏"""
    data = request.get_json()
    version_id = data.get('version_id')
    
    if not version_id:
        return jsonify({'error': '缺少参数'}), 400
    
    # 检查是否已存在
    existing = UserCollection.query.filter_by(
        user_id=current_user.id,
        version_id=version_id
    ).first()
    
    if existing:
        existing.quantity += 1
    else:
        collection = UserCollection(
            user_id=current_user.id,
            version_id=version_id
        )
        db.session.add(collection)
    
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/collection/remove', methods=['POST'])
@login_required
def remove_from_collection():
    """从收藏移除"""
    data = request.get_json()
    version_id = data.get('version_id')
    
    item = UserCollection.query.filter_by(
        user_id=current_user.id,
        version_id=version_id
    ).first()
    
    if item:
        db.session.delete(item)
        db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/wishlist/add', methods=['POST'])
@login_required
def add_to_wishlist():
    """添加到愿望单"""
    data = request.get_json()
    version_id = data.get('version_id')
    
    if not version_id:
        return jsonify({'error': '缺少参数'}), 400
    
    existing = Wishlist.query.filter_by(
        user_id=current_user.id,
        version_id=version_id
    ).first()
    
    if not existing:
        wishlist = Wishlist(
            user_id=current_user.id,
            version_id=version_id
        )
        db.session.add(wishlist)
        db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/wishlist/remove', methods=['POST'])
@login_required
def remove_from_wishlist():
    """从愿望单移除"""
    data = request.get_json()
    version_id = data.get('version_id')
    
    item = Wishlist.query.filter_by(
        user_id=current_user.id,
        version_id=version_id
    ).first()
    
    if item:
        db.session.delete(item)
        db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/cards/search')
def search_cards():
    """搜索卡片 (用于卡组编辑)"""
    name = request.args.get('name', '').strip()
    card_type = request.args.get('type', '').strip()
    color = request.args.get('color', '').strip()
    
    q = Card.query.filter_by(language='jp')
    
    if name:
        q = q.filter(Card.name.contains(name))
    if card_type:
        q = q.filter(Card.card_type == card_type)
    if color:
        q = q.filter(Card.colors.contains(color))
    
    cards = q.order_by(Card.card_number).limit(50).all()
    
    result = []
    for card in cards:
        version = card.versions.first()
        if version:
            image = version.images.first()
            result.append({
                'id': card.id,
                'card_number': card.card_number,
                'name': card.name,
                'card_type': card.card_type,
                'rarity': card.rarity,
                'colors': card.colors,
                'version_id': version.id,
                'image_url': image.original_url if image else None
            })
    
    return jsonify(result)


@bp.route('/decks/<int:deck_id>/add-card', methods=['POST'])
@login_required
def add_card_to_deck(deck_id):
    """添加卡片到卡组"""
    deck = Deck.query.get_or_404(deck_id)
    
    if deck.user_id != current_user.id:
        return jsonify({'error': '无权限'}), 403
    
    data = request.get_json()
    version_id = data.get('version_id')
    quantity = data.get('quantity', 1)
    
    # 获取卡片类型
    version = CardVersion.query.get(version_id)
    if not version:
        return jsonify({'error': 'カードが見つかりません'}), 404
    
    card_type = version.card.card_type
    
    # LEADER 只能有1张
    if card_type == 'LEADER':
        # 先移除已有的 LEADER
        existing_leaders = DeckCard.query.join(CardVersion).join(Card).filter(
            DeckCard.deck_id == deck_id,
            Card.card_type == 'LEADER'
        ).all()
        for el in existing_leaders:
            db.session.delete(el)
        
        deck_card = DeckCard(
            deck_id=deck_id,
            version_id=version_id,
            quantity=1
        )
        db.session.add(deck_card)
    else:
        existing = DeckCard.query.filter_by(
            deck_id=deck_id,
            version_id=version_id
        ).first()
        
        if existing:
            existing.quantity = min(existing.quantity + quantity, 4)  # 最多4张
        else:
            deck_card = DeckCard(
                deck_id=deck_id,
                version_id=version_id,
                quantity=min(quantity, 4)
            )
            db.session.add(deck_card)
    
    deck.updated_at = db.func.now()
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/decks/<int:deck_id>/remove-card', methods=['POST'])
@login_required
def remove_card_from_deck(deck_id):
    """从卡组移除卡片"""
    deck = Deck.query.get_or_404(deck_id)
    
    if deck.user_id != current_user.id:
        return jsonify({'error': '无权限'}), 403
    
    data = request.get_json()
    version_id = data.get('version_id')
    remove_all = data.get('remove_all', False)
    
    item = DeckCard.query.filter_by(
        deck_id=deck_id,
        version_id=version_id
    ).first()
    
    if item:
        if remove_all or item.quantity <= 1:
            db.session.delete(item)
        else:
            item.quantity -= 1
        
        deck.updated_at = db.func.now()
        db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/decks/<int:deck_id>/delete', methods=['POST'])
@login_required
def delete_deck(deck_id):
    """删除卡组"""
    deck = Deck.query.get_or_404(deck_id)
    
    if deck.user_id != current_user.id:
        return jsonify({'error': '无权限'}), 403
    
    db.session.delete(deck)
    db.session.commit()
    
    return jsonify({'success': True})
