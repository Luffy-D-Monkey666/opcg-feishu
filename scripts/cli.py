#!/usr/bin/env python3
"""
OPCG TCG 统一 CLI 工具

用法:
    python cli.py scrape --all --lang jp      # 爬取所有日文系列
    python cli.py scrape --series OP-15       # 爬取指定系列
    python cli.py scrape --check-new          # 检查新系列
    python cli.py prices --update             # 更新价格
    python cli.py sync --to-pg                # 同步到 PostgreSQL
    python cli.py verify                      # 验证数据
"""
import sys
import os
import argparse

# 设置路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)


def cmd_scrape(args):
    """爬取卡片数据"""
    from scrape_all import scrape_all_series, scrape_single_series, check_new_series
    
    if args.series:
        scrape_single_series(args.series, lang=args.lang, download_images=args.images)
    elif args.check_new:
        check_new_series(lang=args.lang)
    elif args.all:
        scrape_all_series(lang=args.lang, download_images=args.images)
    else:
        print("请指定 --all, --series <code>, 或 --check-new")


def cmd_prices(args):
    """更新价格数据"""
    from update_prices import update_all_prices
    update_all_prices()


def cmd_sync(args):
    """同步数据"""
    if args.to_pg:
        from sync_to_pg import sync_to_postgres
        sync_to_postgres()
    else:
        print("请指定 --to-pg")


def cmd_verify(args):
    """验证数据"""
    from verify_data import verify_all
    verify_all()


def main():
    parser = argparse.ArgumentParser(
        description='OPCG TCG 管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # scrape 子命令
    scrape_parser = subparsers.add_parser('scrape', help='爬取卡片数据')
    scrape_parser.add_argument('--all', action='store_true', help='爬取所有系列')
    scrape_parser.add_argument('--series', type=str, help='指定系列代码')
    scrape_parser.add_argument('--check-new', action='store_true', help='检查新系列')
    scrape_parser.add_argument('--lang', type=str, default='jp', choices=['jp', 'en'])
    scrape_parser.add_argument('--images', action='store_true', help='下载图片')
    scrape_parser.set_defaults(func=cmd_scrape)
    
    # prices 子命令
    prices_parser = subparsers.add_parser('prices', help='价格管理')
    prices_parser.add_argument('--update', action='store_true', help='更新价格')
    prices_parser.set_defaults(func=cmd_prices)
    
    # sync 子命令
    sync_parser = subparsers.add_parser('sync', help='数据同步')
    sync_parser.add_argument('--to-pg', action='store_true', help='同步到 PostgreSQL')
    sync_parser.set_defaults(func=cmd_sync)
    
    # verify 子命令
    verify_parser = subparsers.add_parser('verify', help='验证数据')
    verify_parser.set_defaults(func=cmd_verify)
    
    args = parser.parse_args()
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
