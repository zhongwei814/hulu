import os

# 数据库
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/snore"
)

# 文件存储
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

# 管理员密码（生产环境请通过环境变量覆盖）
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# 上传限制
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB
MAX_DURATION = 180                  # 3 分钟
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".webm"}

# 排行榜
LEADERBOARD_SIZE = 10

# AI 评语（DeepSeek API，OpenAI 兼容）
# ⚠️ 生产环境请通过环境变量覆盖，切勿将 key 提交到 git
AI_API_KEY = os.getenv("AI_API_KEY", "sk-7f06a5dc4c1640d49172895b2a031b5a")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-v4-flash")
