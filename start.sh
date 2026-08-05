#!/usr/bin/env bash
set -e

# ╔══════════════════════════════════╗
# ║   🛌 最会打呼之人 — 本地启动     ║
# ╚══════════════════════════════════╝

cd "$(dirname "$0")"

echo ""
echo "  最会打呼之人 — 本地启动"
echo ""

# ── 1. 检查 Python ──
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.10+"
    exit 1
fi
echo "✅ Python 已就绪"

# ── 2. 创建虚拟环境 ──
if [ ! -d "venv" ]; then
    echo "📦 正在创建虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate

# ── 3. 安装依赖 ──
echo "📦 安装 Python 依赖（首次较慢，含 librosa 音频库）..."
pip install -r backend/requirements.txt -q

# ── 4. 环境变量 ──
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "📝 已创建 backend/.env"
fi

# 本地测试用 SQLite
export DATABASE_URL="sqlite:///./backend/snore.db"

# ── 5. 启动 ──
echo ""
echo "🚀 启动后端服务 http://localhost:8000"
echo ""

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
