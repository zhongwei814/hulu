import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import (
    FastAPI, File, Form, UploadFile, HTTPException, Request,
    Depends, BackgroundTasks, Header,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from config import UPLOAD_DIR, ADMIN_PASSWORD, MAX_FILE_SIZE, MAX_DURATION, ALLOWED_EXTENSIONS, LEADERBOARD_SIZE
from models.database import engine, Base, get_db
from models.audio import Audio
from models.like import Like
from models.dislike import Dislike
from schemas.audio import AudioUploadResponse, AudioDetail, LeaderboardItem
from schemas.admin import AdminStats, AdminAudioItem
from services.scorer import score_audio
from services.nickname import generate_nickname

app = FastAPI(title="最会打呼之人 API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# 音频文件静态服务（直接访问上传目录）
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---- 工具函数 ----

def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _mime_type(ext: str) -> str:
    return {".mp3": "audio/mpeg", ".wav": "audio/wav",
            ".ogg": "audio/ogg", ".webm": "audio/webm"}.get(ext, "audio/mpeg")


def _audio_to_detail(audio: Audio) -> AudioDetail:
    return AudioDetail(
        id=audio.id, nickname=audio.nickname, duration=audio.duration,
        score=audio.score, score_detail=audio.score_detail,
        ai_commentary=audio.ai_commentary,
        ai_score=audio.ai_score,
        ai_score_detail=audio.ai_score_detail,
        like_count=audio.like_count, dislike_count=audio.dislike_count,
        created_at=audio.created_at.isoformat(),
        stream_url=f"/api/audio/stream/{audio.id}",
        waveform_url=f"/api/audio/{audio.id}/waveform",
    )


def _audio_to_leaderboard(audio: Audio) -> LeaderboardItem:
    return LeaderboardItem(
        id=audio.id, nickname=audio.nickname, duration=audio.duration,
        score=audio.score, ai_score=audio.ai_score,
        like_count=audio.like_count,
        dislike_count=audio.dislike_count,
        created_at=audio.created_at.isoformat(),
    )


def _time_range_filter(query, range_str: str, model):
    now = datetime.now(timezone.utc)
    if range_str == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return query.filter(model.created_at >= start)
    elif range_str == "week":
        start = now - timedelta(days=7)
        return query.filter(model.created_at >= start)
    return query


# ---- 音频上传 & 查询 ----

@app.post("/api/audio/upload", response_model=AudioUploadResponse)
async def upload_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    nickname: str = Form(""),
    db: Session = Depends(get_db),
):
    # 校验扩展名
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的格式：{ext}")

    # 校验文件大小
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件大小超过 10MB 限制")

    # 保存文件
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # 获取时长
    import librosa
    try:
        duration = librosa.get_duration(path=filepath)
    except Exception:
        os.remove(filepath)
        raise HTTPException(400, "无法解析音频文件")

    if duration > MAX_DURATION:
        os.remove(filepath)
        raise HTTPException(400, f"音频时长超过 {MAX_DURATION} 秒限制")

    # IP 防刷
    ip = _get_client_ip(request)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_count = db.query(Audio).filter(
        Audio.ip_address == ip, Audio.created_at >= one_hour_ago
    ).count()
    if recent_count >= 3:
        os.remove(filepath)
        raise HTTPException(429, "上传过于频繁，请稍后再试")

    # 昵称
    display_name = nickname.strip() if nickname.strip() else generate_nickname()

    # 入库
    audio = Audio(
        nickname=display_name,
        file_path=filepath,
        duration=round(duration, 1),
        file_size=len(contents),
        ip_address=ip,
        created_at=datetime.now(timezone.utc),
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)

    # 异步评分
    background_tasks.add_task(score_audio, audio.id)

    return AudioUploadResponse(id=audio.id, nickname=display_name, message="上传成功，正在评分中…")


@app.get("/api/audio/{id}", response_model=AudioDetail)
def get_audio(id: int, db: Session = Depends(get_db)):
    audio = db.query(Audio).get(id)
    if audio is None:
        raise HTTPException(404, "音频不存在")
    return _audio_to_detail(audio)


@app.get("/api/audio/stream/{id}")
def stream_audio(id: int, db: Session = Depends(get_db)):
    audio = db.query(Audio).get(id)
    if audio is None:
        raise HTTPException(404, "音频不存在")
    ext = os.path.splitext(audio.file_path)[-1].lower()
    return FileResponse(audio.file_path, media_type=_mime_type(ext))


@app.get("/api/audio/{id}/waveform")
def get_waveform(id: int, db: Session = Depends(get_db)):
    audio = db.query(Audio).get(id)
    if audio is None:
        raise HTTPException(404, "音频不存在")
    try:
        import librosa
        import numpy as np
        y, sr = librosa.load(audio.file_path, sr=22050)
        rms = librosa.feature.rms(y=y).flatten()
        # 降采样到 ~200 个点
        if len(rms) > 200:
            indices = np.linspace(0, len(rms) - 1, 200, dtype=int)
            rms = rms[indices]
        return {"waveform": rms.tolist(), "duration": audio.duration}
    except Exception:
        raise HTTPException(500, "波形数据提取失败")


# ---- 点赞 / 点踩 ----

@app.post("/api/audio/{id}/like")
def like_audio(id: int, request: Request, db: Session = Depends(get_db)):
    audio = db.query(Audio).get(id)
    if audio is None:
        raise HTTPException(404, "音频不存在")
    ip = _get_client_ip(request)
    existing = db.query(Like).filter(Like.audio_id == id, Like.ip_address == ip).first()
    if existing:
        return {"message": "已点赞", "already_liked": True}
    db.add(Like(audio_id=id, ip_address=ip, created_at=datetime.now(timezone.utc)))
    audio.like_count += 1
    db.commit()
    return {"message": "点赞成功", "like_count": audio.like_count}


@app.post("/api/audio/{id}/dislike")
def dislike_audio(id: int, request: Request, db: Session = Depends(get_db)):
    audio = db.query(Audio).get(id)
    if audio is None:
        raise HTTPException(404, "音频不存在")
    ip = _get_client_ip(request)
    existing = db.query(Dislike).filter(Dislike.audio_id == id, Dislike.ip_address == ip).first()
    if existing:
        return {"message": "已点踩", "already_disliked": True}
    db.add(Dislike(audio_id=id, ip_address=ip, created_at=datetime.now(timezone.utc)))
    audio.dislike_count += 1
    db.commit()
    return {"message": "点踩成功", "dislike_count": audio.dislike_count}


# ---- 排行榜 ----

def _leaderboard_query(db: Session, range_str: str, order_by):
    query = db.query(Audio)
    query = _time_range_filter(query, range_str, Audio)
    query = query.order_by(order_by.desc(), Audio.created_at.desc()).limit(LEADERBOARD_SIZE)
    return [_audio_to_leaderboard(a) for a in query.all()]


@app.get("/api/leaderboard/likes")
def leaderboard_likes(range: str = "all", db: Session = Depends(get_db)):
    if range not in ("all", "week", "today"):
        raise HTTPException(400, "range 参数仅支持 all/week/today")
    return _leaderboard_query(db, range, Audio.like_count)


@app.get("/api/leaderboard/scores")
def leaderboard_scores(range: str = "all", db: Session = Depends(get_db)):
    if range not in ("all", "week", "today"):
        raise HTTPException(400, "range 参数仅支持 all/week/today")
    query = db.query(Audio).filter(Audio.score.isnot(None))
    query = _time_range_filter(query, range, Audio)
    query = query.order_by(Audio.score.desc(), Audio.created_at.desc()).limit(LEADERBOARD_SIZE)
    return [_audio_to_leaderboard(a) for a in query.all()]


# ---- 管理后台 ----

def _verify_admin(authorization: str = Header(None)):
    if not authorization or authorization.replace("Bearer ", "") != ADMIN_PASSWORD:
        raise HTTPException(401, "无权限")


@app.get("/api/admin/stats", dependencies=[Depends(_verify_admin)])
def admin_stats(db: Session = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return AdminStats(
        total_audios=db.query(Audio).count(),
        total_likes=db.query(Like).count(),
        total_dislikes=db.query(Dislike).count(),
        today_uploads=db.query(Audio).filter(Audio.created_at >= today_start).count(),
    )


@app.get("/api/admin/audios", dependencies=[Depends(_verify_admin)])
def admin_audios(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    query = db.query(Audio).order_by(Audio.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            AdminAudioItem(
                id=a.id, nickname=a.nickname,
                created_at=a.created_at.isoformat(),
                score=a.score, ai_score=a.ai_score,
                ai_commentary=a.ai_commentary,
                like_count=a.like_count,
                dislike_count=a.dislike_count,
            ) for a in items
        ],
    }


@app.delete("/api/admin/audios/{id}", dependencies=[Depends(_verify_admin)])
def admin_delete_audio(id: int, db: Session = Depends(get_db)):
    audio = db.query(Audio).get(id)
    if audio is None:
        raise HTTPException(404, "音频不存在")
    # 删除文件
    if os.path.exists(audio.file_path):
        os.remove(audio.file_path)
    # 删除关联记录
    db.query(Like).filter(Like.audio_id == id).delete()
    db.query(Dislike).filter(Dislike.audio_id == id).delete()
    db.delete(audio)
    db.commit()
    return {"message": "已删除"}


# ---- 健康检查 ----

@app.get("/api/health")
def health_check():
    """存活探针：用于监控和负载均衡。"""
    return {"status": "ok", "version": "1.0.0"}
