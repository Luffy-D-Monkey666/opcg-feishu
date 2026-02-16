#!/usr/bin/env python3
"""
校核脚本：验证数据库中的卡片版本数与官网显示的卡片数是否一致

官网每个系列的卡片数 = 所有卡片（含异画版、平行卡等）
数据库中的 CardVersion 数量应该与之匹配

用法:
    python scripts/verify_card_counts.py [--fix]
"""
import sys
import time
import re
import argparse
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
from loguru import logger
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion


def get_official_counts_from_browser():
    """
    从官网获取每个系列的卡片数
    返回: {official_series_id: count}
    """
    counts = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = browser.new_page()
        page.set_default_timeout(30000)
        
        logger.info("访问官网卡片列表...")
        page.goto('https://www.onepiece-cardgame.com/cardlist/', wait_until='domcontentloaded')
        time.sleep(3)
        
        # 获取所有系列选项
        options = page.evaluate('''
            () => {
                const select = document.querySelector('select.selectModal');
                if (!select) return [];
                return Array.from(select.options).map(opt => ({
                    value: opt.value,
                    text: opt.textContent.trim()
                })).filter(o => o.value && !['', 'ALL'].includes(o.text.substring(0, 3)));
            }
        ''')
        
        logger.info(f"找到 {len(options)} 个系列")
        
        for i, opt in enumerate(options):
            series_id = opt['value']
            series_name = opt['text']
            
            if not series_id:
                continue
            
            try:
                url = f"https://www.onepiece-cardgame.com/cardlist/?series={series_id}"
                page.goto(url, wait_until='domcontentloaded')
                time.sleep(1.5)
                
                # 等待结果加载
                try:
                    page.wait_for_selector('.resultCol', timeout=5000)
                except:
                    pass
                
                # 从"XXX件HIT"提取数量
                hit_text = page.evaluate('''
                    () => {
                        const el = document.querySelector('.resultCol .resultHead span, .searchResult .count, [class*="hit"]');
                        if (el) return el.textContent;
                        // 尝试从页面文本中匹配
                        const match = document.body.textContent.match(/(\\d+)件HIT/);
                        return match ? match[0] : null;
                    }
                ''')
                
                if hit_text:
                    match = re.search(r'(\d+)', hit_text)
                    if match:
                        count = int(match.group(1))
                        counts[series_id] = count
                        
                        # 提取系列代码
                        code_match = re.search(r'【([A-Z]+-?\d+)】', series_name)
                        code = code_match.group(1) if code_match else series_id
                        
                        logger.info(f"[{i+1}/{len(options)}] {code}: {count} 张")
                else:
                    logger.warning(f"[{i+1}/{len(options)}] {series_name[:30]}: 无法获取数量")
                
            except Exception as e:
                logger.error(f"[{i+1}/{len(options)}] 错误: {series_name[:30]} - {e}")
        
        browser.close()
    
    return counts


def compare_with_database(official_counts):
    """对比官网数据与数据库"""
    app = create_app()
    results = []
    
    with app.app_context():
        for series_id, official_count in official_counts.items():
            series = Series.query.filter_by(official_series_id=series_id, language='jp').first()
            
            if not series:
                results.append({
                    'code': f'({series_id})',
                    'official': official_count,
                    'db': 0,
                    'diff': -official_count,
                    'status': '❌ 系列不存在'
                })
                continue
            
            db_version_count = CardVersion.query.join(Card).filter(Card.series_id == series.id).count()
            diff = db_version_count - official_count
            
            if diff == 0:
                status = '✅'
            elif diff > 0:
                status = f'⚠️ 多 {diff}'
            else:
                status = f'❌ 少 {abs(diff)}'
            
            results.append({
                'code': series.code,
                'name': series.name[:30] if series.name else '',
                'official': official_count,
                'db': db_version_count,
                'diff': diff,
                'status': status
            })
    
    return results


def print_report(results):
    """打印校核报告"""
    print("\n" + "=" * 80)
    print(" 卡片数量校核报告 ".center(80, "="))
    print("=" * 80)
    print(f"{'Code':<12} {'官网':<8} {'数据库':<8} {'差异':<8} 状态")
    print("-" * 80)
    
    total_official = 0
    total_db = 0
    issues = []
    
    for r in sorted(results, key=lambda x: x['code']):
        total_official += r['official']
        total_db += r['db']
        
        print(f"{r['code']:<12} {r['official']:<8} {r['db']:<8} {r['diff']:+8} {r['status']}")
        
        if r['diff'] != 0:
            issues.append(r)
    
    print("-" * 80)
    print(f"{'总计':<12} {total_official:<8} {total_db:<8} {total_db - total_official:+8}")
    print("=" * 80)
    
    if issues:
        print(f"\n⚠️ 发现 {len(issues)} 个系列存在差异:")
        for r in issues:
            print(f"  - {r['code']}: {r['status']}")
    else:
        print("\n✅ 所有系列卡片数量一致!")
    
    return issues


def main():
    parser = argparse.ArgumentParser(description='校核卡片数量')
    parser.add_argument('--fix', action='store_true', help='自动修复缺失的卡片')
    args = parser.parse_args()
    
    logger.info("开始校核卡片数量...")
    
    # 从官网获取数量
    official_counts = get_official_counts_from_browser()
    
    if not official_counts:
        logger.error("无法从官网获取数据")
        return 1
    
    # 对比数据库
    results = compare_with_database(official_counts)
    
    # 打印报告
    issues = print_report(results)
    
    if args.fix and issues:
        logger.info("修复功能尚未实现")
        # TODO: 实现自动补爬缺失卡片的逻辑
    
    return 0 if not issues else 1


if __name__ == '__main__':
    sys.exit(main())
