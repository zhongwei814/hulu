"""AI 评语服务：全部走 mock，不发真实请求。"""

import json
from types import SimpleNamespace

import pytest

from models.audio import Audio
from services import ai_commentary

VALID_PAYLOAD = {
    "commentary": "有种重型机械缓慢驶过月球表面的震撼。",
    "dimensions": {"节奏": 85, "能量": 92, "爆发力": 78, "感染力": 88},
}


def _install_fake_client(monkeypatch, content=None, error=None):
    class _Completions:
        def create(self, **kwargs):
            if error is not None:
                raise error
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class _Client:
        def __init__(self, *args, **kwargs):
            self.chat = SimpleNamespace(completions=_Completions())

    monkeypatch.setattr("openai.OpenAI", _Client)


@pytest.fixture
def audio_with_score(seed_audio, db):
    audio_id = seed_audio(score=60.0)
    yield audio_id
    db.expire_all()


def test_skips_entirely_when_api_key_missing(monkeypatch, audio_with_score, db):
    monkeypatch.setattr(ai_commentary, "AI_API_KEY", "")
    monkeypatch.setattr(
        "openai.OpenAI", lambda *a, **k: pytest.fail("不应发起 AI 调用")
    )

    ai_commentary.generate_commentary(audio_with_score)

    db.expire_all()
    assert db.query(Audio).get(audio_with_score).ai_commentary is None


def test_parses_plain_json_response(monkeypatch, audio_with_score, db):
    monkeypatch.setattr(ai_commentary, "AI_API_KEY", "test-key")
    _install_fake_client(monkeypatch, content=json.dumps(VALID_PAYLOAD))

    ai_commentary.generate_commentary(audio_with_score)

    db.expire_all()
    audio = db.query(Audio).get(audio_with_score)
    assert audio.ai_commentary == VALID_PAYLOAD["commentary"]
    assert audio.ai_score_detail == VALID_PAYLOAD["dimensions"]
    assert audio.ai_score == pytest.approx(85.8)


@pytest.mark.parametrize(
    "content",
    [
        "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```",
        "```\n" + json.dumps(VALID_PAYLOAD) + "\n```",
        "  \n" + json.dumps(VALID_PAYLOAD) + "  ",
    ],
    ids=["fenced-json", "fenced-plain", "whitespace-padded"],
)
def test_parses_markdown_fenced_json(monkeypatch, audio_with_score, db, content):
    monkeypatch.setattr(ai_commentary, "AI_API_KEY", "test-key")
    _install_fake_client(monkeypatch, content=content)

    ai_commentary.generate_commentary(audio_with_score)

    db.expire_all()
    assert db.query(Audio).get(audio_with_score).ai_score == pytest.approx(85.8)


def test_malformed_response_does_not_raise_or_write(monkeypatch, audio_with_score, db):
    monkeypatch.setattr(ai_commentary, "AI_API_KEY", "test-key")
    _install_fake_client(monkeypatch, content="抱歉，我无法完成这个请求。")

    ai_commentary.generate_commentary(audio_with_score)

    db.expire_all()
    audio = db.query(Audio).get(audio_with_score)
    assert audio.ai_commentary is None
    assert audio.ai_score is None


def test_api_failure_is_swallowed(monkeypatch, audio_with_score, db):
    monkeypatch.setattr(ai_commentary, "AI_API_KEY", "test-key")
    _install_fake_client(monkeypatch, error=RuntimeError("502 Bad Gateway"))

    ai_commentary.generate_commentary(audio_with_score)

    db.expire_all()
    assert db.query(Audio).get(audio_with_score).ai_commentary is None


def test_skips_when_score_detail_is_missing(monkeypatch, seed_audio, db):
    monkeypatch.setattr(ai_commentary, "AI_API_KEY", "test-key")
    monkeypatch.setattr(
        "openai.OpenAI", lambda *a, **k: pytest.fail("评分缺失时不应发起 AI 调用")
    )
    audio_id = seed_audio(score=None)

    ai_commentary.generate_commentary(audio_id)

    db.expire_all()
    assert db.query(Audio).get(audio_id).ai_commentary is None


def test_ignores_unknown_audio_id(monkeypatch):
    monkeypatch.setattr(ai_commentary, "AI_API_KEY", "test-key")
    monkeypatch.setattr(
        "openai.OpenAI", lambda *a, **k: pytest.fail("未知 id 不应发起 AI 调用")
    )

    ai_commentary.generate_commentary(999_999)


def test_non_numeric_dimensions_are_ignored_in_average(monkeypatch, audio_with_score, db):
    monkeypatch.setattr(ai_commentary, "AI_API_KEY", "test-key")
    payload = {"commentary": "x", "dimensions": {"节奏": 80, "能量": 90, "备注": "高"}}
    _install_fake_client(monkeypatch, content=json.dumps(payload))

    ai_commentary.generate_commentary(audio_with_score)

    db.expire_all()
    assert db.query(Audio).get(audio_with_score).ai_score == pytest.approx(85.0)
