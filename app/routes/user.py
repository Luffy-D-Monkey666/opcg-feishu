"""
用户中心路由
"""
from flask import Blueprint, render_template, request, jsonify, abort, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from app.models.collection import UserCollection, Wishlist
from app.models.deck import Deck, DeckCard
from app.models.card import Card, CardVersion
from app.models.series import Series
from app import db
from sqlalchemy import func
import json
import csv
from io import StringIO

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/profile')
@login_required
def profile():
    """用户主页"""
    collection_count = current_user.collections.count()
    wishlist_count = current_user.wishlists.count()
    deck_count = current_user.decks.count()
    
    return render_template('user/profile.html',
                           collection_count=collection_count,
                           wishlist_count=wishlist_count,
                           deck_count=deck_count)


@bp.route('/collection')
@login_required
def collection():
    """我的收藏"""
    page = request.args.get('page', 1, type=int)
    per_page = 24
    
    pagination = current_user.collections.order_by(
        UserCollection.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('user/collection.html',
                           items=pagination.items,
                           pagination=pagination)


@bp.route('/wishlist')
@login_required
def wishlist():
    """愿望单"""
    page = request.args.get('page', 1, type=int)
    per_page = 24
    
    pagination = current_user.wishlists.order_by(
        Wishlist.priority.desc(),
        Wishlist.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('user/wishlist.html',
                           items=pagination.items,
                           pagination=pagination)


@bp.route('/decks')
@login_required
def decks():
    """我的卡组"""
    decks = current_user.decks.order_by(Deck.updated_at.desc()).all()
    return render_template('user/decks.html', decks=decks)


@bp.route('/decks/<int:deck_id>')
@login_required
def deck_detail(deck_id):
    """卡组详情"""
    deck = Deck.query.get_or_404(deck_id)
    
    # 检查权限
    if deck.user_id != current_user.id and not deck.is_public:
        abort(403)
    
    is_owner = deck.user_id == current_user.id
    
    # 获取卡组中的卡片，按类型分组
    deck_cards = deck.cards.all()
    leader = None
    characters = []
    events = []
    stages = []
    
    for dc in deck_cards:
        card_type = dc.version.card.card_type
        if card_type == 'LEADER':
            leader = dc
        elif card_type == 'CHARACTER':
            characters.append(dc)
        elif card_type == 'EVENT':
            events.append(dc)
        elif card_type == 'STAGE':
            stages.append(dc)
    
    # 计算数量
    char_count = sum(dc.quantity for dc in characters)
    event_count = sum(dc.quantity for dc in events)
    stage_count = sum(dc.quantity for dc in stages)
    
    # 给 deck 添加 card_count 属性
    deck.card_count = char_count + event_count + stage_count + (1 if leader else 0)
    
    return render_template('user/deck_detail.html', 
                          deck=deck,
                          is_owner=is_owner,
                          leader=leader,
                          characters=characters,
                          events=events,
                          stages=stages,
                          char_count=char_count,
                          event_count=event_count,
                          stage_count=stage_count)


@bp.route('/decks/<int:deck_id>/edit')
@login_required
def deck_edit(deck_id):
    """卡组编辑页"""
    deck = Deck.query.get_or_404(deck_id)
    
    if deck.user_id != current_user.id:
        abort(403)
    
    # 获取卡组中的卡片
    deck_cards = deck.cards.all()
    leader = None
    characters = []
    events = []
    stages = []
    
    for dc in deck_cards:
        card_type = dc.version.card.card_type
        if card_type == 'LEADER':
            leader = dc
        elif card_type == 'CHARACTER':
            characters.append(dc)
        elif card_type == 'EVENT':
            events.append(dc)
        elif card_type == 'STAGE':
            stages.append(dc)
    
    char_count = sum(dc.quantity for dc in characters)
    event_count = sum(dc.quantity for dc in events)
    stage_count = sum(dc.quantity for dc in stages)
    deck.card_count = char_count + event_count + stage_count + (1 if leader else 0)
    
    return render_template('user/deck_edit.html',
                          deck=deck,
                          leader=leader,
                          characters=characters,
                          events=events,
                          stages=stages,
                          char_count=char_count,
                          event_count=event_count,
                          stage_count=stage_count)


@bp.route('/decks/create', methods=['POST'])
@login_required
def deck_create():
    """创建新卡组"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    is_public = request.form.get('is_public') == 'on'
    
    if not name:
        flash('デッキ名を入力してください', 'error')
        return redirect(url_for('user.decks'))
    
    deck = Deck(
        user_id=current_user.id,
        name=name,
        description=description,
        is_public=is_public
    )
    db.session.add(deck)
    db.session.commit()
    
    flash(f'デッキ「{name}」を作成しました', 'success')
    return redirect(url_for('user.deck_edit', deck_id=deck.id))


# ==================== 阶段4: 收藏统计 ====================

@bp.route('/stats')
@login_required
def stats():
    """收藏统计页面"""
    from app.models.price import PriceHistory
    
    # 基础统计
    collection_count = current_user.collections.count()
    total_quantity = db.session.query(func.sum(UserCollection.quantity)).filter(
        UserCollection.user_id == current_user.id
    ).scalar() or 0
    
    # 收藏总价值估算
    # 获取每个收藏版本的最新价格
    subq = db.session.query(
        PriceHistory.version_id,
        func.max(PriceHistory.recorded_at).label('latest')
    ).group_by(PriceHistory.version_id).subquery()
    
    # 计算总价值 (价格 * 数量)
    total_value_usd = db.session.query(
        func.sum(PriceHistory.price * UserCollection.quantity)
    ).join(subq, (PriceHistory.version_id == subq.c.version_id) & 
           (PriceHistory.recorded_at == subq.c.latest))\
     .join(UserCollection, PriceHistory.version_id == UserCollection.version_id)\
     .filter(
         UserCollection.user_id == current_user.id,
         PriceHistory.currency == 'USD'
     ).scalar() or 0
    
    # 有价格数据的卡片数量
    cards_with_price = db.session.query(func.count(func.distinct(UserCollection.version_id)))\
        .join(PriceHistory, UserCollection.version_id == PriceHistory.version_id)\
        .filter(UserCollection.user_id == current_user.id).scalar() or 0
    
    # 最有价值的卡片 Top 5
    top_value_cards = db.session.query(
        Card.card_number,
        Card.name,
        PriceHistory.price,
        UserCollection.quantity,
        (PriceHistory.price * UserCollection.quantity).label('total_value')
    ).join(subq, (PriceHistory.version_id == subq.c.version_id) & 
           (PriceHistory.recorded_at == subq.c.latest))\
     .join(UserCollection, PriceHistory.version_id == UserCollection.version_id)\
     .join(CardVersion, UserCollection.version_id == CardVersion.id)\
     .join(Card, CardVersion.card_id == Card.id)\
     .filter(
         UserCollection.user_id == current_user.id,
         PriceHistory.currency == 'USD'
     ).order_by((PriceHistory.price * UserCollection.quantity).desc())\
     .limit(5).all()
    
    # 稀有度分布
    rarity_stats = db.session.query(
        Card.rarity,
        func.count(UserCollection.id).label('count'),
        func.sum(UserCollection.quantity).label('total')
    ).join(CardVersion, UserCollection.version_id == CardVersion.id)\
     .join(Card, CardVersion.card_id == Card.id)\
     .filter(UserCollection.user_id == current_user.id)\
     .group_by(Card.rarity).all()
    
    # 按类型分布
    type_stats = db.session.query(
        Card.card_type,
        func.count(UserCollection.id).label('count'),
        func.sum(UserCollection.quantity).label('total')
    ).join(CardVersion, UserCollection.version_id == CardVersion.id)\
     .join(Card, CardVersion.card_id == Card.id)\
     .filter(UserCollection.user_id == current_user.id)\
     .group_by(Card.card_type).all()
    
    # 按系列分布 (前10)
    series_stats = db.session.query(
        Series.code,
        Series.name,
        func.count(UserCollection.id).label('count'),
        func.sum(UserCollection.quantity).label('total')
    ).join(CardVersion, UserCollection.version_id == CardVersion.id)\
     .join(Card, CardVersion.card_id == Card.id)\
     .join(Series, Card.series_id == Series.id)\
     .filter(UserCollection.user_id == current_user.id)\
     .group_by(Series.id)\
     .order_by(func.sum(UserCollection.quantity).desc())\
     .limit(10).all()
    
    # 按颜色分布
    color_stats = db.session.query(
        Card.colors,
        func.count(UserCollection.id).label('count')
    ).join(CardVersion, UserCollection.version_id == CardVersion.id)\
     .join(Card, CardVersion.card_id == Card.id)\
     .filter(UserCollection.user_id == current_user.id)\
     .group_by(Card.colors).all()
    
    # 解析颜色 (可能有多色卡)
    color_counts = {}
    for colors, count in color_stats:
        if colors:
            for color in colors.split(','):
                color = color.strip()
                color_counts[color] = color_counts.get(color, 0) + count
    
    # 计算系列覆盖率
    all_series = Series.query.filter_by(language='jp').count()
    owned_series = db.session.query(func.count(func.distinct(Series.id)))\
        .join(Card, Series.id == Card.series_id)\
        .join(CardVersion, Card.id == CardVersion.card_id)\
        .join(UserCollection, CardVersion.id == UserCollection.version_id)\
        .filter(UserCollection.user_id == current_user.id).scalar() or 0
    
    return render_template('user/stats.html',
                           collection_count=collection_count,
                           total_quantity=total_quantity,
                           rarity_stats=rarity_stats,
                           type_stats=type_stats,
                           series_stats=series_stats,
                           color_counts=color_counts,
                           all_series=all_series,
                           owned_series=owned_series,
                           total_value_usd=total_value_usd,
                           cards_with_price=cards_with_price,
                           top_value_cards=top_value_cards)


# ==================== 阶段4: 卡组分享 ====================

@bp.route('/decks/<int:deck_id>/share', methods=['POST'])
@login_required
def deck_share(deck_id):
    """生成卡组分享码"""
    deck = Deck.query.get_or_404(deck_id)
    
    if deck.user_id != current_user.id:
        abort(403)
    
    if not deck.share_code:
        deck.generate_share_code()
        deck.is_public = True
        db.session.commit()
    
    return jsonify({
        'success': True,
        'share_code': deck.share_code,
        'share_url': url_for('user.deck_by_code', code=deck.share_code, _external=True)
    })


@bp.route('/d/<code>')
def deck_by_code(code):
    """通过分享码访问卡组"""
    deck = Deck.query.filter_by(share_code=code).first_or_404()
    
    if not deck.is_public:
        abort(404)
    
    # 重定向到卡组详情页
    return redirect(url_for('user.deck_public', deck_id=deck.id))


@bp.route('/decks/<int:deck_id>/public')
def deck_public(deck_id):
    """公开卡组详情页 (无需登录)"""
    deck = Deck.query.get_or_404(deck_id)
    
    if not deck.is_public:
        abort(404)
    
    # 获取卡组中的卡片，按类型分组
    deck_cards = deck.cards.all()
    leader = None
    characters = []
    events = []
    stages = []
    
    for dc in deck_cards:
        card_type = dc.version.card.card_type
        if card_type == 'LEADER':
            leader = dc
        elif card_type == 'CHARACTER':
            characters.append(dc)
        elif card_type == 'EVENT':
            events.append(dc)
        elif card_type == 'STAGE':
            stages.append(dc)
    
    char_count = sum(dc.quantity for dc in characters)
    event_count = sum(dc.quantity for dc in events)
    stage_count = sum(dc.quantity for dc in stages)
    deck.card_count = char_count + event_count + stage_count + (1 if leader else 0)
    
    return render_template('user/deck_public.html', 
                          deck=deck,
                          leader=leader,
                          characters=characters,
                          events=events,
                          stages=stages,
                          char_count=char_count,
                          event_count=event_count,
                          stage_count=stage_count)


# ==================== 阶段4: 导入导出 ====================

@bp.route('/collection/export')
@login_required
def collection_export():
    """导出收藏 (CSV)"""
    format_type = request.args.get('format', 'csv')
    
    collections = current_user.collections.all()
    
    if format_type == 'json':
        data = []
        for c in collections:
            card = c.version.card
            data.append({
                'card_number': card.card_number,
                'name': card.name,
                'card_type': card.card_type,
                'rarity': card.rarity,
                'series': card.series.code if card.series else '',
                'version_type': c.version.version_type,
                'quantity': c.quantity,
                'condition': c.condition,
                'purchase_price': c.purchase_price,
                'notes': c.notes
            })
        return Response(
            json.dumps(data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment; filename=collection.json'}
        )
    else:
        # CSV 格式
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Card Number', 'Name', 'Type', 'Rarity', 'Series', 'Version', 'Quantity', 'Condition', 'Price', 'Notes'])
        
        for c in collections:
            card = c.version.card
            writer.writerow([
                card.card_number,
                card.name,
                card.card_type,
                card.rarity,
                card.series.code if card.series else '',
                c.version.version_type,
                c.quantity,
                c.condition,
                c.purchase_price or '',
                c.notes or ''
            ])
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=collection.csv'}
        )


@bp.route('/collection/import', methods=['GET', 'POST'])
@login_required
def collection_import():
    """导入收藏"""
    if request.method == 'GET':
        return render_template('user/import.html')
    
    file = request.files.get('file')
    if not file:
        flash('ファイルを選択してください', 'error')
        return redirect(url_for('user.collection_import'))
    
    filename = file.filename.lower()
    imported = 0
    errors = []
    
    try:
        if filename.endswith('.json'):
            data = json.load(file)
            for item in data:
                card_number = item.get('card_number')
                version_type = item.get('version_type', 'normal')
                quantity = item.get('quantity', 1)
                
                # 查找卡片
                card = Card.query.filter_by(card_number=card_number, language='jp').first()
                if not card:
                    errors.append(f'{card_number}: カードが見つかりません')
                    continue
                
                version = card.versions.filter_by(version_type=version_type).first()
                if not version:
                    version = card.versions.first()
                
                if version:
                    existing = UserCollection.query.filter_by(
                        user_id=current_user.id,
                        version_id=version.id
                    ).first()
                    
                    if existing:
                        existing.quantity += quantity
                    else:
                        collection = UserCollection(
                            user_id=current_user.id,
                            version_id=version.id,
                            quantity=quantity
                        )
                        db.session.add(collection)
                    imported += 1
                    
        elif filename.endswith('.csv'):
            content = file.read().decode('utf-8')
            reader = csv.DictReader(StringIO(content))
            
            for row in reader:
                card_number = row.get('Card Number') or row.get('card_number')
                if not card_number:
                    continue
                    
                version_type = row.get('Version') or row.get('version_type', 'normal')
                quantity = int(row.get('Quantity') or row.get('quantity', 1))
                
                card = Card.query.filter_by(card_number=card_number, language='jp').first()
                if not card:
                    errors.append(f'{card_number}: カードが見つかりません')
                    continue
                
                version = card.versions.filter_by(version_type=version_type).first()
                if not version:
                    version = card.versions.first()
                
                if version:
                    existing = UserCollection.query.filter_by(
                        user_id=current_user.id,
                        version_id=version.id
                    ).first()
                    
                    if existing:
                        existing.quantity += quantity
                    else:
                        collection = UserCollection(
                            user_id=current_user.id,
                            version_id=version.id,
                            quantity=quantity
                        )
                        db.session.add(collection)
                    imported += 1
        else:
            flash('サポートされていないファイル形式です (CSV/JSONのみ)', 'error')
            return redirect(url_for('user.collection_import'))
        
        db.session.commit()
        
        if errors:
            flash(f'{imported}枚をインポートしました。{len(errors)}件のエラー。', 'warning')
        else:
            flash(f'{imported}枚をインポートしました', 'success')
            
    except Exception as e:
        flash(f'インポートエラー: {str(e)}', 'error')
    
    return redirect(url_for('user.collection'))


@bp.route('/decks/<int:deck_id>/export')
@login_required
def deck_export(deck_id):
    """导出卡组"""
    deck = Deck.query.get_or_404(deck_id)
    
    if deck.user_id != current_user.id and not deck.is_public:
        abort(403)
    
    format_type = request.args.get('format', 'json')
    
    if format_type == 'json':
        return Response(
            json.dumps(deck.to_export_dict(), ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=deck_{deck.id}.json'}
        )
    else:
        # 简单文本格式 (类似 PTCGO 格式)
        lines = [f'// {deck.name}']
        if deck.description:
            lines.append(f'// {deck.description}')
        lines.append('')
        
        for dc in deck.cards:
            card = dc.version.card
            lines.append(f'{dc.quantity}x {card.card_number} {card.name}')
        
        return Response(
            '\n'.join(lines),
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename=deck_{deck.id}.txt'}
        )
