# API 文档

## 基础信息

- **Base URL**: `https://opcg-tcg.onrender.com`
- **响应格式**: JSON
- **编码**: UTF-8

---

## 卡片搜索

### `GET /api/cards/search`

搜索卡片名称或编号。

**参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| q | string | ✅ | 搜索关键词 |
| lang | string | ❌ | 语言 (jp/en)，默认 jp |
| limit | int | ❌ | 返回数量，默认 20，最大 100 |

**请求示例:**
```
GET /api/cards/search?q=ルフィ&lang=jp&limit=10
```

**响应示例:**
```json
{
  "results": [
    {
      "card_number": "OP01-003",
      "name": "モンキー・Ｄ・ルフィ",
      "card_type": "LEADER",
      "rarity": "L",
      "colors": "赤",
      "image_url": "https://..."
    }
  ],
  "total": 2,
  "query": "ルフィ"
}
```

---

## 价格历史

### `GET /api/prices/history/<version_id>`

获取指定版本的价格历史。

**参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| version_id | int | CardVersion ID |
| days | int | 历史天数 (默认30) |

**响应示例:**
```json
{
  "version_id": 1234,
  "prices": [
    {"date": "2026-02-01", "price_usd": 15.50},
    {"date": "2026-02-15", "price_usd": 14.75}
  ],
  "current_price": 14.75
}
```

---

## 卡组操作 (需登录)

### `POST /api/decks/<deck_id>/add-card`

**请求体:**
```json
{"version_id": 1234, "quantity": 4}
```

**响应:**
```json
{"success": true, "total_cards": 50}
```

### `POST /api/decks/<deck_id>/remove-card`

**请求体:**
```json
{"version_id": 1234, "quantity": 1}
```

**响应:**
```json
{"success": true, "remaining": 3}
```

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未登录 |
| 404 | 不存在 |
| 500 | 服务器错误 |
