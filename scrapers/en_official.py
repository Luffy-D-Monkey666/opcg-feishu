"""
英文官网爬虫 - 基于日文爬虫修改
"""
import re
import time
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from playwright.sync_api import sync_playwright
from loguru import logger
from pathlib import Path


@dataclass
class CardDataEN:
    """英文卡片数据"""
    card_number: str
    name: str
    card_type: str
    rarity: str
    colors: str
    cost: Optional[int] = None
    life: Optional[int] = None
    power: Optional[int] = None
    counter: Optional[int] = None
    attribute: Optional[str] = None
    traits: Optional[str] = None
    effect_text: Optional[str] = None
    trigger_text: Optional[str] = None
    source_info: Optional[str] = None
    block_icon: Optional[int] = None
    image_url: Optional[str] = None
    version_index: int = 0


class EnglishOfficialScraper:
    """英文官网爬虫"""
    
    BASE_URL = "https://en.onepiece-cardgame.com"
    CARD_LIST_URL = f"{BASE_URL}/cardlist/"
    
    # 动态计算项目根目录
    _PROJECT_ROOT = Path(__file__).parent.parent
    IMAGE_DIR = _PROJECT_ROOT / "data" / "images" / "en"
    
    SERIES_TYPE_KEYWORDS = {
        'PREMIUM BOOSTER': 'premium',
        'EXTRA BOOSTER': 'extra',
        'BOOSTER PACK': 'booster',
        'STARTER DECK': 'starter',
        'ULTIMATE DECK': 'ultimate',
        'PROMOTION': 'promo',
    }
    
    # 颜色映射 (英文 -> 日文存储)
    COLOR_MAP = {
        'Red': '赤',
        'Green': '緑',
        'Blue': '青',
        'Purple': '紫',
        'Yellow': '黄',
        'Black': '黒'
    }
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    def start_browser(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = self.browser.new_page()
        self.page.set_viewport_size({"width": 1920, "height": 1080})
        logger.info("浏览器已启动 (EN)")
    
    def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("浏览器已关闭 (EN)")
    
    def get_series_list(self) -> List[Dict]:
        """获取所有系列列表"""
        logger.info("获取英文系列列表...")
        
        self.page.goto(self.CARD_LIST_URL, wait_until='networkidle')
        time.sleep(2)
        
        options = self.page.locator('select.selectModal option').all()
        
        series_list = []
        for option in options:
            value = option.get_attribute('value')
            text = option.inner_text().strip()
            
            if not value or text in ['Card Set', 'ALL', '']:
                continue
            
            clean_text = re.sub(r'<[^>]+>', ' ', text).strip()
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            # 提取系列代码
            code_match = re.search(r'\[([A-Z]+-?\d+(?:-[A-Z]+\d+)?)\]', clean_text)
            if not code_match:
                continue
            
            code = code_match.group(1)
            # 处理组合代码如 OP14-EB04，取第一个
            if '-' in code and not code.startswith(('OP', 'ST', 'EB', 'PRB')):
                code = code.split('-')[0]
            
            series_type = 'other'
            for keyword, stype in self.SERIES_TYPE_KEYWORDS.items():
                if keyword in clean_text.upper():
                    series_type = stype
                    break
            
            series_list.append({
                'code': code,
                'name': clean_text,
                'official_series_id': value,
                'series_type': series_type
            })
        
        logger.info(f"共找到 {len(series_list)} 个英文系列")
        return series_list
    
    def scrape_series(self, series_id: str, download_images: bool = False) -> List[CardDataEN]:
        """爬取指定系列的所有卡片"""
        url = f"{self.CARD_LIST_URL}?series={series_id}"
        logger.info(f"爬取英文系列: {url}")
        
        self.page.goto(url, wait_until='networkidle')
        time.sleep(2)
        
        self._close_cookie_banner()
        
        all_cards = []
        page_num = 1
        
        while True:
            logger.info(f"处理第 {page_num} 页...")
            time.sleep(1)
            
            cards_on_page = self._extract_cards_from_html()
            logger.info(f"当前页找到 {len(cards_on_page)} 张卡片")
            
            if cards_on_page:
                all_cards.extend(cards_on_page)
            
            # 检查下一页
            next_link = self.page.locator('a:has-text("NEXT")').first
            if not next_link.is_visible():
                break
            
            try:
                next_link.click()
                time.sleep(1.5)
                page_num += 1
            except:
                break
        
        # 处理版本号
        seen_cards = {}
        for card in all_cards:
            card_num = card.card_number
            if card_num in seen_cards:
                seen_cards[card_num] += 1
                card.version_index = seen_cards[card_num]
            else:
                seen_cards[card_num] = 0
        
        logger.info(f"英文系列爬取完成，共 {len(all_cards)} 张卡片")
        return all_cards
    
    def _close_cookie_banner(self):
        """关闭 Cookie 弹窗"""
        try:
            btn = self.page.locator('button:has-text("Accept All")').first
            if btn.is_visible(timeout=2000):
                btn.click()
                time.sleep(0.5)
        except:
            pass
    
    def _extract_cards_from_html(self) -> List[CardDataEN]:
        """从HTML提取卡片数据"""
        cards = []
        
        card_data_list = self.page.evaluate('''
            () => {
                const results = [];
                const modals = document.querySelectorAll('.resultCol .modalCol');
                
                modals.forEach(modal => {
                    try {
                        const infoCol = modal.querySelector('.infoCol');
                        if (!infoCol) return;
                        
                        const spans = infoCol.querySelectorAll('span');
                        const cardNumber = spans[0]?.textContent?.trim() || '';
                        const rarity = spans[1]?.textContent?.trim() || '';
                        const cardType = spans[2]?.textContent?.trim() || '';
                        
                        const name = modal.querySelector('.cardName')?.textContent?.trim() || '';
                        
                        const img = modal.querySelector('.frontCol img');
                        let imageUrl = img?.getAttribute('data-src') || img?.getAttribute('src') || '';
                        if (imageUrl && !imageUrl.startsWith('http')) {
                            imageUrl = 'https://en.onepiece-cardgame.com' + imageUrl.replace('..', '');
                        }
                        
                        const getText = (selector) => {
                            const el = modal.querySelector(selector);
                            if (!el) return null;
                            const text = el.textContent.replace(el.querySelector('h3')?.textContent || '', '').trim();
                            return text === '-' ? null : text;
                        };
                        
                        const cost = getText('.cost');
                        const power = getText('.power');
                        const counter = getText('.counter');
                        const color = getText('.color');
                        const block = getText('.block');
                        const feature = getText('.feature');
                        const effect = getText('.text');
                        const trigger = getText('.trigger');
                        const getInfo = getText('.getInfo');
                        
                        const attrImg = modal.querySelector('.attribute img');
                        const attribute = attrImg?.getAttribute('alt') || null;
                        
                        results.push({
                            cardNumber,
                            name,
                            cardType,
                            rarity,
                            imageUrl,
                            cost,
                            power,
                            counter,
                            color,
                            block,
                            attribute,
                            feature,
                            effect,
                            trigger,
                            getInfo
                        });
                    } catch (e) {
                        console.error('Error:', e);
                    }
                });
                
                return results;
            }
        ''')
        
        for data in card_data_list:
            try:
                # 转换颜色
                color_en = data.get('color') or ''
                colors_jp = []
                for en, jp in self.COLOR_MAP.items():
                    if en in color_en:
                        colors_jp.append(jp)
                colors = '/'.join(colors_jp) if colors_jp else color_en
                
                card = CardDataEN(
                    card_number=data['cardNumber'],
                    name=data['name'],
                    card_type=data['cardType'],
                    rarity=data['rarity'],
                    colors=colors,
                    cost=self._parse_int(data.get('cost')),
                    life=self._parse_int(data.get('cost')) if data['cardType'] == 'LEADER' else None,
                    power=self._parse_int(data.get('power')),
                    counter=self._parse_int(data.get('counter')),
                    attribute=data.get('attribute'),
                    traits=data.get('feature'),
                    effect_text=data.get('effect'),
                    trigger_text=data.get('trigger'),
                    source_info=data.get('getInfo'),
                    block_icon=self._parse_int(data.get('block')),
                    image_url=data.get('imageUrl')
                )
                cards.append(card)
            except Exception as e:
                logger.error(f"解析英文卡片失败: {e}")
                continue
        
        return cards
    
    def _parse_int(self, value) -> Optional[int]:
        if not value or value == '-':
            return None
        try:
            clean = re.sub(r'[^\d]', '', str(value))
            return int(clean) if clean else None
        except:
            return None


def test_scraper():
    """测试英文爬虫"""
    scraper = EnglishOfficialScraper()
    
    try:
        scraper.start_browser()
        
        print("\n=== 获取英文系列列表 ===")
        series_list = scraper.get_series_list()
        print(f"找到 {len(series_list)} 个系列\n")
        
        for s in series_list[:10]:
            print(f"  {s['code']:15} | {s['official_series_id']:10} | {s['series_type']:10} | {s['name'][:40]}")
        
        if series_list:
            print("\n=== 测试爬取第一个系列 ===")
            first = series_list[0]
            cards = scraper.scrape_series(first['official_series_id'])
            
            print(f"\n共 {len(cards)} 张卡片:")
            for card in cards[:5]:
                print(f"  {card.card_number:12} | {card.rarity:3} | {card.name[:25]}")
        
    finally:
        scraper.close_browser()


if __name__ == '__main__':
    test_scraper()
