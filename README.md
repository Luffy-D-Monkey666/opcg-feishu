# OPCG TCG Manager

One Piece Card Game 卡牌收藏管理系统 - 一个全功能的卡牌数据库和收藏管理工具。

🔗 **在线演示**: [https://opcg-tcg.onrender.com](https://opcg-tcg.onrender.com)

## ✨ 功能特性

### 📚 卡牌数据库
- **多语言支持**: 日文/英文卡牌数据
- **完整图鉴**: 收录所有官方系列（OP/ST/EB/PRB/P 等）
- **高级筛选**: 
  - 系列、类型、颜色、稀有度
  - 插画类型（原作/动画/原创）
  - ⭐ 星标异画卡识别
- **版本管理**: 同一卡片的多个版本（普通版、异画版、SP 版等）
- **入手情报**: 每个版本显示来源信息

### 🎯 收藏管理
- 用户注册/登录
- 收藏列表管理
- 愿望单功能
- 收藏统计

### 💰 价格追踪
- 市场价格数据（数据来源: OPTCG API）
- 价格历史记录

## 🏗️ 技术架构

### 后端
- **框架**: Flask 3.0
- **数据库**: PostgreSQL (生产) / SQLite (开发)
- **ORM**: SQLAlchemy
- **认证**: Flask-Login

### 前端
- **UI框架**: Bootstrap 5
- **图标**: Bootstrap Icons
- **响应式设计**: 支持移动端

### 数据抓取
- **爬虫**: Playwright (Headless Chrome)
- **数据源**: 
  - 日文官网: onepiece-cardgame.com
  - 英文官网: en.onepiece-cardgame.com
  - 价格: OPTCG API

### 部署
- **平台**: Render
- **CI/CD**: GitHub 自动部署

## 📁 项目结构

```
opcg-tcg/
├── app/                      # Flask 应用
│   ├── __init__.py          # 应用工厂
│   ├── models/              # 数据模型
│   │   ├── card.py          # Card, CardVersion, CardImage
│   │   ├── series.py        # Series
│   │   ├── user.py          # User, Collection, Wishlist
│   │   └── price.py         # PriceHistory
│   ├── routes/              # 路由/视图
│   │   ├── main.py          # 首页
│   │   ├── cards.py         # 卡牌列表、详情
│   │   ├── auth.py          # 认证
│   │   ├── user.py          # 用户中心
│   │   ├── prices.py        # 价格
│   │   └── api.py           # API 接口
│   ├── templates/           # Jinja2 模板
│   └── static/              # 静态资源
├── scrapers/                 # 数据爬虫
│   ├── jp_official.py       # 日文官网爬虫
│   └── en_official.py       # 英文官网爬虫
├── scripts/                  # 脚本工具
│   ├── scrape_all.py        # 全量抓取
│   ├── update_prices.py     # 价格更新
│   └── update_source_info.py # 入手情报更新
├── requirements.txt          # Python 依赖
├── Procfile                 # Render 启动配置
└── render.yaml              # Render 部署配置
```

## 🗄️ 数据模型

### Card (卡片)
核心卡片数据，唯一标识: `card_number + language`

| 字段 | 说明 |
|------|------|
| card_number | 卡片编号 (如 OP01-001) |
| language | 语言 (jp/en) |
| name | 卡片名称 |
| card_type | 类型 (LEADER/CHARACTER/EVENT/STAGE) |
| rarity | 稀有度 (L/SEC/SR/R/UC/C/SP CARD/TR/P) |
| colors | 颜色 (赤/緑/青/紫/黒/黄) |
| cost/life/power/counter | 数值属性 |
| effect_text | 效果文本 |
| traits | 特征 |

### CardVersion (卡片版本)
同一卡片的不同版本（普通、异画、SP 等）

| 字段 | 说明 |
|------|------|
| card_id | 所属卡片 |
| series_id | 来源系列 |
| version_type | 版本类型 (normal/alt_art/special/promo) |
| version_suffix | 版本后缀 (_p1, _v1 等) |
| has_star_mark | ⭐ 是否有星标 (OP04+ 异画卡) |
| source_description | 入手情报 |
| illustration_type | 插画类型 (原作/アニメ/オリジナル) |

### Series (系列)
卡片系列/补充包信息

| 字段 | 说明 |
|------|------|
| code | 系列代码 (OP01, ST01 等) |
| name | 系列名称 |
| series_type | 类型 (booster/starter/extra/promo) |
| language | 语言 |

## 🚀 本地开发

### 环境要求
- Python 3.12+
- PostgreSQL (可选，开发可用 SQLite)
- Playwright (爬虫需要)

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/Luffy-D-Monkey666/opcg-feishu.git
cd opcg-feishu

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器 (爬虫需要)
playwright install chromium

# 初始化数据库
flask db upgrade

# 运行开发服务器
flask run --debug
```

### 环境变量

```bash
# .env 文件
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/opcg  # 或 sqlite:///instance/opcg.db
FLASK_ENV=development
```

## 📊 数据抓取

### 全量抓取日文数据
```bash
python scripts/scrape_all.py
```

### 抓取英文数据
```bash
python scripts/scrape_en_full.py
```

### 更新价格数据
```bash
python scripts/update_prices.py
```

### 更新入手情报
```bash
python scripts/update_source_info.py
```

## 🌟 特色功能说明

### 星标异画卡识别
OP04 及之后的补充包中，异画卡（Parallel/Alt Art）在卡面编号位置有星星标识。系统通过分析图片 URL 后缀 (`_r1`, `_r2`) 自动识别这些版本。

### 多版本管理
同一卡片编号可能有多个版本：
- **普通版**: 标准版本
- **异画版 (alt_art)**: 不同插画的收藏版
- **SP 版**: 特殊稀有版本
- **Promo**: 促销/活动限定版

每个版本独立记录来源系列和入手情报。

### 系列导航
支持从不同系列进入同一张卡片的详情页，会自动显示该系列对应版本的信息。

## 📝 API 接口

### 收藏操作
```
POST /api/collection/add    # 添加收藏
POST /api/collection/remove # 移除收藏
POST /api/wishlist/add      # 添加愿望单
POST /api/wishlist/remove   # 移除愿望单
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- 数据来源: [ONE PIECE CARD GAME 官方网站](https://www.onepiece-cardgame.com/)
- 价格数据: OPTCG API
- 图片版权归 Bandai/集英社/东映动画 所有

---

Made with ❤️ for One Piece Card Game collectors
