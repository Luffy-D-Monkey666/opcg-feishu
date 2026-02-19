# OPCG TCG 卡牌图鉴系统

[![Tests](https://github.com/Luffy-D-Monkey666/opcg-feishu/actions/workflows/test.yml/badge.svg)](https://github.com/Luffy-D-Monkey666/opcg-feishu/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)


> One Piece Card Game 卡牌收藏管理工具

**在线演示**: https://opcg-tcg.onrender.com

## 📋 项目概述

这是一个完整的 One Piece Card Game (OPCG) 卡牌数据库和收藏管理系统，支持：

- 🃏 **卡片浏览** - 日文/英文双语支持，8500+ 张卡片版本
- 🔍 **高级搜索** - 按类型、颜色、稀有度、插画类型筛选
- 📦 **系列管理** - 104 个系列（Booster/Starter/Extra/Premium/Promo等）
- 👤 **用户系统** - 注册登录、收藏管理、愿望单
- 🎴 **卡组构建** - 创建卡组、分享链接
- 💰 **价格追踪** - 市场价格历史图表

## 🏗️ 技术架构

```
Flask (Python 3.12) + SQLAlchemy + Playwright
├── 后端: Flask + Flask-Login + Flask-SQLAlchemy
├── 数据库: SQLite (开发) / PostgreSQL (生产)
├── 爬虫: Playwright (headless Chrome)
├── 前端: Bootstrap 5 + Jinja2
└── 部署: Render.com
```

## 📁 项目结构

```
opcg-tcg/
├── app/                          # Flask 应用
│   ├── __init__.py              # 应用工厂
│   ├── config.py                # 配置文件
│   ├── models/                  # 数据模型
│   │   ├── card.py              # Card, CardVersion, CardImage
│   │   ├── series.py            # Series (系列)
│   │   ├── user.py              # User (用户)
│   │   ├── collection.py        # UserCollection, Wishlist
│   │   ├── deck.py              # Deck, DeckCard
│   │   └── price.py             # PriceHistory
│   ├── routes/                  # 路由
│   │   ├── main.py              # 首页
│   │   ├── cards.py             # 卡片列表/详情
│   │   ├── auth.py              # 登录/注册
│   │   ├── user.py              # 用户中心
│   │   ├── prices.py            # 价格页面
│   │   └── api.py               # JSON API
│   ├── templates/               # Jinja2 模板
│   └── static/                  # 静态资源
├── scrapers/                    # 爬虫模块
│   ├── jp_official.py           # 日文官网爬虫
│   ├── en_official.py           # 英文官网爬虫
│   └── price_scraper.py         # 价格爬虫
├── scripts/                     # 运维脚本
│   ├── scrape_all.py            # 批量爬取
│   ├── update_prices.py         # 价格更新
│   └── sync_to_pg.py            # 同步到 PostgreSQL
├── data/                        # 数据文件
│   └── opcg_dev.db              # SQLite 数据库
├── requirements.txt             # Python 依赖
├── render.yaml                  # Render 部署配置
├── Procfile                     # 启动命令
└── run.py                       # 入口文件
```

## 📊 数据模型

### ER 图 (Entity-Relationship Diagram)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           OPCG TCG 数据模型                              │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐      1:N      ┌──────────┐      1:N      ┌─────────────┐
  │  Series  │──────────────►│   Card   │──────────────►│ CardVersion │
  │          │               │          │               │             │
  │ id       │               │ id       │               │ id          │
  │ code     │               │ card_no  │               │ card_id(FK) │
  │ language │               │ series_id│◄──────┐       │ series_id   │──┐
  │ name     │               │ language │       │       │ version_type│  │
  │ type     │               │ name     │       │       │ illust_type │  │
  └──────────┘               │ rarity   │       │       └─────────────┘  │
       │                     │ colors   │       │              │         │
       │                     │ cost     │       │        1:N   │    1:N  │
       │                     │ power    │       │              ▼         ▼
       │    M:N              │ effect   │       │       ┌──────────┐ ┌────────────┐
       │ (card_series)       └──────────┘       │       │CardImage │ │PriceHistory│
       │                           │            │       │          │ │            │
       └───────────────────────────┴────────────┘       │ id       │ │ id         │
                                                        │ version_ │ │ version_id │
  ┌──────────┐      1:N      ┌────────────────┐         │   id(FK) │ │ price_usd  │
  │   User   │──────────────►│ UserCollection │         │ orig_url │ │ recorded_at│
  │          │               └────────────────┘         └──────────┘ └────────────┘
  │ id       │      1:N      ┌────────────────┐
  │ username │──────────────►│    Wishlist    │
  │ email    │               └────────────────┘
  │ password │      1:N      ┌──────────┐      1:N      ┌──────────┐
  └──────────┘──────────────►│   Deck   │──────────────►│ DeckCard │
                             │          │               │          │
                             │ id       │               │ deck_id  │
                             │ user_id  │               │ version_ │
                             │ name     │               │   id     │
                             │ is_public│               │ quantity │
                             │ share_   │               └──────────┘
                             │   code   │
                             └──────────┘
```

### 表关系说明

| 关系 | 类型 | 说明 |
|------|------|------|
| Series → Card | 1:N | 一个系列包含多张卡片 |
| Card → CardVersion | 1:N | 一张卡有多个版本（普通/异画/漫画） |
| CardVersion → CardImage | 1:N | 一个版本可有多张图片 |
| CardVersion → PriceHistory | 1:N | 一个版本有多条价格记录 |
| Card ↔ Series (card_series) | M:N | 再录卡可出现在多个系列 |
| User → Collection/Wishlist/Deck | 1:N | 用户数据 |

### Card 模型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| card_number | String(20) | 卡片编号 (如 OP14-001) |
| language | String(5) | 语言 (jp/en) |
| name | String(200) | 卡片名称 |
| card_type | String(20) | LEADER/CHARACTER/EVENT/STAGE |
| rarity | String(10) | L/C/UC/R/SR/SEC |
| colors | String(50) | 颜色 (逗号分隔: 赤,緑,青,紫,黄,黒) |
| cost | Integer | 费用 |
| life | Integer | 生命值 (LEADER) |
| power | Integer | 力量 |
| counter | Integer | Counter 值 |
| attribute | String(20) | 属性 (斬/打/特/知) |
| traits | String(500) | 特征 (斜杠分隔) |
| effect_text | Text | 效果文本 |
| trigger_text | Text | 触发效果 |
| block_icon | Integer | Block 图标数量 |

### CardVersion 模型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| card_id | FK | 所属卡片 |
| series_id | FK | 来源系列 |
| version_type | String(20) | normal/alt_art/comic/special/promo |
| version_suffix | String(10) | 版本后缀 (_p1, _sp) |
| illustration_type | String(20) | 原作/アニメ/オリジナル/その他 |
| source_description | String(500) | 入手情報 |

## ☁️ 部署指南

### 环境变量完整列表

| 变量名 | 必需 | 示例值 | 说明 |
|--------|------|--------|------|
| `FLASK_ENV` | ✅ | `production` | 环境模式 |
| `SECRET_KEY` | ✅ | `<随机32位>` | Session 加密密钥 |
| `DATABASE_URL` | ✅ | `postgresql://...` | 数据库连接字符串 |
| `PORT` | ❌ | `5000` | 端口 (Render 自动设置) |
| `PYTHON_VERSION` | ❌ | `3.11` | Python 版本 |

**生成 SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### .env.example

```bash
# 复制为 .env 并修改
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///data/opcg_dev.db
```

### Render 部署步骤

#### 1. 创建 PostgreSQL
- Render Dashboard → New → PostgreSQL
- 记录 **External Database URL**

#### 2. 创建 Web Service
- New → Web Service → 连接 GitHub
- **Build Command:**
  ```
  pip install -r requirements.txt && playwright install chromium --with-deps
  ```
- **Start Command:**
  ```
  gunicorn run:app --bind 0.0.0.0:$PORT --workers 2
  ```

#### 3. 设置环境变量
在 Environment 标签添加上述必需变量

#### 4. 数据迁移
```bash
# 本地导出
python scripts/sync_to_pg.py --export

# 设置生产 DB
export DATABASE_URL="postgresql://..."

# 导入
python scripts/sync_to_pg.py --import
```

### 常见问题

| 问题 | 解决 |
|------|------|
| 502 Bad Gateway | 免费层首次启动慢，等待 2-3 分钟 |
| 数据库连接失败 | 检查 DATABASE_URL 格式 |
| Playwright 安装失败 | Build Command 加 `--with-deps` |

### 保活 (防休眠)

用 [UptimeRobot](https://uptimerobot.com) 每 5 分钟 ping 网站 URL

## 🕷️ 爬虫说明

### 数据源

- **日文官网**: https://www.onepiece-cardgame.com/cardlist/
- **英文官网**: https://en.onepiece-cardgame.com/cardlist/
- **价格 API**: https://optcgapi.com/

### 爬虫原理

官网使用 JavaScript 渲染，数据存储在 HTML 的 `.modalCol` 元素中：

```html
<div class="resultCol">
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
        <div class="feature"><h3>特徴</h3>...</div>
        <div class="text"><h3>テキスト</h3>...</div>
        <div class="getInfo"><h3>入手情報</h3>...</div>
      </div>
    </dd>
  </dl>
</div>
```

爬虫使用 Playwright 加载页面后，通过 JavaScript 直接提取 DOM 数据。

### 运行爬虫

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 爬取单个系列
python scripts/scrape_all.py --series OP-14

# 爬取所有日文系列
python scripts/scrape_all.py --all --lang jp

# 爬取所有英文系列
python scripts/scrape_all.py --all --lang en

# 更新价格数据
python scripts/update_prices.py
```

## 🚀 本地开发

### 1. 克隆项目

```bash
git clone https://github.com/Luffy-D-Monkey666/opcg-feishu.git
cd opcg-feishu
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. 初始化数据库

```bash
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 5. 爬取数据

```bash
# 爬取日文数据
python scripts/scrape_all.py --all --lang jp

# 爬取英文数据
python scripts/scrape_all.py --all --lang en
```

### 6. 启动应用

```bash
python run.py
# 访问 http://localhost:5000
```

## 📱 主要页面

| 路由 | 功能 |
|------|------|
| `/` | 首页 (统计数据) |
| `/cards/` | 卡片列表 |
| `/cards/<number>` | 卡片详情 |
| `/cards/series` | 系列列表 |
| `/cards/series/<id>` | 系列详情 |
| `/search` | 搜索页面 |
| `/prices` | 价格一览 |
| `/prices/card/<number>` | 价格历史 |
| `/auth/login` | 登录 |
| `/auth/register` | 注册 |
| `/user/collection` | 我的收藏 |
| `/user/wishlist` | 愿望单 |
| `/user/decks` | 我的卡组 |
| `/user/stats` | 收藏统计 |

## 🔌 API 接口

详细文档见 [docs/API.md](docs/API.md)


```
GET  /api/cards/search?q=<关键词>     # 搜索卡片
GET  /api/prices/history/<version_id> # 价格历史
POST /api/decks/<id>/add-card         # 添加卡片到卡组
POST /api/decks/<id>/remove-card      # 从卡组移除卡片
```

## 📈 数据统计 (2026-02-17)

| 语言 | 系列数 | 卡片数 | 版本数 |
|------|--------|--------|--------|
| 日文 | 52 | 2,394 | 4,272 |
| 英文 | 52 | 2,346 | 4,310 |
| **总计** | **104** | **4,740** | **8,582** |

## 🔧 配置说明

### app/config.py

```python
class DevelopmentConfig:
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data/opcg_dev.db'
    SECRET_KEY = 'dev-secret-key'

class ProductionConfig:
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
```

### 图片 CDN

项目使用 wsrv.nl 作为图片 CDN 代理：

```python
def cdn_image(url, width=None):
    cdn_url = f"https://wsrv.nl/?url={quote(url, safe='')}"
    if width:
        cdn_url += f"&w={width}"
    cdn_url += "&output=webp&q=85"
    return cdn_url
```

## 📝 复刻指南 (给 AI)

如果你是另一个 AI，想要复刻这个项目：

1. **理解数据源**: 官网 HTML 结构在 `.modalCol` 中，所有卡片数据一次性加载
2. **爬虫核心**: 使用 Playwright 等待页面渲染，然后执行 JS 提取 DOM
3. **版本处理**: 同一编号可能有多个版本（普通/异画/漫画），用 `version_index` 区分
4. **系列关联**: CardVersion.series_id 表示该版本来自哪个补充包
5. **再录卡**: 使用 card_series 多对多表处理同一张卡在多个系列出现的情况
6. **语言分离**: jp 和 en 是独立的数据，通过 Card.language 区分

### 关键代码位置

- 爬虫逻辑: `scrapers/jp_official.py` 的 `_extract_cards_from_html()` 方法
- 数据模型: `app/models/card.py`
- 卡片列表: `app/routes/cards.py` 的 `card_list()` 方法
- 模板示例: `app/templates/cards/list.html`

## 📜 License

MIT License

---

*Built with ❤️ for OPCG collectors*

## 🔒 安全

- 所有敏感信息通过环境变量管理，不提交到仓库
- 详见 [docs/SECURITY.md](docs/SECURITY.md)

## 🔄 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.3 | 2026-02-19 | 清理调试文件，优化 .gitignore |
| v1.2 | 2026-02-17 | 价格追踪功能上线 |
| v1.1 | 2026-02-16 | 用户收藏和卡组功能 |
| v1.0 | 2026-02-15 | 首次发布，基础卡片浏览 |

## 🔄 数据库迁移

项目使用 Flask-Migrate 管理数据库结构变更：

```bash
# 初始化迁移目录 (首次)
flask db init

# 生成迁移脚本
flask db migrate -m "描述变更内容"

# 执行迁移
flask db upgrade

# 回滚迁移
flask db downgrade
```

**注意**: 仓库中已包含完整的 SQLite 数据库 (`data/opcg_dev.db`)，克隆后可直接运行，无需执行迁移。
