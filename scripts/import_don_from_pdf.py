#!/usr/bin/env python3
"""
从官方 DON 卡 PDF 导入数据
- 日文: https://www.onepiece-cardgame.com/pdf/don-cardlist.pdf
- 英文: https://asia-en.onepiece-cardgame.com/pdf/don-cardlist.pdf

PDF 提供了官方的 DON 卡图片，但没有卡片编号。
本脚本基于 PDF 页面顺序和来源信息来组织数据。
"""
import sys
import os
import json
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage

# PDF 来源信息映射
# 基于 PDF 页面顺序，手动整理的来源信息
# 格式: (起始ID, 结束ID, 来源描述)
JP_SOURCES = [
    # 第1页
    (1, 1, "背景图"),  # 跳过
    (2, 4, "通常デザイン"),
    (5, 10, "イベント配布 / スタンダードバトルパックVol.1 / ストレージボックス"),
    # 第2页
    (11, 11, "背景图"),  # 跳过
    (12, 15, "ストレージボックス×ドン!!カードセット"),
    (16, 17, "イベント配布"),
    (18, 18, "アルティメットデッキ【ST-10】"),
    (19, 19, "アルティメットデッキ【ST-13】"),
    (20, 20, "イベント配布"),
    # 第3页 - ブースターパック DON
    (21, 21, "背景图"),  # 跳过
    (22, 22, "ブースターパック【OP-01】"),
    (23, 23, "ブースターパック【OP-02】"),
    (24, 24, "ブースターパック【OP-03】"),
    (25, 25, "ブースターパック【OP-04】"),
    (26, 26, "ブースターパック【OP-05】"),
    (27, 27, "ブースターパック【OP-06】"),
    (28, 28, "ブースターパック【OP-07】"),
    (29, 29, "ブースターパック【OP-08】"),
    (30, 30, "オフィシャルカードケース"),
    # 第4-14页 - PRB-01 (90张: 30角色 x 3版本)
    # ... PRB-01 数据需要更详细的映射
]


def get_or_create_don_series(language='jp'):
    """获取或创建 DON 卡系列"""
    series = Series.query.filter_by(code='DON', language=language).first()
    if not series:
        series = Series(
            code='DON',
            name='ドン!!カード' if language == 'jp' else 'DON!! Card',
            series_type='don',
            language=language
        )
        db.session.add(series)
        db.session.commit()
        logger.info(f"创建 {language.upper()} DON 卡系列")
    return series


def import_don_images(language='jp'):
    """
    从提取的图片文件导入 DON 卡数据
    
    由于 PDF 没有卡片编号，我们使用以下命名规则:
    - DON-{序号:03d} 作为卡片编号 (如 DON-001, DON-002)
    - 来源信息从 PDF 文本解析
    """
    # 确定图片目录
    img_dir = f"data/don_images_{'full' if language == 'jp' else 'en'}"
    json_file = f"data/don_cards_{'extracted' if language == 'jp' else 'en_extracted'}.json"
    
    if not os.path.exists(json_file):
        logger.error(f"找不到数据文件: {json_file}")
        logger.info("请先运行 PDF 提取脚本")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        cards_data = json.load(f)
    
    series = get_or_create_don_series(language)
    
    # 目标图片目录
    target_dir = f"app/static/images/don/{language}"
    os.makedirs(target_dir, exist_ok=True)
    
    imported = 0
    skipped = 0
    actual_index = 0  # 实际卡片索引（跳过背景图后）
    
    for card_data in cards_data:
        card_id = card_data['id']
        img_file = card_data['image_file']
        source_info = card_data.get('source_info', '官方 PDF')
        
        # 跳过背景图（通常很大，约 1.5MB）
        if card_data.get('image_size', 0) > 1000000:
            skipped += 1
            continue
        
        actual_index += 1
        
        # 生成卡片编号 (使用实际索引，不包含背景图)
        card_number = f"DON-{actual_index:03d}"
        
        # 复制图片到静态目录
        src_path = os.path.join(img_dir, img_file)
        if not os.path.exists(src_path):
            logger.warning(f"图片不存在: {src_path}")
            continue
        
        # 生成新文件名
        ext = os.path.splitext(img_file)[1]
        new_filename = f"{card_number}{ext}"
        dst_path = os.path.join(target_dir, new_filename)
        shutil.copy2(src_path, dst_path)
        
        # 创建或更新数据库记录
        card = Card.query.filter_by(card_number=card_number, language=language).first()
        if not card:
            card = Card(
                card_number=card_number,
                series_id=series.id,
                language=language,
                name='ドン!!カード' if language == 'jp' else 'DON!! Card',
                card_type='DON',
                rarity='DON',
                colors='',
                source_info=source_info
            )
            db.session.add(card)
            db.session.flush()
        
        # 创建版本
        version = CardVersion.query.filter_by(card_id=card.id, series_id=series.id).first()
        if not version:
            version = CardVersion(
                card_id=card.id,
                series_id=series.id,
                version_type='normal',
                source_description=source_info
            )
            db.session.add(version)
            db.session.flush()
        
        # 创建图片记录
        img_record = CardImage.query.filter_by(version_id=version.id).first()
        if not img_record:
            img_record = CardImage(
                version_id=version.id,
                local_path=f"/static/images/don/{language}/{new_filename}"
            )
            db.session.add(img_record)
        else:
            img_record.local_path = f"/static/images/don/{language}/{new_filename}"
        
        imported += 1
    
    db.session.commit()
    logger.info(f"{language.upper()} DON 卡导入完成: 导入 {imported} 张, 跳过 {skipped} 张背景图")


def main():
    app = create_app()
    with app.app_context():
        logger.info("开始从 PDF 导入 DON 卡数据...")
        
        # 导入日文
        import_don_images('jp')
        
        # 导入英文
        import_don_images('en')
        
        # 统计
        jp_count = Card.query.filter_by(language='jp', card_type='DON').count()
        en_count = Card.query.filter_by(language='en', card_type='DON').count()
        logger.info(f"导入完成！日文 {jp_count} 张, 英文 {en_count} 张")


if __name__ == '__main__':
    main()
