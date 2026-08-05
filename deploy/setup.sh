#!/usr/bin/env bash
# ============================================================
# 最会打呼之人 — 一键部署脚本（Ubuntu/Debian）
# 使用：sudo bash deploy/setup.sh
# ============================================================
set -euo pipefail

APP_DIR="/opt/snore"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"

echo "===== 1/6 安装系统依赖 ====="
apt-get update
apt-get install -y python3.11 python3.11-venv python3-pip \
    postgresql postgresql-client \
    nginx \
    libsndfile1 \
    ffmpeg

echo "===== 2/6 配置 PostgreSQL ====="
systemctl enable postgresql
systemctl start postgresql

# 创建数据库和用户（如果不存在）
su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='snore'\" | grep -q 1 || psql -c \"CREATE USER snore WITH PASSWORD 'snore123';\""
su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='snore'\" | grep -q 1 || psql -c \"CREATE DATABASE snore OWNER snore;\""

echo "===== 3/6 创建目录结构 ====="
mkdir -p "$BACKEND_DIR/uploads"
mkdir -p "$FRONTEND_DIR"
chown -R www-data:www-data "$APP_DIR"

echo "===== 4/6 安装 Python 依赖 ====="
python3.11 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

echo "===== 5/6 配置 Nginx ====="
cp "$APP_DIR/nginx.conf" /etc/nginx/sites-available/snore
ln -sf /etc/nginx/sites-available/snore /etc/nginx/sites-enabled/
# 移除默认站点
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "===== 6/6 配置 systemd 服务 ====="
cp "$APP_DIR/deploy/snore-api.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable snore-api
systemctl start snore-api

echo ""
echo "✅ 部署完成！"
echo "   前端地址: http://<服务器IP>"
echo "   API 文档: http://<服务器IP>/docs"
echo "   管理后台: http://<服务器IP>/admin.html"
echo ""
echo "⚠️  部署后请务必修改："
echo "   1. PostgreSQL 密码: /opt/snore/backend/.env 中的 DATABASE_URL"
echo "   2. 管理员密码: /opt/snore/backend/.env 中的 ADMIN_PASSWORD"
echo "   3. AI API Key: /opt/snore/backend/.env 中的 AI_API_KEY"
echo "   4. Nginx 域名: /etc/nginx/sites-available/snore 中的 server_name"
