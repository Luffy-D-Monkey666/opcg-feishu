# 安全指南

## 🔐 Secrets 管理

### 敏感信息清单

| 变量 | 说明 | 泄露风险 |
|------|------|---------|
| `SECRET_KEY` | Flask Session 加密 | 高 - 可伪造用户会话 |
| `DATABASE_URL` | 数据库连接 | 高 - 数据库暴露 |
| GitHub Token | 仓库访问 | 中 - 代码泄露 |

### 最佳实践

#### 1. 永远不要提交敏感信息

```bash
# .gitignore 已包含
.env
*.pem
*.key
secrets/
```

#### 2. 使用环境变量

```python
# ✅ 正确
SECRET_KEY = os.environ.get('SECRET_KEY')

# ❌ 错误
SECRET_KEY = 'hardcoded-secret-key'
```

#### 3. 生成强密钥

```bash
# 生成 SECRET_KEY (32 字节 hex)
python -c "import secrets; print(secrets.token_hex(32))"

# 生成 PostgreSQL 密码
openssl rand -base64 24
```

#### 4. 定期轮换密钥

- `SECRET_KEY`: 每 6 个月
- 数据库密码: 每 3 个月
- API Token: 按需

### 生产环境检查清单

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` 使用环境变量
- [ ] `DATABASE_URL` 使用环境变量
- [ ] HTTPS 强制启用
- [ ] 数据库连接加密 (SSL)
- [ ] 日志不包含敏感信息

### 报告漏洞

如发现安全漏洞，请通过以下方式报告：
- 不要公开披露
- 发送邮件至项目维护者
- 描述漏洞详情和复现步骤

我们会在 48 小时内响应。
