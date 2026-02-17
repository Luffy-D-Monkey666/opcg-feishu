#!/usr/bin/env python3
"""
导入英文版 DON 卡数据
基于日文版 DON 卡创建英文版对应记录
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage

# PRB01 DON 卡英文名
PRB01_DON_NAMES_EN = {
    '001': 'Iceburg',
    '002': 'Vinsmoke Reiju',
    '003': 'Uta',
    '004': 'Edward Newgate',
    '005': 'Enel',
    '006': 'Emporio Ivankov',
    '007': 'Kaido',
    '008': 'King',
    '009': 'Queen',
    '010': 'Crocodile',
    '011': 'Gecko Moria',
    '012': 'Kozuki Oden',
    '013': 'Sakazuki',
    '014': 'Sabo',
    '015': 'Charlotte Katakuri',
    '016': 'Charlotte Linlin',
    '017': 'Trafalgar Law',
    '018': 'Donquixote Doflamingo',
    '019': 'Donquixote Rosinante',
    '020': 'Nefeltari Vivi',
    '021': 'Perona',
    '022': 'Hody Jones',
    '023': 'Portgas D. Ace',
    '024': 'Magellan',
    '025': 'Monkey D. Luffy',
    '026': 'Yamato',
    '027': 'Eustass Kid',
    '028': 'Rebecca',
    '029': 'Rob Lucci',
    '030': 'Roronoa Zoro',
}

# PRB02 DON 卡英文名
PRB02_DON_NAMES_EN = {
    '001': 'Usopp',
    '002': 'Kalgara',
    '003': 'Carrot',
    '004': 'Kyros',
    '005': 'Koby',
    '006': 'Sanji',
    '007': 'Caesar',
    '008': 'Charlotte Pudding',
    '009': 'Shanks',
    '010': 'Jewelry Bonney',
    '011': 'Sugar',
    '012': 'Shirahoshi',
    '013': 'Jinbe',
    '014': 'Smoker',
    '015': 'Tony Tony Chopper',
    '016': 'Nami',
    '017': 'Nico Robin',
    '018': 'Buggy',
    '019': 'Hannyabal',
    '020': 'Foxy',
    '021': 'Vegapunk',
    '022': 'Boa Hancock',
    '023': 'Marshall D. Teach',
    '024': 'Marco',
    '025': 'Revolutionary Army',
    '026': 'Snakeman',
    '027': 'Nika Luffy',
    '028': 'Yamato',
    '029': 'ODYSSEY',
    '030': 'Rob Lucci',
}

BASE_IMAGE_URL = "https://tierone-media-op.com/wp-content/uploads/"


def get_or_create_don_series_en():
    """获取或创建英文 DON 卡系列"""
    series = Series.query.filter_by(code='DON', language='en').first()
    if not series:
        series = Series(
            code='DON',
            name='DON!! Card',
            series_type='don',
            language='en'
        )
        db.session.add(series)
        db.session.commit()
        logger.info("创建英文 DON 卡系列")
    return series


def import_don_card_en(card_number, name, source_info, image_urls, series):
    """导入单张英文 DON 卡"""
    # 查找或创建卡片
    card = Card.query.filter_by(card_number=card_number, language='en').first()
    
    if not card:
        card = Card(
            card_number=card_number,
            series_id=series.id,
            language='en',
            name=name,
            card_type='DON',
            rarity='DON',
            colors='',
            source_info=source_info
        )
        db.session.add(card)
        db.session.flush()
        logger.info(f"新增英文 DON 卡: {card_number} - {name}")
    
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
            
            # 添加图片 (使用与日文版相同的图片URL)
            img = CardImage(
                version_id=version.id,
                original_url=image_url
            )
            db.session.add(img)
            logger.info(f"  添加版本: {version_type}")
    
    db.session.commit()


def import_prb_don_cards_en(series):
    """导入 PRB 系列英文 DON 卡"""
    # PRB01
    for num, name in PRB01_DON_NAMES_EN.items():
        card_number = f'PRB01-DON-{num}'
        image_urls = {
            'normal': f'{BASE_IMAGE_URL}don_card_prb01-{num}.webp',
            'parallel': f'{BASE_IMAGE_URL}don_card_prb01-{num}p.webp',
            'super_parallel': f'{BASE_IMAGE_URL}don_card_prb01-{num}sp.webp',
        }
        import_don_card_en(
            card_number=card_number,
            name=f'DON!! Card ({name})',
            source_info='ONE PIECE CARD THE BEST [PRB-01]',
            image_urls=image_urls,
            series=series
        )
    
    # PRB02
    for num, name in PRB02_DON_NAMES_EN.items():
        card_number = f'PRB02-DON-{num}'
        image_urls = {
            'normal': f'{BASE_IMAGE_URL}don_card_prb02-{num}.webp',
            'parallel': f'{BASE_IMAGE_URL}don_card_prb02-{num}p.webp',
            'super_parallel': f'{BASE_IMAGE_URL}don_card_prb02-{num}sp.webp',
        }
        import_don_card_en(
            card_number=card_number,
            name=f'DON!! Card ({name})',
            source_info='ONE PIECE CARD THE BEST Vol.2 [PRB-02]',
            image_urls=image_urls,
            series=series
        )


def import_booster_don_cards_en(series):
    """导入补充包英文 DON 卡"""
    # OP01-OP14
    for i in range(1, 15):
        num = str(i).zfill(2)
        card_number = f'OP{num}-DON'
        image_urls = {
            'normal': f'{BASE_IMAGE_URL}op{num}-doncard.webp',
        }
        import_don_card_en(
            card_number=card_number,
            name='DON!! Card',
            source_info=f'BOOSTER PACK [OP-{num}]',
            image_urls=image_urls,
            series=series
        )


def import_extra_don_cards_en(series):
    """导入 EB 系列英文 DON 卡"""
    # EB02, EB03 有 DON 卡
    for i in [2, 3]:
        num = str(i).zfill(2)
        card_number = f'EB{num}-DON'
        image_urls = {
            'normal': f'{BASE_IMAGE_URL}eb{num}-doncard.webp',
        }
        import_don_card_en(
            card_number=card_number,
            name='DON!! Card',
            source_info=f'EXTRA BOOSTER [EB-{num}]',
            image_urls=image_urls,
            series=series
        )


def import_basic_don_cards_en(series):
    """导入基础英文 DON 卡"""
    # 通常版
    import_don_card_en(
        card_number='DON-NORMAL',
        name='DON!! Card (Normal)',
        source_info='Starter Deck / Booster Pack',
        image_urls={'normal': f'{BASE_IMAGE_URL}don-normal.webp'},
        series=series
    )
    
    # Foil版
    import_don_card_en(
        card_number='DON-FOIL',
        name='DON!! Card (Foil)',
        source_info='Ultra Deck',
        image_urls={'normal': f'{BASE_IMAGE_URL}don-foil.webp'},
        series=series
    )


def main():
    app = create_app()
    with app.app_context():
        logger.info("开始导入英文 DON 卡数据...")
        
        # 创建英文 DON 系列
        series = get_or_create_don_series_en()
        
        # 导入各类 DON 卡
        import_basic_don_cards_en(series)
        import_booster_don_cards_en(series)
        import_extra_don_cards_en(series)
        import_prb_don_cards_en(series)
        
        # 统计
        don_count = Card.query.filter_by(card_type='DON', language='en').count()
        don_versions = CardVersion.query.filter_by(series_id=series.id).count()
        logger.info(f"导入完成！共 {don_count} 张英文 DON 卡, {don_versions} 个版本")


if __name__ == '__main__':
    main()
