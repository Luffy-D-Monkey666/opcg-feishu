#!/usr/bin/env python3
"""
导入 DON 卡数据
数据来源: tier-one-onepiece.jp
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import requests
from bs4 import BeautifulSoup
from loguru import logger
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage

# DON 卡角色名映射 (PRB01)
PRB01_DON_NAMES = {
    '001': 'アイスバーグ',
    '002': 'ヴィンスモーク・レイジュ',
    '003': 'ウタ',
    '004': 'エドワード・ニューゲート',
    '005': 'エネル',
    '006': 'エンポリオ・イワンコフ',
    '007': 'カイドウ',
    '008': 'キング',
    '009': 'クイーン',
    '010': 'クロコダイル',
    '011': 'ゲッコー・モリア',
    '012': '光月おでん',
    '013': 'サカズキ',
    '014': 'サボ',
    '015': 'シャーロット・カタクリ',
    '016': 'シャーロット・リンリン',
    '017': 'トラファルガー・ロー',
    '018': 'ドンキホーテ・ドフラミンゴ',
    '019': 'ドンキホーテ・ロシナンテ',
    '020': 'ネフェルタリ・ビビ',
    '021': 'ペローナ',
    '022': 'ホーディ・ジョーンズ',
    '023': 'ポートガス・D・エース',
    '024': 'マゼラン',
    '025': 'モンキー・D・ルフィ',
    '026': 'ヤマト',
    '027': 'ユースタス・キッド',
    '028': 'レベッカ',
    '029': 'ロブ・ルッチ',
    '030': 'ロロノア・ゾロ',
}

# DON 卡角色名映射 (PRB02)
PRB02_DON_NAMES = {
    '001': 'ウソップ',
    '002': 'カルガラ',
    '003': 'キャロット',
    '004': 'キュロス',
    '005': 'コビー',
    '006': 'サンジ',
    '007': 'シーザー',
    '008': 'シャーロット・プリン',
    '009': 'シャンクス',
    '010': 'ジュエリー・ボニー',
    '011': 'シュガー',
    '012': 'しらほし',
    '013': 'ジンベエ',
    '014': 'スモーカー',
    '015': 'トニートニー・チョッパー',
    '016': 'ナミ',
    '017': 'ニコ・ロビン',
    '018': 'バギー',
    '019': 'ハンニャバル',
    '020': 'フォクシー',
    '021': 'ベガパンク',
    '022': 'ボア・ハンコック',
    '023': 'マーシャル・D・ティーチ',
    '024': 'マルコ',
    '025': '革命軍',
    '026': 'スネイクマン',
    '027': 'ニカルフィ',
    '028': 'ヤマト',
    '029': 'ODYSSEY',
    '030': 'ロブ・ルッチ',
}

BASE_IMAGE_URL = "https://tierone-media-op.com/wp-content/uploads/"


def get_or_create_don_series():
    """获取或创建 DON 卡系列"""
    series = Series.query.filter_by(code='DON', language='jp').first()
    if not series:
        series = Series(
            code='DON',
            name='ドン!!カード',
            series_type='don',
            language='jp'
        )
        db.session.add(series)
        db.session.commit()
        logger.info("创建 DON 卡系列")
    return series


def import_don_card(card_number, name, source_info, image_urls, series):
    """导入单张 DON 卡"""
    # 查找或创建卡片
    card = Card.query.filter_by(card_number=card_number, language='jp').first()
    
    if not card:
        card = Card(
            card_number=card_number,
            series_id=series.id,
            language='jp',
            name=name,
            card_type='DON',
            rarity='DON',
            colors='',
            source_info=source_info
        )
        db.session.add(card)
        db.session.flush()
        logger.info(f"新增 DON 卡: {card_number} - {name}")
    
    # 创建版本
    for version_type, image_url in image_urls.items():
        version_suffix = ''
        if version_type == 'parallel':
            version_suffix = '_p'
        elif version_type == 'super_parallel':
            version_suffix = '_sp'
        
        existing_version = CardVersion.query.filter_by(
            card_id=card.id,
            series_id=series.id,
            version_suffix=version_suffix
        ).first()
        
        if not existing_version:
            version = CardVersion(
                card_id=card.id,
                series_id=series.id,
                version_type='normal' if version_type == 'normal' else 'alt_art',
                version_suffix=version_suffix,
                source_description=source_info
            )
            db.session.add(version)
            db.session.flush()
            
            # 添加图片
            img = CardImage(
                version_id=version.id,
                original_url=image_url
            )
            db.session.add(img)
            logger.info(f"  添加版本: {version_type}")
    
    db.session.commit()


def import_prb_don_cards(series):
    """导入 PRB 系列 DON 卡"""
    # PRB01
    for num, name in PRB01_DON_NAMES.items():
        card_number = f'PRB01-DON-{num}'
        image_urls = {
            'normal': f'{BASE_IMAGE_URL}don_card_prb01-{num}.webp',
            'parallel': f'{BASE_IMAGE_URL}don_card_prb01-{num}p.webp',
            'super_parallel': f'{BASE_IMAGE_URL}don_card_prb01-{num}sp.webp',
        }
        import_don_card(
            card_number=card_number,
            name=f'ドン!!カード ({name})',
            source_info='ONE PIECE CARD THE BEST【PRB-01】',
            image_urls=image_urls,
            series=series
        )
    
    # PRB02
    for num, name in PRB02_DON_NAMES.items():
        card_number = f'PRB02-DON-{num}'
        image_urls = {
            'normal': f'{BASE_IMAGE_URL}don_card_prb02-{num}.webp',
            'parallel': f'{BASE_IMAGE_URL}don_card_prb02-{num}p.webp',
            'super_parallel': f'{BASE_IMAGE_URL}don_card_prb02-{num}sp.webp',
        }
        import_don_card(
            card_number=card_number,
            name=f'ドン!!カード ({name})',
            source_info='ONE PIECE CARD THE BEST Vol.2【PRB-02】',
            image_urls=image_urls,
            series=series
        )


def import_booster_don_cards(series):
    """导入补充包 DON 卡"""
    # OP01-OP14
    for i in range(1, 15):
        num = str(i).zfill(2)
        card_number = f'OP{num}-DON'
        image_urls = {
            'normal': f'{BASE_IMAGE_URL}op{num}-doncard.webp',
        }
        import_don_card(
            card_number=card_number,
            name='ドン!!カード',
            source_info=f'ブースターパック【OP-{num}】',
            image_urls=image_urls,
            series=series
        )


def import_extra_don_cards(series):
    """导入 EB 系列 DON 卡"""
    # EB02, EB03 有 DON 卡
    for i in [2, 3]:
        num = str(i).zfill(2)
        card_number = f'EB{num}-DON'
        image_urls = {
            'normal': f'{BASE_IMAGE_URL}eb{num}-doncard.webp',
        }
        import_don_card(
            card_number=card_number,
            name='ドン!!カード',
            source_info=f'エクストラブースター【EB-{num}】',
            image_urls=image_urls,
            series=series
        )


def import_basic_don_cards(series):
    """导入基础 DON 卡"""
    # 通常版
    import_don_card(
        card_number='DON-NORMAL',
        name='ドン!!カード (通常)',
        source_info='スタートデッキ/ブースターパック',
        image_urls={'normal': f'{BASE_IMAGE_URL}don-normal.webp'},
        series=series
    )
    
    # Foil版
    import_don_card(
        card_number='DON-FOIL',
        name='ドン!!カード (フォイル)',
        source_info='アルティメットデッキ',
        image_urls={'normal': f'{BASE_IMAGE_URL}don-foil.webp'},
        series=series
    )


def main():
    app = create_app()
    with app.app_context():
        logger.info("开始导入 DON 卡数据...")
        
        # 创建 DON 系列
        series = get_or_create_don_series()
        
        # 导入各类 DON 卡
        import_basic_don_cards(series)
        import_booster_don_cards(series)
        import_extra_don_cards(series)
        import_prb_don_cards(series)
        
        # 统计
        don_count = Card.query.filter_by(card_type='DON').count()
        logger.info(f"导入完成！共 {don_count} 张 DON 卡")


if __name__ == '__main__':
    main()
