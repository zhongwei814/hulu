# 部署指南 — 最会打呼之人

> 目标服务器：阿里云 1C2G，Ubuntu 22.04

---

## 前置条件

1. 服务器已安装 Ubuntu 22.04（或 Debian 11+）
2. 项目代码已上传到 `/opt/snore/`
3. 域名 DNS 已指向服务器 IP（如使用域名）

---

## 快速部署（推荐）

```bash
# 上传代码后，以 root 执行
sudo bash /opt/snore/deploy/setup.sh
```

## 手动部署

### 1. 系统依赖

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql nginx libsndfile1 ffmpeg
```

### 2. PostgreSQL

```bash
sudo -u postgres psql
CREATE USER snore WITH PASSWORD 'your_password';
CREATE DATABASE snore OWNER snore;
\q
```

### 3. Python 环境

```bash
cd /opt/snore/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置环境变量

编辑 `backend/.env`：
```ini
DATABASE_URL=postgresql://snore:your_password@localhost:5432/snore
ADMIN_PASSWORD=your_admin_password
AI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 5. Nginx

```bash
sudo cp /opt/snore/nginx.conf /etc/nginx/sites-available/snore
sudo ln -sf /etc/nginx/sites-available/snore /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 6. 启动

```bash
# 开发模式（前台运行）
cd /opt/snore/backend
source venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 生产模式（systemd 后台运行）
sudo cp /opt/snore/deploy/snore-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now snore-api
```

---

## 验证

```bash
# 检查 API 是否存活
curl http://localhost:8000/docs

# 检查 Nginx 是否正常代理
curl http://localhost/api/leaderboard/likes

# 查看后端日志
sudo journalctl -u snore-api -f
```

---

## SSL 证书（Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 常用维护

```bash
sudo systemctl status snore-api     # 查看服务状态
sudo systemctl restart snore-api    # 重启服务
sudo journalctl -u snore-api -n 50  # 查看最近日志
sudo nginx -t && sudo nginx -s reload  # 重载 Nginx
```

---

## 文件结构（服务器上）

```
/opt/snore/
├── backend/
│   ├── .env              ← 环境变量（不入 git）
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── uploads/          ← 音频文件存储
│   └── venv/             ← Python 虚拟环境
├── frontend/
│   ├── index.html
│   ├── play.html
│   ├── upload.html
│   ├── admin.html
│   ├── css/style.css
│   └── js/utils.js
├── deploy/
│   ├── setup.sh
│   ├── snore-api.service
│   └── DEPLOY.md
└── nginx.conf
```
