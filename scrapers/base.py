"""
爬虫基类 - 通用逻辑
"""
import os
import time
import hashlib
import requests
from pathlib import Path
from loguru import logger

# 配置日志
logger.add("logs/scraper_{time}.log", rotation="10 MB", retention="7 days")


class BaseScraper:
    """爬虫基类"""
    
    def __init__(self, language='jp'):
        self.language = language
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 图片保存路径
        self.image_base_path = Path(__file__).parent.parent / 'app' / 'static' / 'images' / 'cards' / language
        self.image_base_path.mkdir(parents=True, exist_ok=True)
    
    def download_image(self, url: str, card_number: str, version_suffix: str = '') -> str:
        """
        下载图片并返回本地路径
        
        Args:
            url: 图片URL
            card_number: 卡片编号
            version_suffix: 版本后缀 (如 _alt, _comic)
        
        Returns:
            本地相对路径
        """
        try:
            # 生成文件名
            ext = url.split('.')[-1].split('?')[0]
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                ext = 'jpg'
            
            filename = f"{card_number}{version_suffix}.{ext}"
            local_path = self.image_base_path / filename
            
            # 如果已存在则跳过
            if local_path.exists():
                logger.debug(f"图片已存在: {filename}")
                return f"{self.language}/{filename}"
            
            # 下载
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"下载图片: {filename}")
            time.sleep(0.5)  # 礼貌延迟
            
            return f"{self.language}/{filename}"
            
        except Exception as e:
            logger.error(f"下载图片失败 {url}: {e}")
            return None
    
    def generate_version_suffix(self, existing_count: int) -> str:
        """根据已存在的版本数量生成后缀"""
        if existing_count == 0:
            return ''
        return f"_v{existing_count + 1}"
