"""
轻量音频工具 — 使用 miniaudio + numpy 替代 librosa。

librosa ≈ 100MB+（含 numba/scipy/scikit-learn），Vercel Hobby 函数限制 250MB。
miniaudio ≈ 2MB，自包含 C 库，原生支持 MP3 / WAV / OGG / FLAC，
所有信号分析（RMS、频谱质心等）由 numpy 直接计算。
"""

import os
import logging

import numpy as np
import miniaudio

logger = logging.getLogger(__name__)

# miniaudio 不原生支持 WebM 容器格式，回退到 audioread（如果可用）
_HAS_AUDIOREAD = False
try:
    import audioread  # noqa: F401
    _HAS_AUDIOREAD = True
except ImportError:
    pass


# ---- 文件读取 ----

def get_duration(filepath: str) -> float:
    """获取音频时长（秒）。"""
    ext = os.path.splitext(filepath)[-1].lower()
    if ext == ".webm":
        return _get_duration_audioread(filepath)
    info = miniaudio.get_file_info(filepath)
    return info.duration


def _get_duration_audioread(filepath: str) -> float:
    """通过 audioread 获取时长（WebM 回退方案）。"""
    try:
        import audioread
        with audioread.audio_open(filepath) as f:
            return f.duration
    except Exception:
        raise OSError(f"无法解析音频文件（包括其时长）: {filepath}")


def load_audio_mono(filepath: str, target_sr: int = 22050) -> "tuple[np.ndarray, int]":
    """
    加载音频文件，转为单声道，重采样到 target_sr。
    返回 (samples, sample_rate)。
    """
    ext = os.path.splitext(filepath)[-1].lower()
    if ext == ".webm":
        return _load_webm(filepath, target_sr)

    try:
        audio = miniaudio.decode_file(filepath, dither=False)
    except Exception:
        raise OSError(f"无法解析音频文件: {filepath}")

    # 转为 numpy float32
    samples = np.array(audio.samples, dtype=np.float32)

    # 多声道 → 单声道
    if audio.nchannels > 1:
        samples = samples.reshape((-1, audio.nchannels))
        samples = samples.mean(axis=1)

    # 重采样
    if audio.sample_rate != target_sr:
        samples = _resample_linear(samples, audio.sample_rate, target_sr)

    return samples, target_sr


def _load_webm(filepath: str, target_sr: int = 22050) -> "tuple[np.ndarray, int]":
    """WebM 格式回退方案（通过 audioread）。"""
    if not _HAS_AUDIOREAD:
        raise OSError(
            "WebM 格式需要 audioread 库支持。"
            "请在 requirements.txt 中取消注释 audioread 依赖。"
        )
    import audioread
    with audioread.audio_open(filepath) as f:
        sr_native = f.samplerate
        # 收集所有音频块
        chunks = []
        for buf in f:
            # audioread 返回 bytes，转为 float32
            chunk = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0
            chunks.append(chunk)
        samples = np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)

    if f.channels > 1:
        samples = samples.reshape((-1, f.channels)).mean(axis=1)

    if sr_native != target_sr:
        samples = _resample_linear(samples, sr_native, target_sr)

    return samples, target_sr


def _resample_linear(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """线性插值重采样。"""
    if orig_sr == target_sr or len(samples) < 2:
        return samples.astype(np.float32)
    duration = len(samples) / orig_sr
    new_len = max(1, int(duration * target_sr))
    old_idx = np.linspace(0, len(samples) - 1, len(samples))
    new_idx = np.linspace(0, len(samples) - 1, new_len)
    return np.interp(new_idx, old_idx, samples).astype(np.float32)


# ---- 信号分析 ----

def compute_rms(
    y: np.ndarray,
    frame_length: int = 2048,
    hop_length: int = 512,
) -> np.ndarray:
    """
    逐帧计算 RMS 能量（等效于 librosa.feature.rms）。
    返回形状 (n_frames,) 的 numpy 数组。
    """
    if len(y) < hop_length:
        y = np.pad(y, (0, hop_length - len(y)))

    n_frames = 1 + (len(y) - frame_length) // hop_length
    if n_frames < 1:
        n_frames = 1

    # 高效帧提取（as_strided 避免复制）
    y = np.ascontiguousarray(y)
    shape = (n_frames, frame_length)
    strides = (y.strides[0] * hop_length, y.strides[0])
    frames = np.lib.stride_tricks.as_strided(y, shape=shape, strides=strides)

    return np.sqrt(np.mean(frames ** 2, axis=1))


def compute_spectral_centroid(
    y: np.ndarray,
    sr: int,
    frame_length: int = 2048,
    hop_length: int = 512,
) -> np.ndarray:
    """
    逐帧计算频谱质心（等效于 librosa.feature.spectral_centroid）。
    返回形状 (n_frames,) 的 numpy 数组。
    """
    if len(y) < hop_length:
        y = np.pad(y, (0, hop_length - len(y)))

    n_frames = 1 + (len(y) - frame_length) // hop_length
    if n_frames < 1:
        n_frames = 1

    freqs = np.fft.rfftfreq(frame_length, 1.0 / sr)
    window = np.hanning(frame_length)
    centroids = np.zeros(n_frames, dtype=np.float32)

    for i in range(n_frames):
        start = i * hop_length
        frame = y[start:start + frame_length] * window
        spectrum = np.abs(np.fft.rfft(frame))
        total = np.sum(spectrum)
        if total > 1e-10:
            centroids[i] = np.sum(freqs * spectrum) / total

    return centroids


def compute_waveform_rms(
    y: np.ndarray,
    target_points: int = 200,
) -> np.ndarray:
    """降采样 RMS 到指定点数，用于前端波形展示。"""
    rms = compute_rms(y)
    if len(rms) > target_points:
        indices = np.linspace(0, len(rms) - 1, target_points, dtype=int)
        rms = rms[indices]
    return rms
