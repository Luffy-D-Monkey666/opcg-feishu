"""
OPCG TCG 图鉴网站 - Flask 应用工厂
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from urllib.parse import quote
import os

db = SQLAlchemy()
login_manager = LoginManager()


def cdn_image(url, width=None):
    """通过 CDN 代理加速图片加载"""
    if not url:
        return url
    # 使用 wsrv.nl 免费图片 CDN
    # 文档: https://wsrv.nl/docs/
    cdn_url = f"https://wsrv.nl/?url={quote(url, safe='')}"
    if width:
        cdn_url += f"&w={width}"
    # 添加质量优化
    cdn_url += "&output=webp&q=85"
    return cdn_url


def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    # 注册 Jinja2 过滤器
    app.jinja_env.filters['cdn_image'] = cdn_image
    
    # 注册蓝图
    from app.routes import main, cards, auth, user, api, prices
    
    app.register_blueprint(main.bp)
    app.register_blueprint(cards.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(prices.bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 检查并导入 DON 卡数据
        _ensure_don_cards()
    
    return app


def _ensure_don_cards():
    """确保 DON 卡数据存在"""
    from app.models.series import Series
    from app.models.card import Card
    
    # 检查 DON 系列是否存在
    don_series = Series.query.filter_by(code='DON', language='jp').first()
    if don_series:
        return  # 已存在，跳过
    
    print("正在导入 DON 卡数据...")
    
    # 创建 DON 系列
    don_series = Series(
        code='DON',
        name='ドン!!カード',
        series_type='don',
        language='jp'
    )
    db.session.add(don_series)
    db.session.commit()
    
    # 导入 DON 卡数据
    from app.models.card import CardVersion, CardImage
    
    # PRB01 DON 卡角色名
    PRB01_NAMES = {
        '001': 'アイスバーグ', '002': 'ヴィンスモーク・レイジュ', '003': 'ウタ',
        '004': 'エドワード・ニューゲート', '005': 'エネル', '006': 'エンポリオ・イワンコフ',
        '007': 'カイドウ', '008': 'キング', '009': 'クイーン', '010': 'クロコダイル',
        '011': 'ゲッコー・モリア', '012': '光月おでん', '013': 'サカズキ', '014': 'サボ',
        '015': 'シャーロット・カタクリ', '016': 'シャーロット・リンリン',
        '017': 'トラファルガー・ロー', '018': 'ドンキホーテ・ドフラミンゴ',
        '019': 'ドンキホーテ・ロシナンテ', '020': 'ネフェルタリ・ビビ', '021': 'ペローナ',
        '022': 'ホーディ・ジョーンズ', '023': 'ポートガス・D・エース', '024': 'マゼラン',
        '025': 'モンキー・D・ルフィ', '026': 'ヤマト', '027': 'ユースタス・キッド',
        '028': 'レベッカ', '029': 'ロブ・ルッチ', '030': 'ロロノア・ゾロ',
    }
    
    PRB02_NAMES = {
        '001': 'ウソップ', '002': 'カルガラ', '003': 'キャロット', '004': 'キュロス',
        '005': 'コビー', '006': 'サンジ', '007': 'シーザー', '008': 'シャーロット・プリン',
        '009': 'シャンクス', '010': 'ジュエリー・ボニー', '011': 'シュガー', '012': 'しらほし',
        '013': 'ジンベエ', '014': 'スモーカー', '015': 'トニートニー・チョッパー',
        '016': 'ナミ', '017': 'ニコ・ロビン', '018': 'バギー', '019': 'ハンニャバル',
        '020': 'フォクシー', '021': 'ベガパンク', '022': 'ボア・ハンコック',
        '023': 'マーシャル・D・ティーチ', '024': 'マルコ', '025': '革命軍',
        '026': 'スネイクマン', '027': 'ニカルフィ', '028': 'ヤマト',
        '029': 'ODYSSEY', '030': 'ロブ・ルッチ',
    }
    
    BASE_URL = "https://tierone-media-op.com/wp-content/uploads/"
    
    def add_don_card(card_number, name, source, image_urls):
        card = Card(
            card_number=card_number,
            series_id=don_series.id,
            language='jp',
            name=name,
            card_type='DON',
            rarity='DON',
            colors='',
            source_info=source
        )
        db.session.add(card)
        db.session.flush()
        
        for vtype, url in image_urls.items():
            suffix = '' if vtype == 'normal' else ('_p' if vtype == 'parallel' else '_sp')
            version = CardVersion(
                card_id=card.id,
                series_id=don_series.id,
                version_type='normal' if vtype == 'normal' else 'alt_art',
                version_suffix=suffix,
                source_description=source
            )
            db.session.add(version)
            db.session.flush()
            
            img = CardImage(version_id=version.id, original_url=url)
            db.session.add(img)
    
    # 基础 DON 卡
    add_don_card('DON-NORMAL', 'ドン!!カード (通常)', 'スタートデッキ/ブースターパック',
                 {'normal': f'{BASE_URL}don-normal.webp'})
    add_don_card('DON-FOIL', 'ドン!!カード (フォイル)', 'アルティメットデッキ',
                 {'normal': f'{BASE_URL}don-foil.webp'})
    
    # OP01-OP14 DON 卡
    for i in range(1, 15):
        num = str(i).zfill(2)
        add_don_card(f'OP{num}-DON', 'ドン!!カード', f'ブースターパック【OP-{num}】',
                     {'normal': f'{BASE_URL}op{num}-doncard.webp'})
    
    # EB DON 卡
    for i in [2, 3]:
        num = str(i).zfill(2)
        add_don_card(f'EB{num}-DON', 'ドン!!カード', f'エクストラブースター【EB-{num}】',
                     {'normal': f'{BASE_URL}eb{num}-doncard.webp'})
    
    # PRB01 DON 卡
    for num, name in PRB01_NAMES.items():
        add_don_card(f'PRB01-DON-{num}', f'ドン!!カード ({name})', 'ONE PIECE CARD THE BEST【PRB-01】',
                     {'normal': f'{BASE_URL}don_card_prb01-{num}.webp',
                      'parallel': f'{BASE_URL}don_card_prb01-{num}p.webp',
                      'super_parallel': f'{BASE_URL}don_card_prb01-{num}sp.webp'})
    
    # PRB02 DON 卡
    for num, name in PRB02_NAMES.items():
        add_don_card(f'PRB02-DON-{num}', f'ドン!!カード ({name})', 'ONE PIECE CARD THE BEST Vol.2【PRB-02】',
                     {'normal': f'{BASE_URL}don_card_prb02-{num}.webp',
                      'parallel': f'{BASE_URL}don_card_prb02-{num}p.webp',
                      'super_parallel': f'{BASE_URL}don_card_prb02-{num}sp.webp'})
    
    db.session.commit()
    print(f"DON 卡导入完成！共 {Card.query.filter_by(card_type='DON').count()} 张")
