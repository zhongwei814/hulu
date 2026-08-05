# Vercel FastAPI 入口点
# Vercel Python 运行时在项目根目录查找 ASGI app，此文件负责导入 backend/main.py 中的 app

import sys
from pathlib import Path

# 将 backend/ 加入 Python 搜索路径，使 main.py 中的 from config/model... 等导入正常解析
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from main import app  # noqa: E402
