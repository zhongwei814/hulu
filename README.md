# 最会打呼之人 🛌

> 一个轻量级、无需登录的趣玩社区 —— 上传你的呼噜录音，让社区投票和 AI 算法共同评选出"最会打呼之人"。

---

## 功能

- 🎤 **匿名上传** — 上传 mp3 / wav / ogg / webm 音频（≤10MB，≤3 分钟），无需注册
- 🔥 **点赞榜** — 群众的选择，按点赞数排行
- ⭐ **评分榜** — 算法 + AI 双维度打分（节奏、能量、爆发力、感染力）
- 🤖 **AI 评语** — 由 DeepSeek 大模型生成趣味评论，像"有种重型机械缓慢驶过月球表面的震撼"
- 📱 **移动端优先** — 极简浅色风格，手机端完美适配
- 🛡️ **基础防刷** — IP 级别限制，点赞/上传均有校验
- ⚙️ **后台管理** — 统计面板、音频列表、删除管理

---

## 技术栈

| 层级 | 方案 |
|------|------|
| 后端框架 | **FastAPI** + Uvicorn |
| 数据库 | **PostgreSQL** + SQLAlchemy |
| 音频分析 | **Librosa**（规则引擎打分） |
| AI 评语 | **DeepSeek API**（大模型文本生成） |
| 前端 | **HTML + CSS + Alpine.js**（CDN 引入，零构建） |
| 反向代理 | **Nginx** |

---

## 项目结构

```
最会打呼之人/
├── frontend/                  # 前端静态页面
│   ├── index.html             # 首页 — 排行榜 + 上传入口
│   ├── play.html              # 播放页 — 音频播放 + 点赞/点踩
│   ├── upload.html            # 上传页
│   ├── admin.html             # 后台管理页
│   ├── css/style.css          # 样式
│   └── js/utils.js            # 工具函数
├── backend/                   # Python FastAPI 后端
│   ├── main.py                # 应用入口 + API 路由
│   ├── config.py              # 配置加载
│   ├── models/                # SQLAlchemy 数据模型
│   ├── schemas/               # Pydantic 请求/响应模型
│   ├── services/              # 业务逻辑（评分、AI 评语、昵称生成）
│   └── uploads/               # 音频文件存储
├── nginx.conf                 # Nginx 配置
├── requirements.txt           # Python 依赖
└── Vision.md                  # 项目愿景文档
```

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- PostgreSQL
- FFmpeg（音频处理依赖）

### 2. 安装依赖

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 3. 配置环境变量

复制 `backend/.env.example` 为 `backend/.env`，填入数据库连接和 API Key：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/snore
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 4. 启动后端

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 启动前端（开发）

直接浏览器打开 `frontend/index.html`，或使用 Nginx 部署（见 `nginx.conf`）。

---

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/audio/upload` | 上传音频 |
| `GET` | `/api/audio/{id}` | 音频详情（含 AI 评语） |
| `GET` | `/api/audio/stream/{id}` | 音频流播放 |
| `POST` | `/api/audio/{id}/like` | 点赞 |
| `POST` | `/api/audio/{id}/dislike` | 点踩 |
| `GET` | `/api/leaderboard/likes` | 点赞榜 Top 10 |
| `GET` | `/api/leaderboard/scores` | 评分榜 Top 10 |
| `GET` | `/api/admin/stats` | 后台统计 |
| `DELETE` | `/api/admin/audios/{id}` | 删除音频 |

---

## 部署

单机部署（1C2G 云服务器即可）：

```
用户 → Nginx (:80) → /api/* → Uvicorn (:8000) → PostgreSQL
                    → /*     → 前端静态文件
```

详细部署步骤见 [Vision.md](Vision.md)。

---

## 许可证

MIT

---

*"让最会打呼之人，被世界听到。"*
