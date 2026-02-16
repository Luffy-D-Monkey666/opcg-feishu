#!/usr/bin/env python
"""
数据校验脚本 - 对比数据库和官网卡片数量
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion, CardImage

# 官网数据 (手动收集)
# 格式: {系列代码: 官网显示的卡片数}
OFFICIAL_CARD_COUNTS = {
    # Booster Packs
    'OP-01': 121,  # ROMANCE DAWN
    'OP-02': 121,  # 頂上決戦
    'OP-03': 122,  # 強大な敵
    'OP-04': 121,  # 謀略の王国
    'OP-05': 120,  # 新時代の主役
    'OP-06': 129,  # 双璧の覇者
    'OP-07': 142,  # 500年後の未来
    'OP-08': 142,  # 二つの伝説
    'OP-09': 137,  # 新たなる皇帝
    'OP-10': 144,  # 王族の血統
    'OP-11': 144,  # 神速の拳
    'OP-12': 144,  # 師弟の絆
    'OP-13': 144,  # 受け継がれる意志
    'OP-14': 156,  # 蒼海の七傑
    
    # Extra Boosters
    'EB-01': 88,   # メモリアルコレクション
    'EB-02': 173,  # Anime 25th collection
    'EB-03': 124,  # ONE PIECE Heroines Edition
    'EB-04': 96,   # EGGHEAD CRISIS
    
    # Premium Boosters
    'PRB-01': 216, # ONE PIECE CARD THE BEST
    'PRB-02': 347, # ONE PIECE CARD THE BEST vol.2
    
    # Starter Decks
    'ST-01': 17,   # 麦わらの一味
    'ST-02': 17,   # 最悪の世代
    'ST-03': 17,   # 王下七武海
    'ST-04': 17,   # 百獣海賊団
    'ST-05': 17,   # ONE PIECE FILM edition
    'ST-06': 17,   # 海軍
    'ST-07': 17,   # ビッグ・マム海賊団
    'ST-08': 17,   # Side モンキー・D・ルフィ
    'ST-09': 17,   # Side ヤマト
    'ST-10': 17,   # アルティメットデッキ "三船長"集結
    'ST-11': 17,   # Side ウタ
    'ST-12': 17,   # ゾロ&サンジ
    'ST-13': 17,   # アルティメットデッキ 3兄弟の絆
    'ST-14': 17,   # 3D2Y
    'ST-15': 17,   # 赤 エドワード・ニューゲート
    'ST-16': 17,   # 緑 ウタ
    'ST-17': 17,   # 青 ドンキホーテ・ドフラミンゴ
    'ST-18': 17,   # 紫 モンキー・D・ルフィ
    'ST-19': 17,   # 黒 スモーカー
    'ST-20': 17,   # 黄 シャーロット・カタクリ
    'ST-21': 26,   # スタートデッキEX ギア5
    'ST-22': 17,   # エース&ニューゲート
    'ST-23': 17,   # 赤 シャンクス
    'ST-24': 17,   # 緑 ジュエリー・ボニー
    'ST-25': 17,   # 青 バギー
    'ST-26': 17,   # 紫黒 モンキー・D・ルフィ
    'ST-27': 17,   # 黒 マーシャル・D・ティーチ
    'ST-28': 17,   # 緑黄 ヤマト
    'ST-29': 17,   # EGGHEAD
}


def main():
    app = create_app()
    
    with app.app_context():
        print('=' * 60)
        print('数据库与官网卡片数量对比')
        print('=' * 60)
        
        total_db = 0
        total_official = 0
        issues = []
        
        for series_code, official_count in sorted(OFFICIAL_CARD_COUNTS.items()):
            series = Series.query.filter_by(code=series_code, language='jp').first()
            
            if not series:
                issues.append(f'❌ {series_code}: 数据库中不存在此系列')
                total_official += official_count
                continue
            
            # 只统计日文卡片
            db_card_count = Card.query.filter_by(series_id=series.id, language='jp').count()
            db_version_count = CardVersion.query.join(Card).filter(Card.series_id == series.id, Card.language == 'jp').count()
            
            total_db += db_card_count
            total_official += official_count
            
            status = '✅' if db_card_count >= official_count * 0.8 else '⚠️'  # 80%以上认为OK (有些是版本合并)
            if db_card_count < official_count * 0.5:
                status = '❌'
            
            diff = db_card_count - official_count
            diff_str = f'+{diff}' if diff > 0 else str(diff)
            
            print(f'{status} {series_code}: DB={db_card_count} 官网={official_count} ({diff_str}) [版本数:{db_version_count}]')
            
            if status in ['⚠️', '❌']:
                issues.append(f'{series_code}: 数据库{db_card_count}张, 官网{official_count}张')
        
        print('\n' + '=' * 60)
        print(f'总计: 数据库 {total_db} 张, 官网 {total_official} 张')
        print('=' * 60)
        
        if issues:
            print('\n⚠️ 发现的问题:')
            for issue in issues:
                print(f'  - {issue}')
        
        # 检查是否有未在官方列表中的系列
        print('\n=== 额外检查 ===')
        all_db_series = Series.query.filter_by(language='jp').all()
        for s in all_db_series:
            if s.code not in OFFICIAL_CARD_COUNTS:
                card_count = Card.query.filter_by(series_id=s.id).count()
                print(f'📌 {s.code}: {card_count}张 (未在校验列表中) - {s.name[:30]}')
        
        # 检查图片完整性
        print('\n=== 图片完整性 ===')
        cards_without_images = db.session.query(Card).join(CardVersion).outerjoin(CardImage).filter(
            CardImage.id == None
        ).count()
        
        total_cards = Card.query.filter_by(language='jp').count()
        print(f'缺少图片的卡片: {cards_without_images}/{total_cards}')


if __name__ == '__main__':
    main()
