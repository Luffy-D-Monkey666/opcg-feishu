# OPCG TCG 管理系统 - 项目文档

> 最后更新: 2026-02-16 11:35 GMT+8

## 📋 项目概述

**目标**: 构建一个 One Piece Card Game (OPCG) 卡牌收藏管理系统

**核心功能**:
- 卡片数据库（日文/英文）
- 卡片浏览和搜索
- 用户收藏管理
- 卡组构建
- 价格追踪

---

## 🏗️ 项目结构

```
/workspace/opcg-tcg/
├── app/                        # Flask 应用
│   ├── __init__.py            # Flask 工厂函数
│   ├── config.py              # 配置文件
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   ├── card.py            # Card, CardVersion, CardImage
│   │   ├── series.py          # Series (系列/补充包)
│   │   ├── collection.py      # UserCollection, Wishlist
│   │   ├── deck.py            # Deck, DeckCard
│   │   ├── user.py            # User
│   │   └── price.py           # PriceHistory
│   ├── routes/                # 路由蓝图 (待开发)
│   ├── services/              # 业务逻辑 (待开发)
│   ├── templates/             # Jinja2 模板 (待开发)
│   └── static/                # 静态资源
├── scrapers/                   # 爬虫模块
│   ├── __init__.py
│   ├── base.py                # 基础爬虫类
│   ├── jp_official.py         # ✅ 日文官网爬虫 (已完成)
│   └── utils/
├── scripts/                    # 运维脚本
│   └── scrape_all.py          # 批量爬取脚本
├── data/                       # 数据文件
│   ├── opcg_dev.db            # SQLite 数据库
│   └── images/                # 卡片图片 (可选)
├── logs/                       # 日志文件
├── tests/                      # 测试
├── requirements.txt            # 依赖
├── run.py                      # 启动入口
└── PROJECT.md                  # 本文档
```

---

## 📊 数据模型

### Series (系列)
```python
- id: Integer (PK)
- code: String(20)              # 如: OP-14, ST-01, PRB-01
- language: String(5)           # jp / en
- name: String(200)             # 系列名称
- series_type: String(20)       # booster/starter/extra/premium/promo/limited
- official_series_id: String(20) # 官网 series 参数值
- release_date: Date
- card_count: Integer
- cover_image: String(500)
```

### Card (卡片)
```python
- id: Integer (PK)
- card_number: String(20)       # 如: OP09-119, ST01-012
- language: String(5)           # jp / en
- series_id: Integer (FK)
- name: String(200)
- card_type: String(20)         # LEADER/CHARACTER/EVENT/STAGE
- rarity: String(10)            # L/C/UC/R/SR/SEC
- colors: String(50)            # 赤,緑,青,紫,黄,黒
- cost: Integer
- life: Integer                 # LEADER only
- power: Integer
- counter: Integer
- attribute: String(20)         # 斬/打/特/知
- traits: String(500)           # 特征/种族
- effect_text: Text
- trigger_text: Text
- source_info: String(500)
- block_icon: Integer
```

### CardVersion (卡片版本)
```python
- id: Integer (PK)
- card_id: Integer (FK)
- version_type: String(20)      # normal/alt_art/comic/special/promo
- version_suffix: String(10)    # 如: _p1, _sp, _v1
- has_star_mark: Boolean
- rarity_variant: String(20)
- source_description: String(500)
```

### CardImage (卡片图片)
```python
- id: Integer (PK)
- version_id: Integer (FK)
- image_type: String(10)        # front/back
- local_path: String(500)
- original_url: String(500)
- width: Integer
- height: Integer
```

### 其他模型
- **User**: 用户账户
- **UserCollection**: 用户收藏
- **Wishlist**: 愿望单
- **Deck**: 卡组
- **DeckCard**: 卡组卡片
- **PriceHistory**: 价格历史

---

## 🕷️ 爬虫模块

### 日文官网爬虫 (`scrapers/jp_official.py`)

**数据源**: https://www.onepiece-cardgame.com/cardlist/

**技术栈**: Playwright (headless Chrome)

**核心方法**:
```python
class JapanOfficialScraper:
    def get_series_list() -> List[Dict]
        # 获取所有系列列表
        # 返回: [{'code': 'OP-14', 'name': '...', 'official_series_id': '550114', 'series_type': 'booster'}, ...]
    
    def scrape_series(series_id: str, download_images: bool = False) -> List[CardData]
        # 爬取指定系列的所有卡片
        # 直接从 HTML 中的 .modalCol 元素解析数据，无需点击弹窗
```

**HTML 结构**:
```html
<div class="resultCol">
  <a class="modalOpen" data-src="#OP14-001">
    <img data-src="../images/cardlist/card/OP14-001.png">
  </a>
  <dl class="modalCol" id="OP14-001">
    <dt>
      <div class="infoCol">
        <span>OP14-001</span> | <span>L</span> | <span>LEADER</span>
      </div>
      <div class="cardName">トラファルガー・ロー</div>
    </dt>
    <dd>
      <div class="frontCol"><img data-src="..."></div>
      <div class="backCol">
        <div class="cost"><h3>ライフ</h3>5</div>
        <div class="power"><h3>パワー</h3>5000</div>
        <div class="color"><h3>色</h3>赤</div>
        <div class="feature"><h3>特徴</h3>王下七武海/超新星/ハートの海賊団</div>
        <div class="text"><h3>テキスト</h3>【起動メイン】...</div>
        <div class="getInfo"><h3>入手情報</h3>ブースターパック 蒼海の七傑【OP-14】</div>
      </div>
    </dd>
  </dl>
</div>
```

**运行命令**:
```bash
# 爬取单个系列
python scripts/scrape_all.py --series OP-14

# 爬取所有系列
python scripts/scrape_all.py --all

# 爬取并下载图片
python scripts/scrape_all.py --all --images
```

---

## 📈 当前进度

### ✅ 阶段1: 项目结构 + 数据模型 (完成)
- [x] Flask 项目结构
- [x] SQLAlchemy 数据模型
- [x] SQLite 数据库初始化

### ✅ 阶段2: 日文官网爬虫 (完成)
- [x] 系列列表获取
- [x] 卡片数据解析
- [x] 数据库存储
- [x] 批量爬取脚本

**爬取结果** (2026-02-16 更新):
- 系列数: **49**
- 卡片数: **2302** (唯一卡号)
- 版本数: **3683** (每个系列独立计数，含异画版和再录卡)
- 卡片-系列关联: **2776**

**数据模型改进** (2026-02-16):
- CardVersion 新增 `series_id` 字段，表示该版本来自哪个系列
- 同一张卡在不同系列中会有独立的版本记录
- 图鉴展示时按 `series_id` 筛选即可获得完整列表

### ✅ 阶段3a: Web界面 (完成)
- [x] 首页 (统计数据 + 最新系列)
- [x] 卡片列表页面 (分页 + 筛选)
- [x] 卡片详情页 (多版本轮播)
- [x] 系列列表页面
- [x] 系列详情页
- [x] 搜索功能

### ✅ 阶段3b: 英文官网爬虫 (完成)
- [x] 英文官网爬虫 (scrapers/en_official.py)
- [x] 英文卡片数据入库
- [x] 日英数据关联

**爬取结果**:
- 日文卡片: 2302
- 英文卡片: 1108
- 总计: 3410

### ✅ 阶段3c: 用户收藏功能 (完成)
- [x] 用户注册/登录 (Flask-Login)
- [x] 收藏管理 (添加/删除/查看)
- [x] 愿望单 (添加/删除/移入收藏)
- [x] 卡组构建 (创建/编辑/删除/卡片搜索)
- [x] 导航栏用户菜单
- [x] 卡片详情页收藏按钮

**新增功能**:
- 卡片详情页: 登录后可一键添加到收藏/愿望单
- 愿望单: 支持"入手"快捷操作（移入收藏）
- 卡组编辑器: 支持卡片搜索和实时添加
- API: /api/cards/search, /api/decks/*/add-card, /api/decks/*/remove-card

### ✅ 阶段4: 用户体验优化 (完成)
- [x] 收藏统计页面 (/user/stats)
  - 稀有度分布
  - 卡片类型分布
  - 颜色分布
  - 系列 Top 10
  - 系列覆盖率
- [x] 卡组分享链接
  - 分享码生成 (8位)
  - 公开卡组 URL (/user/d/<code>)
  - 分享弹窗 UI
- [x] 收藏导入/导出
  - CSV 格式导出
  - JSON 格式导出
  - CSV/JSON 导入
  - 卡组 JSON/TXT 导出

### ✅ 阶段5: 价格追踪 (完成)
- [x] 价格数据爬虫 (scrapers/price_scraper.py)
  - 数据源: OPTCG API (https://optcgapi.com/)
  - 支持单卡和批量查询
- [x] 价格更新脚本 (scripts/update_prices.py)
- [x] 卡片详情页价格显示
- [x] PriceHistory 模型 (USD 价格, 多版本支持)

### ✅ 阶段6: 后续优化 (完成)
- [x] 收藏总价值估算
- [x] 价格走势图表
- [x] 数据定期同步 (cron job)
- [ ] 日文价格数据源 (SNKRDUNK) - 待定
- [x] 数据模型修复：再录卡在图鉴中正确显示

### 🔧 阶段6a: 数据模型修复 (完成)
**问题**: 再录卡在图鉴中显示不完整
**原因**: CardVersion 只关联到 Card，无法区分版本来自哪个系列
**解决**: 
- CardVersion 新增 `series_id` 字段
- 每个系列的版本独立存储
- 图鉴查询改为按 `series_id` 筛选 CardVersion

**校核结果** (2026-02-16):
- OP-14: 156 ✅ (含 6 张再录卡)
- OP-09: 158 ✅
- OP-01: 154 ✅
- 所有 49 个系列版本数与官网一致

### 📈 阶段6b: 价格走势图表 (完成)
**新增功能**:
- `/prices` - 价格一览页面
- `/prices/card/<card_number>` - 卡片价格历史页面
- Chart.js 可视化价格走势
- 支持 7天/30天/90天/1年 时间范围
- API: `/prices/api/history/<version_id>` - 价格历史数据
- API: `/prices/api/compare` - 多卡价格对比

### ⏰ 阶段6c: 数据定期同步 (完成)
**脚本**: `scripts/sync_data.py`
- `--prices` 更新价格数据
- `--cards` 检查新卡片/系列
- `--full` 完整同步

**Cron 任务** (已配置):
- 每天 06:00 更新价格数据
- 每周日 02:00 检查新系列

### 💰 阶段6d: 收藏总价值估算 (完成)
**功能**:
- 收藏统计页面显示总价值 (USD)
- 显示有价格数据的卡片比例
- Top 3 最有价值卡片列表

---

## 🔧 开发环境

**Python**: 3.12  
**数据库**: SQLite (开发) / PostgreSQL (生产)  
**Web框架**: Flask  
**爬虫**: Playwright  
**日志**: Loguru

**依赖安装**:
```bash
cd /workspace/opcg-tcg
pip install -r requirements.txt
playwright install chromium
```

**启动应用**:
```bash
python run.py
```

---

## 📝 重要笔记

### 日文官网爬虫要点
1. 页面需要等待 JavaScript 渲染完成
2. Cookie 弹窗需要关闭才能操作
3. 卡片数据在 `.modalCol` 元素中，无需点击即可提取
4. 同一编号可能有多个版本（普通版、异画版等）
5. 分页通过点击 "NEXT" 链接实现

### 系列类型映射
```python
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
```

### 数据库查询示例
```python
from app import create_app, db
from app.models.series import Series
from app.models.card import Card, CardVersion

app = create_app()
with app.app_context():
    # 获取所有系列
    series = Series.query.all()
    
    # 搜索卡片
    cards = Card.query.filter(Card.name.contains('ルフィ')).all()
    
    # 获取系列下的卡片
    op14 = Series.query.filter_by(code='OP-14').first()
    cards = Card.query.filter_by(series_id=op14.id).all()
```

---

## 🚀 快速恢复指南

如果需要重新开始对话，请：

1. **阅读本文档**: `/workspace/opcg-tcg/PROJECT.md`
2. **检查数据库状态**:
   ```bash
   cd /workspace/opcg-tcg && python -c "
   from app import create_app, db
   from app.models.series import Series
   from app.models.card import Card
   app = create_app()
   with app.app_context():
       print(f'系列: {Series.query.count()}')
       print(f'卡片: {Card.query.count()}')
   "
   ```
3. **继续下一阶段**: Web界面 或 英文爬虫

---

*文档由 AI 助手生成和维护*
