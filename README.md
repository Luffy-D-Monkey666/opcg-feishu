# OPCG TCG 卡牌图鉴系统

[![Tests](https://github.com/Luffy-D-Monkey666/opcg-feishu/actions/workflows/test.yml/badge.svg)](https://github.com/Luffy-D-Monkey666/opcg-feishu/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

> One Piece Card Game 卡牌收藏管理工具

**🌐 在线演示**: https://opcg-tcg.onrender.com

## ⚡ 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/Luffy-D-Monkey666/opcg-feishu.git
cd opcg-feishu

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 4. 启动（仓库已含完整数据库）
python run.py
# 访问 http://localhost:5000
```

> 💡 仓库包含完整的 SQLite 数据库，克隆后可直接运行，无需爬取数据。

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🃏 **卡片浏览** | 日文/英文双语支持，8500+ 张卡片版本 |
| 🔍 **高级搜索** | 按类型、颜色、稀有度、插画类型筛选 |
| 📦 **系列管理** | 104 个系列（Booster/Starter/Promo等） |
| 👤 **用户系统** | 注册登录、收藏管理、愿望单 |
| 🎴 **卡组构建** | 创建卡组、分享链接 |
| 💰 **价格追踪** | 市场价格历史图表 |

## 🏗️ 技术栈

```
Flask (Python 3.12) + SQLAlchemy + Playwright
├── 后端: Flask + Flask-Login + Flask-Migrate
├── 数据库: SQLite (开发) / PostgreSQL (生产)
├── 爬虫: Playwright (headless Chrome)
├── 前端: Bootstrap 5 + Jinja2
├── CI/CD: GitHub Actions
└── 部署: Render.com
```

## 📁 项目结构

```
opcg-tcg/
├── app/                    # Flask 应用
│   ├── __init__.py         # 应用工厂
│   ├── config.py           # 配置
│   ├── models/             # 数据模型 (Card, Series, User, Deck, Price)
│   ├── routes/             # 路由 (main, cards, auth, user, prices, api)
│   ├── services/           # 业务逻辑
│   ├── templates/          # Jinja2 模板
│   └── static/             # CSS/JS/图片
├── scrapers/               # 爬虫模块
│   ├── jp_official.py      # 日文官网爬虫
│   ├── en_official.py      # 英文官网爬虫
│   └── price_scraper.py    # 价格爬虫
├── scripts/                # 运维脚本
│   ├── scrape_all.py       # 批量爬取
│   ├── sync_data.py        # 数据同步
│   └── sync_to_pg.py       # PostgreSQL 迁移
├── tests/                  # 测试
├── docs/                   # 文档
│   └── API.md              # API 文档
├── data/                   # SQLite 数据库
├── requirements.txt
├── render.yaml             # Render 部署配置
└── run.py                  # 入口文件
```

## 📊 数据模型

```
┌──────────┐     1:N     ┌──────────┐     1:N     ┌─────────────┐
│  Series  │────────────►│   Card   │────────────►│ CardVersion │
│          │             │          │             │             │
│ code     │             │ card_no  │             │ version_type│───┐
│ language │             │ name     │             │ illust_type │   │
│ name     │             │ rarity   │             └─────────────┘   │
│ type     │             │ colors   │                   │           │
└──────────┘             │ effect   │              1:N  │      1:N  │
                         └──────────┘                   ▼           ▼
                                                ┌──────────┐ ┌────────────┐
┌──────────┐     1:N     ┌──────────┐           │CardImage │ │PriceHistory│
│   User   │────────────►│   Deck   │           └──────────┘ └────────────┘
│          │             │          │     1:N
│ username │     1:N     │ name     │────────►┌──────────┐
│ email    │────────────►│ is_public│         │ DeckCard │
└──────────┘ Collection  │ share_   │         │ quantity │
             Wishlist    │   code   │         └──────────┘
                         └──────────┘
```

### Card 主要字段

| 字段 | 说明 | 字段 | 说明 |
|------|------|------|------|
| `card_number` | 编号 (OP14-001) | `card_type` | LEADER/CHARACTER/EVENT/STAGE |
| `name` | 卡片名称 | `rarity` | L/C/UC/R/SR/SEC |
| `colors` | 颜色 (赤,緑,青,紫,黄,黒) | `cost` | 费用 |
| `power` | 力量 | `counter` | Counter 值 |
| `effect_text` | 效果文本 | `traits` | 特征 |

### CardVersion 字段

| 字段 | 说明 |
|------|------|
| `version_type` | normal / alt_art / comic / special / promo |
| `illustration_type` | 原作 / アニメ / オリジナル / その他 |

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 带覆盖率
pytest tests/ -v --cov=app --cov-report=term-missing

# 只运行某类测试
pytest tests/test_models.py -v
pytest tests/test_routes.py -v
```

CI 自动运行测试和代码风格检查（black, isort, flake8）。

## 🕷️ 爬虫使用

### 数据源
- 日文官网: https://www.onepiece-cardgame.com/cardlist/
- 英文官网: https://en.onepiece-cardgame.com/cardlist/
- 价格 API: https://optcgapi.com/

### 运行爬虫

```bash
# 爬取单个系列
python scripts/scrape_all.py --series OP-14

# 爬取所有日文系列
python scripts/scrape_all.py --all --lang jp

# 爬取所有英文系列
python scripts/scrape_all.py --all --lang en

# 更新价格
python scripts/update_prices.py
```

### 爬虫原理

官网使用 JavaScript 渲染，卡片数据存储在 `.modalCol` 元素中。爬虫使用 Playwright 加载页面后执行 JS 提取 DOM 数据。详见 `scrapers/jp_official.py`。

## ☁️ 部署

### 环境变量

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `FLASK_ENV` | ✅ | `production` |
| `SECRET_KEY` | ✅ | Session 密钥 (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | ✅ | PostgreSQL 连接字符串 |

### Render 部署

1. **创建 PostgreSQL**: Render Dashboard → New → PostgreSQL
2. **创建 Web Service**: 连接 GitHub 仓库
3. **Build Command**:
   ```
   pip install -r requirements.txt && playwright install chromium --with-deps
   ```
4. **Start Command**:
   ```
   gunicorn run:app --bind 0.0.0.0:$PORT --workers 2
   ```
5. **设置环境变量**

### 数据迁移

```bash
# 本地导出
python scripts/sync_to_pg.py --export

# 设置生产 DB 后导入
export DATABASE_URL="postgresql://..."
python scripts/sync_to_pg.py --import
```

### 保活

用 [UptimeRobot](https://uptimerobot.com) 每 5 分钟 ping 网站 URL，防止免费层休眠。

## 📱 主要路由

| 路由 | 功能 |
|------|------|
| `/` | 首页 |
| `/cards/` | 卡片列表 |
| `/cards/<number>` | 卡片详情 |
| `/cards/series` | 系列列表 |
| `/search` | 搜索 |
| `/prices` | 价格一览 |
| `/auth/login` | 登录 |
| `/user/collection` | 我的收藏 |
| `/user/decks` | 我的卡组 |

## 🔌 API

详细文档见 [docs/API.md](docs/API.md)

```
GET  /api/cards/search?q=<关键词>      # 搜索卡片
GET  /api/prices/history/<version_id>  # 价格历史
POST /api/decks/<id>/add-card          # 添加卡片到卡组
POST /api/decks/<id>/remove-card       # 从卡组移除卡片
```

## 🔧 数据库迁移

```bash
flask db migrate -m "描述"  # 生成迁移
flask db upgrade            # 执行迁移
flask db downgrade          # 回滚
```

## 📈 数据统计

| 语言 | 系列数 | 卡片数 | 版本数 |
|------|--------|--------|--------|
| 日文 | 52 | 2,394 | 4,272 |
| 英文 | 52 | 2,346 | 4,310 |
| **总计** | **104** | **4,740** | **8,582** |

*更新于 2026-02-17*

## 🤝 贡献

欢迎 PR！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
# 代码格式化
black app/ tests/ scripts/
isort app/ tests/ scripts/
flake8 app/ tests/ scripts/
```

## 📜 License

[MIT License](LICENSE)

---

## 📝 复刻指南

如果你想基于这个项目构建类似系统：

### 核心要点

1. **数据源**: 官网 HTML 的 `.modalCol` 元素包含所有卡片数据，一次性加载
2. **爬虫**: 使用 Playwright 等待 JS 渲染后提取 DOM
3. **版本处理**: 同一编号可能有多个版本（普通/异画/漫画），用 `version_index` 区分
4. **语言分离**: jp/en 是独立数据，通过 `Card.language` 区分
5. **再录卡**: 用 M:N 关联表处理同一张卡出现在多个系列

### 关键文件

| 文件 | 作用 |
|------|------|
| `scrapers/jp_official.py` | 爬虫核心逻辑 |
| `app/models/card.py` | 数据模型定义 |
| `app/routes/cards.py` | 卡片列表路由 |
| `app/templates/cards/list.html` | 前端模板示例 |

### 需要替换的内容

复刻时需修改：
- [ ] GitHub 仓库链接
- [ ] 在线演示 URL
- [ ] 数据统计数字
- [ ] 项目名称和描述

---

*Built with ❤️ for OPCG collectors*
