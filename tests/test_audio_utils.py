"""音频工具层：纯 numpy 信号处理 + 文件读取。不需要 HTTP。"""

import warnings

import numpy as np
import pytest

from services.audio_utils import (
    compute_rms,
    compute_spectral_centroid,
    compute_waveform_rms,
    get_duration,
    load_audio_mono,
)

FRAME = 2048


def _tone(freq, seconds=1.0, sr=22050, amp=0.5):
    t = np.linspace(0, seconds, int(seconds * sr), endpoint=False)
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# ---- compute_rms ----

def test_rms_of_constant_signal_matches_analytic_value():
    y = np.full(FRAME * 2, 0.5, dtype=np.float32)
    rms = compute_rms(y)
    assert rms[0] == pytest.approx(0.5, rel=1e-5)


@pytest.mark.parametrize("n", [0, 1, 100, 300, 511, 512, 1000, 2047])
def test_rms_short_input_is_finite_and_correct(n):
    """回归测试：输入短于 frame_length 时曾越界读内存，返回 inf。"""
    y = np.full(n, 0.5, dtype=np.float32)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # 旧实现会抛 overflow RuntimeWarning
        rms = compute_rms(y)

    assert np.all(np.isfinite(rms))
    # 补零到一整帧后的理论值
    assert rms[0] == pytest.approx(0.5 * np.sqrt(n / FRAME), abs=1e-4)


def test_rms_frame_count_scales_with_input_length():
    assert compute_rms(np.zeros(FRAME, dtype=np.float32)).shape == (1,)
    assert compute_rms(np.zeros(FRAME * 3, dtype=np.float32)).shape == (3,)


def test_rms_of_silence_is_zero():
    rms = compute_rms(np.zeros(FRAME * 4, dtype=np.float32))
    assert np.all(rms == 0.0)


def test_rms_of_empty_input_does_not_crash():
    rms = compute_rms(np.array([], dtype=np.float32))
    assert rms.shape == (1,)
    assert rms[0] == 0.0


# ---- compute_spectral_centroid ----

@pytest.mark.parametrize("n", [0, 1, 300, 1000, 2047])
def test_spectral_centroid_short_input_is_finite(n):
    """同一处补齐缺陷的回归测试：旧实现在这里抛广播错误，被上层吞成默认分。"""
    y = np.full(n, 0.5, dtype=np.float32)
    centroid = compute_spectral_centroid(y, 22050)
    assert np.all(np.isfinite(centroid))


def test_spectral_centroid_of_pure_tone_is_near_tone_frequency():
    sr = 22050
    y = _tone(1000.0, seconds=1.0, sr=sr)
    centroid = compute_spectral_centroid(y, sr)
    assert centroid.mean() == pytest.approx(1000.0, rel=0.15)


def test_spectral_centroid_tracks_frequency_ordering():
    sr = 22050
    low = compute_spectral_centroid(_tone(200.0, sr=sr), sr).mean()
    high = compute_spectral_centroid(_tone(3000.0, sr=sr), sr).mean()
    assert low < high


# ---- compute_waveform_rms ----

@pytest.mark.parametrize("seconds", [0.1, 1.0, 30.0])
def test_waveform_rms_never_exceeds_target_points(seconds):
    y = _tone(80.0, seconds=seconds)
    waveform = compute_waveform_rms(y, target_points=200)
    assert 0 < len(waveform) <= 200
    assert np.all(np.isfinite(waveform))


def test_waveform_rms_preserves_short_input():
    y = np.full(FRAME, 0.4, dtype=np.float32)
    assert len(compute_waveform_rms(y, target_points=200)) == 1


# ---- 文件读取 ----

def test_get_duration_reads_generated_wav(make_wav):
    path = make_wav(seconds=2.5)
    assert get_duration(str(path)) == pytest.approx(2.5, abs=0.05)


def test_load_audio_mono_returns_requested_sample_rate(make_wav):
    path = make_wav(seconds=1.0, sr=44100)
    y, sr = load_audio_mono(str(path), target_sr=22050)
    assert sr == 22050
    assert y.dtype == np.float32
    assert len(y) == pytest.approx(22050, rel=0.05)


def test_load_audio_mono_downsamples_to_mono(make_wav, tmp_path):
    import wave

    stereo = tmp_path / "stereo.wav"
    n = 22050
    t = np.linspace(0, 1.0, n, endpoint=False)
    left = (0.5 * np.sin(2 * np.pi * 200 * t) * 32767).astype(np.int16)
    right = (0.5 * np.sin(2 * np.pi * 200 * t) * 32767).astype(np.int16)
    interleaved = np.empty(2 * n, dtype=np.int16)
    interleaved[0::2] = left
    interleaved[1::2] = right
    with wave.open(str(stereo), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(interleaved.tobytes())

    y, _ = load_audio_mono(str(stereo))
    assert y.ndim == 1
    assert len(y) == pytest.approx(n, rel=0.05)


def test_load_audio_mono_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"this is definitely not audio")
    with pytest.raises(OSError):
        load_audio_mono(str(bad))


def test_get_duration_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"this is definitely not audio")
    with pytest.raises(Exception):
        get_duration(str(bad))
