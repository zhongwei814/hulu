"""评分引擎：五维度公式 + 后台任务端到端。"""

import numpy as np
import pytest

from models.audio import Audio
from services.scorer import (
    _calc_duration_score,
    _calc_dynamic_range,
    _calc_freq_richness,
    _calc_loudness,
    _calc_stability,
    score_audio,
)

DIMENSIONS = {
    "loudness_peak",
    "freq_richness",
    "stability",
    "dynamic_range",
    "duration_score",
}


def _tone(freq=80.0, seconds=1.0, sr=22050, amp=0.5):
    t = np.linspace(0, seconds, int(seconds * sr), endpoint=False)
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# ---- 时长维度（纯公式，边界最值得钉死）----

@pytest.mark.parametrize(
    "duration,expected",
    [
        (0.0, 0.0),
        (9.9, 0.0),
        (10.0, 0.0),
        (20.0, 50.0),
        (29.9, 99.5),
        (30.0, 100.0),
        (60.0, 100.0),
        (120.0, 100.0),
        (121.0, 99.2),
        (180.0, 50.0),
        (240.0, 0.0),
        (600.0, 0.0),
    ],
)
def test_duration_score_boundaries(duration, expected):
    assert _calc_duration_score(duration) == pytest.approx(expected, abs=0.05)


def test_duration_score_never_negative():
    assert _calc_duration_score(10_000) == 0.0


# ---- 四个信号维度 ----

@pytest.mark.parametrize(
    "calc",
    [_calc_loudness, _calc_freq_richness, _calc_stability, _calc_dynamic_range],
)
@pytest.mark.parametrize(
    "signal",
    [
        np.zeros(22050, dtype=np.float32),
        np.full(22050, 0.5, dtype=np.float32),
        _tone(),
        np.array([], dtype=np.float32),
        np.array([0.3], dtype=np.float32),
        np.random.default_rng(0).standard_normal(22050).astype(np.float32),
    ],
    ids=["silence", "dc", "tone", "empty", "single", "noise"],
)
def test_signal_dimensions_stay_in_range_and_never_crash(calc, signal):
    value = calc(signal)
    assert np.isfinite(value)
    assert 0.0 <= value <= 100.0


def test_loudness_increases_with_amplitude():
    quiet = _calc_loudness(_tone(amp=0.05))
    loud = _calc_loudness(_tone(amp=0.9))
    assert quiet < loud


def test_stability_is_maximal_for_constant_signal():
    assert _calc_stability(np.full(22050, 0.5, dtype=np.float32)) == 100.0


# ---- 后台任务端到端 ----

def test_score_audio_persists_score_and_all_dimensions(seed_audio, make_wav, db):
    audio_id = seed_audio(file_path=str(make_wav(seconds=30.0)))

    score_audio(audio_id)

    db.expire_all()
    audio = db.query(Audio).get(audio_id)
    assert audio.score is not None
    assert 0.0 <= audio.score <= 100.0
    assert set(audio.score_detail) == DIMENSIONS
    assert all(0.0 <= v <= 100.0 for v in audio.score_detail.values())


def test_score_audio_rewards_duration_in_the_sweet_spot(seed_audio, make_wav, db):
    short_id = seed_audio(file_path=str(make_wav(seconds=5.0, name="short.wav")))
    ideal_id = seed_audio(file_path=str(make_wav(seconds=60.0, name="ideal.wav")))

    score_audio(short_id)
    score_audio(ideal_id)

    db.expire_all()
    short = db.query(Audio).get(short_id)
    ideal = db.query(Audio).get(ideal_id)
    assert short.score_detail["duration_score"] == 0.0
    assert ideal.score_detail["duration_score"] == 100.0
    assert ideal.score > short.score


def test_score_audio_ignores_unknown_id():
    score_audio(999_999)  # 不应抛异常


def test_score_audio_leaves_score_unset_for_corrupt_file(seed_audio, tmp_path, db):
    bad = tmp_path / "corrupt.wav"
    bad.write_bytes(b"not audio at all")
    audio_id = seed_audio(file_path=str(bad))

    score_audio(audio_id)

    db.expire_all()
    assert db.query(Audio).get(audio_id).score is None


def test_score_audio_survives_missing_file(seed_audio, db):
    audio_id = seed_audio(file_path="C:/definitely/not/here.wav")

    score_audio(audio_id)

    db.expire_all()
    assert db.query(Audio).get(audio_id).score is None


def test_score_audio_is_idempotent(seed_audio, make_wav, db):
    audio_id = seed_audio(file_path=str(make_wav(seconds=30.0)))

    score_audio(audio_id)
    db.expire_all()
    first = db.query(Audio).get(audio_id).score

    score_audio(audio_id)
    db.expire_all()
    assert db.query(Audio).get(audio_id).score == first
