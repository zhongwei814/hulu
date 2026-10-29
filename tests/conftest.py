"""共享测试夹具。

三个关键约束（都源于项目现状，不是随意选择）：
1. config.py 在导入时就固化 DATABASE_URL / UPLOAD_DIR，所以必须先改 config 模块属性，
   再导入 main —— 否则测试会连到真实的 PostgreSQL 库。
2. scorer.py 和 ai_commentary.py 自己调 SessionLocal()，不走 FastAPI 依赖注入，
   因此覆盖 get_db 无效，只能整体换掉 DATABASE_URL。
3. TestClient 会在返回响应前跑完 BackgroundTasks，所以上传后无需 sleep 即可断言评分结果。
"""

import shutil
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

_TMP = Path(tempfile.mkdtemp(prefix="snore-test-"))

import config  # noqa: E402

config.DATABASE_URL = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
config.UPLOAD_DIR = str(_TMP / "uploads")
config.ADMIN_PASSWORD = "test-pw"
config.AI_API_KEY = ""  # 关闭 AI 调用：不花钱、不依赖网络

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from models.database import Base, SessionLocal, engine  # noqa: E402

ADMIN_HEADERS = {"Authorization": "Bearer test-pw"}


@pytest.fixture(scope="session", autouse=True)
def _cleanup_tmp():
    yield
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client(clean_db):
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def raw_client(clean_db):
    """不把服务端异常转成 raise，用于断言 500 响应。"""
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def db(clean_db):
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def make_wav(tmp_path):
    """用标准库 wave 造测试音频，避免为了造 mp3/webm 再装编码库。"""

    def _make(seconds=30.0, sr=22050, freq=80.0, amp=0.6, name="snore.wav"):
        n = max(1, int(seconds * sr))
        t = np.linspace(0, seconds, n, endpoint=False)
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t)
        sig = amp * np.sin(2 * np.pi * freq * t) * envelope
        pcm = np.clip(sig * 32767, -32768, 32767).astype(np.int16)
        path = tmp_path / name
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(pcm.tobytes())
        return path

    return _make


@pytest.fixture
def upload(client):
    def _upload(path, nickname="", ip=None, filename=None):
        headers = {"X-Forwarded-For": ip} if ip else {}
        with open(path, "rb") as f:
            return client.post(
                "/api/audio/upload",
                files={"file": (filename or path.name, f, "audio/wav")},
                data={"nickname": nickname},
                headers=headers,
            )

    return _upload


@pytest.fixture
def seed_audio(clean_db):
    """直接插库，用于排行榜/后台测试——比走上传流程快得多且可控。"""
    from datetime import datetime, timezone

    from models.audio import Audio

    def _seed(
        nickname="测试昵称",
        score=None,
        like_count=0,
        dislike_count=0,
        created_at=None,
        duration=30.0,
        file_path=None,
        ip_address="10.0.0.1",
    ):
        session = SessionLocal()
        try:
            audio = Audio(
                nickname=nickname,
                file_path=file_path or str(_TMP / "missing.wav"),
                duration=duration,
                file_size=1024,
                score=score,
                score_detail={"loudness_peak": 60.0} if score is not None else None,
                like_count=like_count,
                dislike_count=dislike_count,
                ip_address=ip_address,
                created_at=created_at or datetime.now(timezone.utc),
            )
            session.add(audio)
            session.commit()
            session.refresh(audio)
            return audio.id
        finally:
            session.close()

    return _seed
