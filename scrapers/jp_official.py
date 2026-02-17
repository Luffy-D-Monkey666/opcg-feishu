"""
日文官网爬虫 - 直接解析HTML中的卡片数据
"""
import re
import time
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from playwright.sync_api import sync_playwright
from loguru import logger
from pathlib import Path


@dataclass
class CardData:
    """卡片数据"""
    card_number: str
    name: str
    card_type: str  # LEADER / CHARACTER / EVENT / STAGE
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
    version_index: int = 0  # 同编号的第几个版本 (0=普通, 1+=异画等)
    illustration_type: Optional[str] = None  # 原作/アニメ/オリジナル/その他
    has_star_mark: bool = False  # 是否有星标
    modal_id: Optional[str] = None  # HTML中的modal ID，用于匹配插画类型


class JapanOfficialScraper:
    """日文官网爬虫"""
    
    BASE_URL = "https://www.onepiece-cardgame.com"
    CARD_LIST_URL = f"{BASE_URL}/cardlist/"
    IMAGE_DIR = Path("/workspace/opcg-tcg/data/images")
    
    # 系列类型关键词映射
    SERIES_TYPE_KEYWORDS = {
        'プレミアムブースター': 'premium',
        'エクストラブースター': 'extra',
        'ブースターパック': 'booster',
        'スタートデッキ': 'starter',
        'アルティメットデッキ': 'ultimate',
        'ファミリーデッキ': 'family',
        'プロモーションカード': 'promo',
        '限定商品': 'limited'
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
        logger.info("浏览器已启动")
    
    def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("浏览器已关闭")
    
    def get_series_list(self) -> List[Dict]:
        """获取所有系列列表"""
        logger.info("获取系列列表...")
        
        self.page.goto(self.CARD_LIST_URL, wait_until='networkidle')
        time.sleep(2)
        
        # 从 select 元素获取所有系列
        options = self.page.locator('select.selectModal option').all()
        
        series_list = []
        for option in options:
            value = option.get_attribute('value')
            text = option.inner_text().strip()
            
            if not value or text in ['収録', 'ALL', '']:
                continue
            
            clean_text = re.sub(r'<[^>]+>', ' ', text).strip()
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            code_match = re.search(r'【([A-Z]+-?\d+)】', clean_text)
            if not code_match:
                continue
            
            code = code_match.group(1)
            
            series_type = 'other'
            for keyword, stype in self.SERIES_TYPE_KEYWORDS.items():
                if keyword in clean_text:
                    series_type = stype
                    break
            
            series_list.append({
                'code': code,
                'name': clean_text,
                'official_series_id': value,
                'series_type': series_type
            })
        
        logger.info(f"共找到 {len(series_list)} 个系列")
        return series_list
    
    def scrape_series(self, series_id: str, download_images: bool = False, fetch_extras: bool = True) -> List[CardData]:
        """
        爬取指定系列的所有卡片 - 直接从HTML解析
        
        Args:
            series_id: 官网系列ID
            download_images: 是否下载图片
            fetch_extras: 是否获取插画类型和星标（会额外请求，较慢）
        """
        url = f"{self.CARD_LIST_URL}?series={series_id}"
        logger.info(f"爬取系列: {url}")
        
        self.page.goto(url, wait_until='networkidle')
        time.sleep(2)
        
        # 关闭 Cookie 弹窗
        self._close_cookie_banner()
        
        # 等待页面加载完成
        time.sleep(3)
        
        # 等待卡片数据加载
        try:
            self.page.wait_for_selector('.resultCol .modalCol', timeout=10000)
        except:
            logger.warning("等待卡片加载超时")
        
        # 官网会一次性将所有卡片数据加载到 DOM 中（分页只是前端展示）
        # 直接提取所有卡片数据
        all_cards = self._extract_cards_from_html()
        logger.info(f"获取 {len(all_cards)} 条卡片记录")
        
        # 处理版本号
        seen_cards = {}
        for card in all_cards:
            card_num = card.card_number
            if card_num in seen_cards:
                seen_cards[card_num] += 1
                card.version_index = seen_cards[card_num]
            else:
                seen_cards[card_num] = 0
        
        # 获取插画类型和星标
        if fetch_extras and all_cards:
            logger.info("获取插画类型和星标...")
            illustration_map = self._fetch_illustration_types(series_id)
            star_ids = self._fetch_star_marked_cards(series_id)
            
            # 应用到卡片数据
            for card in all_cards:
                if card.modal_id:
                    card.illustration_type = illustration_map.get(card.modal_id)
                    card.has_star_mark = card.modal_id in star_ids
        
        # 下载图片
        if download_images:
            for card in all_cards:
                if card.image_url:
                    self._download_image(card)
        
        logger.info(f"系列爬取完成，共 {len(all_cards)} 张卡片")
        return all_cards
    
    def _close_cookie_banner(self):
        """关闭 Cookie 弹窗"""
        try:
            ok_button = self.page.locator('button:has-text("OK")').first
            if ok_button.is_visible(timeout=2000):
                ok_button.click()
                time.sleep(0.5)
        except:
            pass
    
    def _extract_cards_from_html(self) -> List[CardData]:
        """直接从HTML提取当前页所有卡片数据"""
        cards = []
        
        # 获取所有 modalCol（每个包含一张卡的完整数据）
        card_data_list = self.page.evaluate('''
            () => {
                const results = [];
                const modals = document.querySelectorAll('.resultCol .modalCol');
                
                modals.forEach(modal => {
                    try {
                        // 基础信息
                        const infoCol = modal.querySelector('.infoCol');
                        if (!infoCol) return;
                        
                        const spans = infoCol.querySelectorAll('span');
                        const cardNumber = spans[0]?.textContent?.trim() || '';
                        const rarity = spans[1]?.textContent?.trim() || '';
                        const cardType = spans[2]?.textContent?.trim() || '';
                        
                        // 名称
                        const name = modal.querySelector('.cardName')?.textContent?.trim() || '';
                        
                        // 图片URL
                        const img = modal.querySelector('.frontCol img');
                        let imageUrl = img?.getAttribute('data-src') || img?.getAttribute('src') || '';
                        if (imageUrl && !imageUrl.startsWith('http')) {
                            imageUrl = 'https://www.onepiece-cardgame.com' + imageUrl.replace('..', '');
                        }
                        
                        // 属性值
                        const getText = (selector) => {
                            const el = modal.querySelector(selector);
                            if (!el) return null;
                            // 获取文本，排除h3标题
                            const text = el.textContent.replace(el.querySelector('h3')?.textContent || '', '').trim();
                            return text === '-' ? null : text;
                        };
                        
                        const cost = getText('.cost');
                        const life = getText('.cost'); // cost div 在 LEADER 卡上是 life
                        const power = getText('.power');
                        const counter = getText('.counter');
                        const color = getText('.color');
                        const block = getText('.block');
                        const feature = getText('.feature');
                        const effect = getText('.text');
                        const trigger = getText('.trigger');
                        const getInfo = getText('.getInfo');
                        
                        // 属性图标
                        const attrImg = modal.querySelector('.attribute img');
                        const attribute = attrImg?.getAttribute('alt') || null;
                        
                        results.push({
                            cardNumber,
                            name,
                            cardType,
                            rarity,
                            imageUrl,
                            cost,
                            life,
                            power,
                            counter,
                            color,
                            block,
                            attribute,
                            feature,
                            effect,
                            trigger,
                            getInfo,
                            modalId: modal.id || null
                        });
                    } catch (e) {
                        console.error('Error parsing card:', e);
                    }
                });
                
                return results;
            }
        ''')
        
        for data in card_data_list:
            try:
                card = CardData(
                    card_number=data['cardNumber'],
                    name=data['name'],
                    card_type=data['cardType'],
                    rarity=data['rarity'],
                    colors=data.get('color') or '',
                    cost=self._parse_int(data.get('cost')),
                    life=self._parse_int(data.get('life')) if data['cardType'] == 'LEADER' else None,
                    power=self._parse_int(data.get('power')),
                    counter=self._parse_int(data.get('counter')),
                    attribute=data.get('attribute'),
                    traits=data.get('feature'),
                    effect_text=data.get('effect'),
                    trigger_text=data.get('trigger'),
                    source_info=data.get('getInfo'),
                    block_icon=self._parse_int(data.get('block')),
                    image_url=data.get('imageUrl'),
                    modal_id=data.get('modalId')
                )
                cards.append(card)
            except Exception as e:
                logger.error(f"解析卡片数据失败: {e}")
                continue
        
        return cards
    
    def _parse_int(self, value) -> Optional[int]:
        """解析整数"""
        if not value or value == '-':
            return None
        try:
            clean = re.sub(r'[^\d]', '', str(value))
            return int(clean) if clean else None
        except:
            return None
    
    def _download_image(self, card: CardData):
        """下载卡片图片"""
        if not card.image_url:
            return
        
        try:
            suffix = f"_v{card.version_index}" if card.version_index > 0 else ""
            filename = f"{card.card_number}{suffix}.png"
            filepath = self.IMAGE_DIR / filename
            
            if filepath.exists():
                logger.debug(f"图片已存在: {filename}")
                return
            
            response = requests.get(card.image_url, timeout=10)
            response.raise_for_status()
            
            filepath.write_bytes(response.content)
            logger.debug(f"下载图片: {filename}")
            
        except Exception as e:
            logger.error(f"下载图片失败 {card.card_number}: {e}")
    
    def _fetch_illustration_types(self, series_id: str) -> Dict[str, str]:
        """
        获取系列中每张卡片的插画类型（内部方法）
        
        Returns:
            Dict[str, str]: {modal_id: illustration_type}
        """
        illustration_types = ['原作', 'アニメ', 'オリジナル', 'その他']
        card_to_type = {}
        
        for ill_type in illustration_types:
            try:
                card_ids = self.page.evaluate('''
                    (args) => {
                        const [illustrationType, seriesId] = args;
                        return new Promise((resolve) => {
                            const formData = new FormData();
                            formData.append('illustrations[]', illustrationType);
                            formData.append('series', seriesId);
                            
                            fetch('/cardlist/', {
                                method: 'POST',
                                body: formData
                            })
                            .then(response => response.text())
                            .then(html => {
                                const parser = new DOMParser();
                                const doc = parser.parseFromString(html, 'text/html');
                                const ids = [];
                                doc.querySelectorAll('.resultCol .modalCol').forEach(modal => {
                                    if (modal.id) ids.push(modal.id);
                                });
                                resolve(ids);
                            })
                            .catch(err => resolve([]));
                        });
                    }
                ''', [ill_type, series_id])
                
                for card_id in card_ids:
                    if card_id and card_id not in card_to_type:
                        card_to_type[card_id] = ill_type
                        
                logger.debug(f"插画类型 [{ill_type}]: {len(card_ids)} 张")
            except Exception as e:
                logger.warning(f"获取插画类型 {ill_type} 失败: {e}")
        
        return card_to_type
    
    def _fetch_star_marked_cards(self, series_id: str) -> set:
        """
        获取系列中有星标的卡片ID（内部方法）
        
        Returns:
            set: 有星标的 modal_id 集合
        """
        try:
            star_ids = self.page.evaluate('''
                (seriesId) => {
                    return new Promise((resolve) => {
                        const formData = new FormData();
                        formData.append('stars[]', '1');  // 1 = 有星标
                        formData.append('series', seriesId);
                        
                        fetch('/cardlist/', {
                            method: 'POST',
                            body: formData
                        })
                        .then(response => response.text())
                        .then(html => {
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            const ids = [];
                            doc.querySelectorAll('.resultCol .modalCol').forEach(modal => {
                                if (modal.id) ids.push(modal.id);
                            });
                            resolve(ids);
                        })
                        .catch(err => resolve([]));
                    });
                }
            ''', series_id)
            
            logger.debug(f"星标卡: {len(star_ids)} 张")
            return set(star_ids)
        except Exception as e:
            logger.warning(f"获取星标卡失败: {e}")
            return set()
    
    def scrape_illustration_types(self, series_id: str) -> Dict[str, str]:
        """
        获取系列中每张卡片的插画类型（兼容旧接口）
        """
        return self._fetch_illustration_types(series_id)


def test_scraper():
    """测试爬虫"""
    scraper = JapanOfficialScraper()
    
    try:
        scraper.start_browser()
        
        # 获取系列列表
        print("\n=== 获取系列列表 ===")
        series_list = scraper.get_series_list()
        print(f"找到 {len(series_list)} 个系列\n")
        
        for s in series_list[:10]:
            print(f"  {s['code']:10} | {s['official_series_id']:8} | {s['series_type']:10} | {s['name'][:40]}")
        
        # 测试爬取第一个系列
        if series_list:
            print("\n=== 测试爬取系列 ===")
            first_series = series_list[0]
            print(f"爬取: {first_series['code']} - {first_series['name'][:40]}")
            
            cards = scraper.scrape_series(first_series['official_series_id'], download_images=False)
            
            print(f"\n共获取 {len(cards)} 张卡片:")
            for card in cards[:10]:
                print(f"  {card.card_number:12} | {card.rarity:3} | {card.card_type:10} | {card.name[:20]}")
            
            if len(cards) > 10:
                print(f"  ... 还有 {len(cards) - 10} 张卡片")
        
    finally:
        scraper.close_browser()


if __name__ == '__main__':
    test_scraper()
