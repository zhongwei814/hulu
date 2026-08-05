# task_b — 后端开发任务指南

> 本文档是后端开发的具体步骤拆解。每一步完成后在 `help.md` 的任务表中标记 ✅。
> 技术栈：**Python 3.11+ · FastAPI · SQLAlchemy · PostgreSQL · Librosa · Uvicorn**
> 🆕 = 本次新增/修改（AI 评语功能）

---

## 零、项目初始化

### 0.1 创建 Python 虚拟环境

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 0.2 安装依赖 `requirements.txt`

```
fastapi==0.115.*
uvicorn[standard]==0.32.*
sqlalchemy==2.0.*
psycopg2-binary==2.9.*
python-multipart==0.0.*
librosa==0.10.*
soundfile==0.12.*
numpy==1.26.*
openai>=1.0.0           # 🆕 DeepSeek API（OpenAI 兼容）
```

```bash
pip install -r requirements.txt
```

### 0.3 配置文件 `backend/config.py`

```python
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/snore")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # 生产环境务必修改
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DURATION = 180  # 3分钟
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".webm"}

# 🆕 AI 评语配置（DeepSeek OpenAI 兼容 API）
AI_API_KEY = os.getenv("AI_API_KEY", "")           # ⚠️ 必须通过环境变量设置
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-v4-flash")
```

> ⚠️ **安全提醒**：`AI_API_KEY` 必须通过环境变量传入，切勿将 key 写在 config.py 或提交到 git。开发时用 `.env` 文件（加入 `.gitignore`）。

---

## 一、数据库模型 `models/`

### 步骤 1.1：`models/database.py` — 数据库连接

- 创建 SQLAlchemy `engine`（连接 PostgreSQL）
- 创建 `SessionLocal`（每个请求一个 session）
- 创建 `Base`（所有模型的基类）
- 提供 `get_db()` 依赖注入函数

### 步骤 1.2：`models/audio.py` — Audio 模型

```
audio 表字段：
  id              SERIAL PRIMARY KEY
  nickname        VARCHAR(50)      昵称（可空，空则自动生成）
  file_path       VARCHAR(500)     音频文件相对路径
  duration        FLOAT            时长（秒）
  file_size       INTEGER          文件大小（字节）
  score           FLOAT            综合评分 0–100（可空，打分前为 NULL）
  score_detail    JSONB             五维度评分详情（可空）
  like_count      INTEGER DEFAULT 0
  dislike_count   INTEGER DEFAULT 0
  ip_address      VARCHAR(45)      上传者 IP
  created_at      TIMESTAMP        上传时间
  🆕 ai_commentary   VARCHAR(500)  AI 创意评语（可空，AI 打分前为 NULL）
  🆕 ai_score        FLOAT         AI 综合评分 0–100（可空）
  🆕 ai_score_detail JSONB         AI 四维度评分详情（可空，格式：{"节奏":85,"能量":92,"爆发力":78,"感染力":88}）
```

> 🆕 AI 字段在 Librosa 评分完成后由 AI 评语服务异步填充，失败则保持 NULL。

### 步骤 1.3：`models/like.py` — Like 模型

```
like 表字段：
  id         INTEGER PRIMARY KEY
  audio_id   INTEGER FK → audio.id
  ip_address VARCHAR(45)
  created_at DATETIME
  唯一约束：UNIQUE(audio_id, ip_address)
```

### 步骤 1.4：`models/dislike.py` — Dislike 模型

与 Like 结构一致，表名不同。唯一约束同为 `UNIQUE(audio_id, ip_address)`。

---

## 二、Pydantic 模型 `schemas/`

### 步骤 2.1：`schemas/audio.py`

```python
class AudioUploadResponse:    # 上传成功后返回
    id: int
    nickname: str
    message: str

class AudioDetail:            # GET /api/audio/{id} 的响应
    id: int
    nickname: str
    duration: float
    score: float | None
    score_detail: dict | None
    🆕 ai_commentary: str | None       # AI 创意评语
    🆕 ai_score: float | None          # AI 综合评分
    🆕 ai_score_detail: dict | None    # AI 四维度：节奏/能量/爆发力/感染力
    like_count: int
    dislike_count: int
    created_at: str
    stream_url: str
    waveform_url: str                  # 波形数据接口地址

class LeaderboardItem:        # 排行榜单条
    id: int
    nickname: str
    duration: float
    score: float | None       # 评分榜用
    🆕 ai_score: float | None          # AI 综合评分
    like_count: int           # 点赞榜用
    dislike_count: int
    created_at: str
```

### 步骤 2.2：`schemas/admin.py`

```python
class AdminStats:
    total_audios: int
    total_likes: int
    total_dislikes: int
    today_uploads: int

class AdminAudioItem:         # 管理列表单条
    id: int
    nickname: str
    created_at: str
    score: float | None
    🆕 ai_score: float | None
    🆕 ai_commentary: str | None
    like_count: int
    dislike_count: int
```

---

## 三、路由实现 `main.py`

> 所有路由直接写在 `main.py` 中（项目规模小，暂不拆分 `routes/`，后续需要时再拆）。

### 步骤 3.1：应用工厂

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="最会打呼之人 API", version="1.0.0")

# CORS（开发时允许所有来源）
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

# 音频文件静态服务
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
```

### 步骤 3.2：`POST /api/audio/upload`

**请求**：`multipart/form-data`
- `file`: 音频文件（必填）
- `nickname`: 字符串（可选）

**处理流程**：
1. 校验文件扩展名 ∈ ALLOWED_EXTENSIONS
2. 校验文件大小 ≤ MAX_FILE_SIZE
3. 生成唯一文件名 `{uuid}.{ext}`，写入 `uploads/`
4. 使用 Librosa 读取时长，校验 ≤ MAX_DURATION
5. 获取客户端 IP（`request.client.host`）
6. 检查 IP 上传频率：同一 IP 每小时 ≤ 3 条
   ```python
   # 查询该 IP 最近一小时的音频数
   count = db.query(Audio).filter(
       Audio.ip_address == ip,
       Audio.created_at >= datetime.utcnow() - timedelta(hours=1)
   ).count()
   if count >= 3: raise HTTPException(429, "上传过于频繁")
   ```
7. 昵称为空则自动生成匿名代号（见第六节 `services/nickname.py`）
8. 写入 audio 表（score / ai_score / ai_commentary 均为 NULL）
9. 启动后台任务：`BackgroundTasks.add_task(score_audio, audio_id)` — 内部先 Librosa 评分再触发 AI 评语
10. 返回 `AudioUploadResponse`

### 步骤 3.3：`GET /api/audio/{id}`

1. 按 id 查询 audio 表
2. 不存在返回 404
3. 返回 `AudioDetail`（包含 AI 评语字段，AI 未完成时返回 null）

### 步骤 3.4：`GET /api/audio/stream/{id}`

1. 查询 audio 记录获取 file_path
2. 根据文件扩展名设置正确的 MIME 类型：
   - `.mp3` → `audio/mpeg`
   - `.wav` → `audio/wav`
   - `.ogg` → `audio/ogg`
   - `.webm` → `audio/webm`
3. 使用 `FileResponse(file_path, media_type=mime_type)` 返回
4. 支持 Range 请求（浏览器 `<audio>` 需要）——FastAPI `FileResponse` 默认支持

### 步骤 3.5：`POST /api/audio/{id}/like`

1. 获取客户端 IP
2. 查询是否已存在（audio_id + ip 唯一约束）
3. 已存在 → 返回 `{"message": "已点赞", "already_liked": true}`
4. 不存在 → 写入 like 表 + 更新 audio.like_count += 1

### 步骤 3.6：`POST /api/audio/{id}/dislike`

与 like 逻辑一致，改操作 dislike 表和 audio.dislike_count。

### 步骤 3.7：`GET /api/leaderboard/likes`

参数：`range: Literal["all", "week", "today"] = "all"`

```python
query = db.query(Audio)
if range == "today":
    query = query.filter(Audio.created_at >= today_start)
elif range == "week":
    query = query.filter(Audio.created_at >= week_start)
query = query.order_by(Audio.like_count.desc(), Audio.created_at.desc()).limit(10)
```

返回 `List[LeaderboardItem]`

### 步骤 3.8：`GET /api/leaderboard/scores`

与 likes 榜一致，改为按 `score` 降序排列。排除 score 为 NULL 的音频（尚未完成评分）。

### 步骤 3.9：`GET /api/audio/{id}/waveform`（预留接口）

1. 读取音频文件
2. 使用 Librosa 提取 RMS 能量曲线
3. 降采样至 ~200 个数据点（适合前端绘制）
4. 返回 `{"waveform": [0.12, 0.34, ...], "duration": 12.5}`

---

## 四、评分服务

### 步骤 4.1：Librosa 核心流程 `services/scorer.py`

```python
def score_audio(audio_id: int):
    """后台任务入口"""
    db = SessionLocal()
    try:
        audio = db.query(Audio).get(audio_id)
        # 1. 加载音频
        y, sr = librosa.load(audio.file_path)
        # 2. 计算五个维度
        dims = {
            "loudness_peak": calc_loudness(y, sr),       # 30%
            "freq_richness": calc_freq(y, sr),           # 25%
            "stability": calc_stability(y, sr),          # 20%
            "dynamic_range": calc_dynamic(y, sr),        # 15%
            "duration_score": calc_duration(len(y)/sr),  # 10%
        }
        # 3. 加权总分
        total = (
            dims["loudness_peak"] * 0.30 +
            dims["freq_richness"] * 0.25 +
            dims["stability"] * 0.20 +
            dims["dynamic_range"] * 0.15 +
            dims["duration_score"] * 0.10
        )
        # 4. 更新数据库
        audio.score = round(total, 1)
        audio.score_detail = dims
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    # 🆕 5. 独立调用 AI 评语（失败不影响 Librosa 评分结果）
    try:
        from .ai_commentary import generate_commentary
        generate_commentary(audio_id)
    except Exception:
        pass
```

### 步骤 4.2：五个维度计算函数

| 函数 | 计算方式 | 输出范围 |
|------|---------|---------|
| `calc_loudness(y, sr)` | RMS 能量取 95 分位峰值，归一化到 0–100 | 0–100 |
| `calc_freq(y, sr)` | 频谱质心标准差 + 谱滚降点分布，评估"复杂度" | 0–100 |
| `calc_stability(y, sr)` | 将音频分段，计算各段 RMS 的方差，越稳分越高 | 0–100 |
| `calc_dynamic(y, sr)` | RMS 最大值与中位数的比值 | 0–100 |
| `calc_duration(dur)` | 30–120 秒得满分，<10 秒得 0 分，>120 秒线性衰减 | 0–100 |

### 步骤 4.3：注意事项

- 音频加载时使用 `librosa.load(path, sr=22050)` 统一采样率，降低计算量
- 各维度函数需要 try-except，异常时返回默认值 50 分
- `score_detail` 存 JSON，包含各维度原始值和得分

### 🆕 步骤 4.4：AI 评语服务 `services/ai_commentary.py`

> ⚠️ **核心原则**：大模型只能识别文本，**不能直接解析音频**。传给 AI 的是 Librosa 已计算好的五维度数值特征，而非原始音频文件。

**调用方式**：使用 `openai` Python 包，指向 DeepSeek 的 OpenAI 兼容端点。

```python
from openai import OpenAI
from config import AI_API_KEY, AI_BASE_URL, AI_MODEL

client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
response = client.chat.completions.create(
    model=AI_MODEL,
    messages=[...],
    temperature=0.9,
    max_tokens=300,
)
```

**System Prompt 设计**：

```
你是一位专业的鼾声鉴赏师，擅长用诗意、幽默且专业的方式评价打呼噜音频。

用户会提供一段音频的 Librosa 算法分析数据（五维度：响度峰值、频率特色、持续稳定性、动态范围、时长评分，以及综合得分）。

请你：
1. 生成一句创意评语（30–80 字），运用丰富的名词和形容词，风格类似：
   "有种重型机械缓慢驶过月球表面的震撼，低频稳定、爆发力惊人。"
2. 从以下四个维度打分（0–100，整数）：
   - 节奏：呼噜的节拍感、规律性
   - 能量：响度与爆发力
   - 爆发力：峰值强度与冲击感
   - 感染力：整体听感的"魔性"程度

请严格按 JSON 格式返回，不要包含其他内容：
{"commentary": "...", "dimensions": {"节奏": 85, "能量": 92, "爆发力": 78, "感染力": 88}}
```

**User Message 格式**（将 Librosa 数值特征作为文本传入）：

```
请为以下鼾声数据生成评语和 AI 维度分数：

【Librosa 算法评分】
- 响度峰值：{loudness_peak} 分（权重 30%）
- 频率特色：{freq_richness} 分（权重 25%）
- 持续稳定性：{stability} 分（权重 20%）
- 动态范围：{dynamic_range} 分（权重 15%）
- 时长评分：{duration_score} 分（权重 10%）
- 综合得分：{score} 分

请给出你的专业评语和四维度评分。
```

**写入数据库**：

```python
# AI 综合分 = 四维度平均值
ai_score = round(sum(dimensions.values()) / len(dimensions), 1)

audio.ai_commentary = commentary       # 创意评语文本
audio.ai_score = ai_score              # AI 综合评分
audio.ai_score_detail = dimensions     # {"节奏":85, "能量":92, ...}
db.commit()
```

**容错策略**：
- AI 调用失败（超时/key 失效/额度不足等）→ 记录 warning 日志，静默退出
- `ai_commentary` / `ai_score` / `ai_score_detail` 保持 NULL
- **不影响** Librosa 评分主流程，前端展示时判空即可
- JSON 解析时兼容 markdown 代码块包裹（```json ... ```）

### 🆕 步骤 4.5：后台任务调用链

```
POST /api/audio/upload
  └─ BackgroundTasks.add_task(score_audio, audio_id)
       └─ score_audio(audio_id)
            ├─ 1. Librosa 加载音频
            ├─ 2. 五维度计算 + 加权总分
            ├─ 3. 写入 score / score_detail → commit
            └─ 4. 调用 generate_commentary(audio_id)  ← 🆕 AI 评语
                 ├─ 读取 score_detail（文本特征）
                 ├─ 请求 DeepSeek API
                 └─ 写入 ai_commentary / ai_score / ai_score_detail → commit
```

注意：步骤 4 在步骤 3 的 try/except 之外独立执行，AI 失败不会回滚 Librosa 评分。

---

## 五、后台管理接口

### 步骤 5.1：鉴权中间件

管理接口统一要求请求头 `Authorization: Bearer <ADMIN_PASSWORD>`，或查询参数 `?token=<ADMIN_PASSWORD>`。

```python
from fastapi import Header, HTTPException

def verify_admin(authorization: str = Header(None)):
    if not authorization or authorization.replace("Bearer ", "") != ADMIN_PASSWORD:
        raise HTTPException(401, "无权限")
```

### 步骤 5.2：`GET /api/admin/stats`

返回 `AdminStats`：各表的 COUNT，今日上传数。

### 步骤 5.3：`GET /api/admin/audios`

分页参数 `page`, `size`（默认 1, 20）。按 `created_at` 倒序排列。🆕 返回字段包含 `ai_score` 和 `ai_commentary`。

### 步骤 5.4：`DELETE /api/admin/audios/{id}`

1. 验证音频存在
2. 删除磁盘上的音频文件
3. 删除关联的 like / dislike 记录
4. 删除 audio 记录
5. 返回 `{"message": "已删除"}`

---

## 六、匿名代号生成 `services/nickname.py`

从两个词池中各随机抽取一个组成：

```python
ADJECTIVES = ["夜半", "雷霆", "风暴", "沉睡", "悠扬", "轰鸣", "温柔", "狂暴", "银河", "深海",
              "山谷", "云端", ...]
NOUNS = ["鼓手", "之息", "号角", "雷鸣", "微风", "发动机", "低音炮", "协奏曲", "交响乐", "独奏者", ...]

def generate_nickname() -> str:
    return random.choice(ADJECTIVES) + random.choice(NOUNS)
```

---

## 七、启动与测试

### 7.1 本地启动

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 7.2 自动生成 API 文档

- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

### 7.3 数据库初始化

在 `main.py` 启动事件中自动建表：

```python
@app.on_event("startup")
def startup():
    models.database.Base.metadata.create_all(bind=engine)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
```

### 🆕 7.4 环境变量配置（AI 评语）

启动前设置 DeepSeek API Key：

```bash
# Linux / macOS
export AI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Windows PowerShell
$env:AI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 或创建 backend/.env 文件（需 python-dotenv，加入 .gitignore）
echo "AI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" > backend/.env
```

---

*关联文档：Vision.md（总体设计）· help.md（需求 & 进度追踪）*
