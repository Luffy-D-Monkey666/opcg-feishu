#!/usr/bin/env python
"""
价格数据更新脚本

用法:
    # 更新所有卡片价格 (很慢，约1小时)
    python scripts/update_prices.py --all
    
    # 只更新指定系列
    python scripts/update_prices.py --series OP-14
    
    # 测试模式 (只更新10张)
    python scripts/update_prices.py --test
"""
import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from scrapers.price_scraper import update_prices_in_db
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description='Update price data from OPTCG API')
    parser.add_argument('--all', action='store_true', help='Update all cards')
    parser.add_argument('--series', type=str, help='Update specific series (e.g., OP-14)')
    parser.add_argument('--test', action='store_true', help='Test mode (only 10 cards)')
    parser.add_argument('--limit', type=int, help='Limit number of cards to update')
    
    args = parser.parse_args()
    
    app = create_app()
    
    if args.test:
        logger.info("Running in test mode (10 cards)")
        update_prices_in_db(app, limit=10)
    elif args.series:
        logger.info(f"Updating prices for series: {args.series}")
        update_prices_in_db(app, series_code=args.series)
    elif args.all:
        logger.info("Updating all card prices (this may take a while)")
        update_prices_in_db(app, limit=args.limit)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
