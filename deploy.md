# Deploy — 最会打呼之人 部署指南

> 两种部署方式：**本地开发运行** + **Vercel 线上部署**。

---

## 一、本地部署

### 1.1 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.11+ |
| PostgreSQL | 14+（本地运行） |
| pip | 最新即可 |

### 1.2 克隆 & 安装

```bash
# 1. 进入项目
cd 最会打呼之人

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate      # Linux / macOS
# venv\Scripts\activate       # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

### 1.3 创建 `.env` 文件

在 `backend/` 目录下创建 `.env`（此文件不提交 git，已在 `.gitignore` 中）：

```env
# 数据库（本地 PostgreSQL 默认值，可省略）
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/snore

# 管理员密码（生产环境务必修改）
ADMIN_PASSWORD=admin123

# AI 评语（DeepSeek API，不填则 AI 评语功能自动降级跳过）
AI_API_KEY=你的DeepSeek_API_Key
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
```

> `AI_API_KEY` 留空不影响上传和 Librosa 评分，只是不生成 AI 评语。

### 1.4 创建 PostgreSQL 数据库

```bash
# 登录 PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE snore;
\q
```

### 1.5 启动

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

打开浏览器访问：
- **前端页面**：`http://localhost:8000`
- **API 文档**（Swagger）：`http://localhost:8000/docs`

> 本地开发模式下，`main.py` 会自动 serve `frontend/` 目录下的静态文件，无需额外配置 Nginx。

### 1.6 目录说明（本地模式）

```
backend/
├── uploads/       ← 上传的音频文件存这里
├── snore.db       ← Vercel 模式用 SQLite（本地默认用 PostgreSQL，不会出现此文件）
└── .env           ← 环境变量（不提交 git）
```

---

## 二、Vercel 部署

### 2.1 前置准备

1. 注册 [Vercel](https://vercel.com) 账号
2. 安装 Vercel CLI（可选，推荐用 GitHub 集成自动部署）：
   ```bash
   npm i -g vercel
   ```

### 2.2 部署步骤（推荐：GitHub 自动部署）

1. **将项目推送到 GitHub**（公开或私有仓库均可）

2. **在 Vercel 中导入项目**：
   - 进入 [vercel.com/new](https://vercel.com/new)
   - 选择你的 GitHub 仓库
   - 框架自动检测或手动选择 **Other**
   - 点击 Deploy

3. **配置环境变量**（Vercel Dashboard → Settings → Environment Variables）：

   | 变量名 | 值 | 说明 |
   |--------|-----|------|
   | `ADMIN_PASSWORD` | 你的管理密码 | 必填 |
   | `AI_API_KEY` | 你的 DeepSeek API Key | 可选，不填则跳过 AI 评语 |
   | `AI_BASE_URL` | `https://api.deepseek.com` | 可选 |
   | `AI_MODEL` | `deepseek-v4-flash` | 可选 |

   > ⚠️ Vercel 环境会自动检测 `VERCEL` 环境变量，数据库自动切换为 SQLite、上传目录自动切换为 `/tmp/uploads`，**不需要手动设置这些**。

4. **重新部署**（环境变量修改后需要 Redeploy 才能生效）

### 2.3 项目配置文件

项目根目录已有 `vercel.json`，Vercel 会自动读取：

```json
{
  "version": 2,
  "builds": [
    { "src": "index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/index.py" },
    { "src": "/uploads/(.*)", "dest": "/index.py" },
    { "src": "/(.*)", "dest": "/index.py" }
  ]
}
```

> - 所有请求（API + 前端静态文件）统一由 FastAPI 处理
> - ⚠️ 必须使用 `routes`（而不是 `rewrites`）：legacy `rewrites` 不转发 POST 等非 GET 请求，会导致上传返回 405 Method Not Allowed
> - `/api/*` 和 `/uploads/*` 明确路由到 Python 后端
> - 其他请求（`/`, `/index.html`, `/css/*`, `/js/*` 等）也由 FastAPI 内置的 StaticFiles 中间件 serve
> - FastAPI 中 API 路由优先于静态文件挂载，不会互相冲突

### 2.4 Vercel 的行为差异

| 项目 | 本地 | Vercel |
|------|------|--------|
| 数据库 | PostgreSQL | **SQLite**（自动切换） |
| 上传目录 | `backend/uploads/` | `/tmp/uploads/` |
| 前端服务 | FastAPI 内置 StaticFiles | FastAPI 内置 StaticFiles（统一方案） |
| 环境变量 | `.env` 文件 | Vercel Dashboard 设置 |
| 持久化 | 本地磁盘 | ⚠️ `/tmp` 在 Serverless 实例销毁时清空 |

### 2.5 Vercel 限制与注意事项

| 限制 | 说明 | 影响 |
|------|------|------|
| **上传文件不持久** | Serverless 的 `/tmp` 目录在函数实例回收后清空 | 上传的音频文件会在闲置一段时间后丢失 |
| **SQLite 单文件** | 每次部署会重置数据库 | 现有的音频和点赞数据会丢失 |
| **Librosa 体积** | `librosa` 包体积较大（~100MB+） | Hobby 计划有 250MB 函数体积限制，可能需要精简依赖 |
| **函数超时** | Hobby 计划 10s 最大执行时间 | 音频评分是后台异步任务，需要确认是否能在超时前完成 |

> 💡 **建议**：Vercel 适合快速预览和前端展示。如需完整持久化功能，建议将后端部署到阿里云服务器（见下方 §三）。

### 2.6 自定义域名

1. Vercel Dashboard → Domains → Add
2. 输入你的域名，按提示在 DNS 服务商处添加 CNAME 记录指向 `cname.vercel-dns.com`
3. SSL 证书自动签发（Let's Encrypt）

---

## 三、生产环境部署（阿里云服务器）

当 Vercel 的限制（数据不持久、函数超时）成为瓶颈后，迁回传统服务器部署：

### 3.1 服务器配置

- **规格**：1C2G（约 ¥50–70/月）
- **系统**：Ubuntu 22.04
- **软件**：Python 3.11+ / PostgreSQL / Nginx

### 3.2 部署步骤

```bash
# 1. 安装 PostgreSQL
sudo apt install postgresql
sudo -u postgres psql -c "CREATE DATABASE snore;"

# 2. 克隆项目
git clone <你的仓库> /opt/snore
cd /opt/snore

# 3. 创建虚拟环境 & 安装依赖
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 设置环境变量
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/snore
export ADMIN_PASSWORD=<你的密码>
export AI_API_KEY=<你的Key>

# 5. 配置 Nginx（见项目根目录 nginx.conf）

# 6. 使用 systemd 守护 FastAPI
sudo tee /etc/systemd/system/snore.service << 'EOF'
[Unit]
Description=最会打呼之人 API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/snore/backend
ExecStart=/opt/snore/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now snore
```

### 3.3 生产 checklist

- [ ] 修改 `ADMIN_PASSWORD` 为强密码
- [ ] PostgreSQL 设置专用用户和密码
- [ ] 配置 Nginx SSL（Let's Encrypt）
- [ ] 配置防火墙（仅开放 80/443）
- [ ] 设置日志轮转（`/var/log/snore/`）
- [ ] 定期备份 `uploads/` 目录和 PostgreSQL 数据库
