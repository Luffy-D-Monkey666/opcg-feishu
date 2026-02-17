# 贡献指南

## 代码规范

### 注释语言
- **代码注释**: 使用中文
- **变量名/函数名**: 使用英文
- **日文游戏术语**: 保持原文（如 `LEADER`, `赤`, `斬`）

### 示例
```python
# ✅ 正确
def get_card_by_number(card_number: str) -> Card:
    """根据卡片编号获取卡片"""
    pass

# ❌ 避免
def カード取得(カード番号: str):  # 不要用日文变量名
    pass
```

### 游戏术语对照表

| 中文 | 日文 | 英文 | 说明 |
|------|------|------|------|
| 领袖 | リーダー | LEADER | 卡片类型 |
| 角色 | キャラクター | CHARACTER | 卡片类型 |
| 事件 | イベント | EVENT | 卡片类型 |
| 舞台 | ステージ | STAGE | 卡片类型 |
| 稀有度 | レアリティ | Rarity | L/C/UC/R/SR/SEC |
| 费用 | コスト | Cost | 使用费用 |
| 力量 | パワー | Power | 战斗力 |
| 颜色 | 色 | Color | 赤/緑/青/紫/黄/黒 |
| 特征 | 特徴 | Traits | 种族/势力 |

## 运行测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率
pytest --cov=app --cov-report=html

# 运行特定测试
pytest tests/test_models.py -v
```
