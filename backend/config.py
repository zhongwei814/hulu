import os
from pathlib import Path

# 自动加载 .env 文件（本地开发用，生产环境请直接设置环境变量）
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv 未安装时静默跳过，依赖系统环境变量

# 数据库
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/snore"
)

# 文件存储
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

# 管理员密码（生产环境务必通过环境变量覆盖）
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# 上传限制
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB
MAX_DURATION = 180                  # 3 分钟
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".webm"}

# 排行榜
LEADERBOARD_SIZE = 10

# AI 评语（DeepSeek API，OpenAI 兼容）
# ⚠️ key 为空时 AI 评语功能自动降级跳过，不影响上传和 Librosa 评分
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-v4-flash")
